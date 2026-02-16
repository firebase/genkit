# AI-Powered Release Intelligence — Implementation Plan

## Problem Statement

With 67+ packages in the Genkit monorepo, raw per-package changelogs
concatenated into the Release PR body exceed GitHub's **65,536-character
limit**. The current fix (collapsible `<details>` + progressive
truncation) is a workaround. The real solution is AI-powered
summarization that produces release notes comparable to hand-written
ones like [py/v0.5.0](https://github.com/firebase/genkit/releases/tag/py%2Fv0.5.0).

Beyond summarization, the same infrastructure enables: enhanced
changelogs, breaking change detection, migration guide generation,
platform-tailored announcements, security advisory drafting, and
contextual error hints — all using the Genkit SDK as a dogfooding
showcase.

## Design Principles

1. **CI-friendly by default** — Default to Ollama + `gemma3:4b`
   (~2.3 GB). Small enough for fast CI download, capable enough for
   structured summarization. No API key, no cloud account, no egress.
2. **Graceful fallback** — If Ollama isn't running or the model isn't
   pulled, fall back to the existing truncation logic. Never block a
   release on AI availability.
3. **Dogfooding** — Use the Genkit SDK (`ai.generate()` with Pydantic
   structured output) so releasekit is itself a Genkit showcase.
4. **Configurable** — Cloud models (Google GenAI, Vertex AI, Anthropic)
   configurable via `releasekit.toml`, env vars, or CLI flags.
5. **Deterministic-ish** — Low temperature (0.2), cached by content
   hash. Same changelogs → same summary (modulo model non-determinism).
6. **Cacheable** — Both the Ollama model binary (`~/.ollama/models/`)
   and the summary output (content-hash keyed) are cacheable in CI.

---

## Task Dependency Graph

```
T1: Output schema (ReleaseSummary Pydantic model)
    └── no deps

T2: AI config schema ([ai] section in ReleaseConfig)
    └── no deps

T3: Optional deps in pyproject.toml
    └── no deps

T4: Env var support (RELEASEKIT_AI_MODEL, RELEASEKIT_AI_PROVIDER)
    └── T2

T5: Prompt engineering (system prompt + output instructions)
    └── T1

T6: Core summarize.py (Genkit init, generate, retry)
    └── T1, T2, T3, T5

T7: Content-hash caching
    └── T6

T8: Fallback logic (summarize-or-truncate)
    └── T6, T7

T9: Wire into prepare.py (_build_pr_body)
    └── T8

T10: Wire into release_notes.py (GitHub Release body)
    └── T8

T11: CLI flags (--summarize, --no-summarize, --model)
    └── T4, T9

T12: Tests — output schema
    └── T1

T13: Tests — config schema
    └── T2, T4

T14: Tests — summarize.py (mock model)
    └── T6, T7

T15: Tests — prepare.py integration
    └── T9

T16: Tests — release_notes.py integration
    └── T10

T17: Tests — CLI flags
    └── T11

T18: Documentation (README, roadmap status)
    └── T11, T17
```

### Reverse Topological Sort (leaf-first)

```
Level 0 (no deps):     T1, T2, T3
Level 1 (deps on L0):  T4, T5, T12
Level 2 (deps on L1):  T6, T13
Level 3 (deps on L2):  T7, T14
Level 4 (deps on L3):  T8
Level 5 (deps on L4):  T9, T10
Level 6 (deps on L5):  T11, T15, T16
Level 7 (deps on L6):  T17, T18
```

---

## Implementation Phases

### Phase A: Foundation (Level 0–1) — No Genkit dependency yet

**Goal**: Data models, config schema, and prompt template. All pure
Python, fully testable without Genkit or Ollama.

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **T1** | `schemas_ai.py` | `ReleaseSummary` + `ReleaseStats` Pydantic models. JSON schema export for prompt instruction. | ~60 |
| **T2** | `config.py` | Add `[ai]` section support: `AiConfig` dataclass with `provider`, `model`, `temperature`, `max_output_tokens`. Validation. | ~80 |
| **T3** | `pyproject.toml` | Add `genkit`, `genkit-plugin-ollama`, `genkit-plugin-google-genai` as **optional** deps under `[project.optional-dependencies] ai = [...]`. | ~10 |
| **T4** | `config.py` | Env var overrides: `RELEASEKIT_AI_PROVIDER`, `RELEASEKIT_AI_MODEL`. Priority: CLI > env > config > default. | ~30 |
| **T5** | `prompts.py` | System prompt template + user prompt builder. Takes changelog data dict, returns formatted prompt. Few-shot reference output section. | ~100 |
| **T12** | `tests/rk_schemas_ai_test.py` | Test schema validation, JSON schema export, field constraints. | ~40 |

**Deliverable**: `ReleaseSummary` schema is defined, config reads
`[ai]` section, prompt templates are ready. No runtime Genkit
dependency yet.

**Verify**: `pytest tests/rk_schemas_ai_test.py tests/rk_config_test.py` passes.

---

### Phase B: Core Summarization (Level 2–3) — Genkit integration

**Goal**: `summarize.py` module that accepts changelogs and returns
a `ReleaseSummary`. Uses Genkit with a mock model in tests.

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **T6** | `summarize.py` | Core module. `summarize_changelogs(changelogs, config) -> ReleaseSummary`. Lazy Genkit init (import-time guard for optional dep). Provider selection. Structured output via `ai.generate(output=ReleaseSummary)`. Retry on transient failures. | ~200 |
| **T7** | `summarize.py` | Content-hash cache. SHA-256 of sorted changelog content → cached `ReleaseSummary` JSON on disk (`.releasekit-cache/summaries/`). Skip re-summarization if hash matches. | ~60 |
| **T13** | `tests/rk_config_test.py` | Test `[ai]` config parsing, env var overrides, defaults. | ~50 |
| **T14** | `tests/rk_summarize_test.py` | Test with mock Genkit model. Verify prompt construction, schema compliance, caching, retry logic, graceful import failure. | ~120 |

**Key design for T6** — lazy import with CI-optimized defaults:

```python
# summarize.py

# CI-friendly default: gemma3:4b is ~2.3 GB (vs 12b at ~8 GB).
# Fast download, fast inference, good enough for structured summarization.
_DEFAULT_PROVIDER = 'ollama'
_DEFAULT_MODEL = 'gemma3:4b'

def _get_ai():
    """Lazy-init Genkit. Returns None if genkit is not installed."""
    try:
        from genkit import Genkit  # noqa: PLC0415
        ...
    except ImportError:
        return None
```

This keeps `genkit` as an optional dependency — releasekit works
without it (falls back to truncation).

**Deliverable**: `summarize_changelogs()` works end-to-end with Ollama
(manual test) and with a mock model (automated test).

**Verify**:
- `pytest tests/rk_summarize_test.py` passes (mock model).
- Manual: `ollama pull gemma3:12b && python -c "from releasekit.summarize import ..."` works.

---

### Phase C: Integration (Level 4–5) — Wire into existing modules

**Goal**: Summarization integrated into `prepare.py` and
`release_notes.py` with graceful fallback.

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **T8** | `summarize.py` | `summarize_or_truncate()` — orchestrator function. Tries AI summarization, falls back to existing `_build_pr_body()` truncation logic on failure. Returns `(body: str, used_ai: bool)`. | ~40 |
| **T9** | `prepare.py` | Update `_build_pr_body()` call site. When `config.ai.provider` is set and `--summarize` is active, call `summarize_or_truncate()` instead of the truncation path. | ~30 |
| **T10** | `release_notes.py` | Add `summarize_release_notes()` function that uses AI summary for the GitHub Release body (no char limit). Full changelogs in `<details>` below. | ~50 |

**Fallback chain in T8**:

```
1. Try AI summarization (summarize_changelogs)
   ├── Success → return AI summary
   └── Failure (ImportError, ConnectionError, timeout, bad output)
       │
       ▼
2. Fall back to truncation (_build_pr_body current logic)
   └── Always succeeds (no external dependency)
```

**Deliverable**: `releasekit prepare` uses AI when available, falls
back silently when not.

**Verify**: `pytest tests/rk_prepare_test.py tests/rk_release_notes_test.py` passes.

---

### Phase D: CLI + Polish (Level 6–7) — User-facing flags

**Goal**: CLI flags, full test coverage, documentation.

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **T11** | `cli.py` | Add `--summarize` (flag, default off initially), `--no-summarize`, `--model <provider/model>` to `prepare` subcommand. | ~40 |
| **T15** | `tests/rk_prepare_test.py` | Integration tests: AI path (mock), truncation path, fallback on failure. | ~60 |
| **T16** | `tests/rk_release_notes_test.py` | Test `summarize_release_notes()` with mock model. | ~40 |
| **T17** | `tests/rk_cli_test.py` | Test `--summarize`, `--no-summarize`, `--model` flag parsing. | ~30 |
| **T18** | `README.md`, `roadmap.md` | Document AI summarization config, CLI flags, supported models. Update Phase 10 status. | ~50 |

**Deliverable**: Feature is complete, documented, and tested.

**Verify**: Full test suite passes, `bin/lint` clean.

---

## Summary Table

| Phase | Roadmap Phase | Tasks | Deps | Est. Lines | Key Risk |
|-------|--------------|-------|------|-----------|----------|
| **A: Foundation** | 10 | T1–T5, T12 | None | ~320 | None (pure Python) |
| **B: Core** | 10 | T6–T7, T13–T14 | Phase A | ~430 | Genkit optional import, mock model fidelity |
| **C: Integration** | 10 | T8–T10 | Phase B | ~120 | Fallback correctness |
| **D: CLI + Polish** | 10 | T11, T15–T18 | Phase C | ~220 | None |
| **E: Changelog Intel** | 11 | E1–S3 | Phase D | ~1,090 | Diff size, model context windows |
| **F: Content Gen** | 12 | M1–H3 | Phase D (+11 optional) | ~980 | Migration code quality |
| **G: Final Polish** | 10–12 | Docs, integration tests | Phase E+F | ~100 | None |
| **Total** | — | **51 tasks** | — | **~3,260** | — |

---

## File Layout (all AI files)

```
src/releasekit/
├── schemas_ai.py            # T1: ReleaseSummary, ReleaseStats, BreakingChangeReport,
│                            #     ClassificationReport, MigrationEntry, SecurityAdvisory
├── prompts.py               # T5: System/user prompt templates (all features)
├── summarize.py             # T6–T8: Core summarization + cache + fallback
├── enhance.py               # E1: Changelog enhancement (commit → user-friendly)
├── detect_breaking.py       # B1: Breaking change detection from diffs
├── classify.py              # C1: Semantic version classification
├── scope.py                 # S1: Commit scoping for multi-package commits
├── migration.py             # M1: Migration guide generation
├── announce_ai.py           # A1: Platform-tailored announcements
├── advisory.py              # V1: Security advisory drafting
├── hints_ai.py              # H1: Contextual error hint generation
├── config.py                # T2, T4: [ai] section (existing file, updated)
├── prepare.py               # T9: Wire AI into _build_pr_body (existing)
├── release_notes.py         # T10: AI summary for GitHub Release (existing)
├── changelog.py             # E2: Wire enhancement (existing)
├── versioning.py            # B3, C3, S2: Wire intelligence (existing)
├── announce.py              # A2: Wire tailoring (existing)
├── errors.py                # H2: Wire AI hints (existing)
└── cli.py                   # T11+: All --ai flags (existing)

tests/
├── rk_schemas_ai_test.py    # T12: All AI dataclass schemas
├── rk_summarize_test.py     # T14: Summarization + caching
├── rk_enhance_test.py       # E4: Changelog enhancement
├── rk_detect_breaking_test.py # B6: Breaking change detection
├── rk_classify_test.py      # C4: Version classification
├── rk_scope_test.py         # S3: Commit scoping
├── rk_migration_test.py     # M5: Migration guides
├── rk_announce_ai_test.py   # A4: Announcement tailoring
├── rk_advisory_test.py      # V4: Security advisory
├── rk_hints_ai_test.py      # H3: Error hints
├── rk_config_test.py        # T13 (existing, updated)
├── rk_prepare_test.py       # T15 (existing, updated)
├── rk_release_notes_test.py # T16 (existing, updated)
└── rk_cli_test.py           # T17 (existing, updated)
```

---

## Config Reference

```toml
# releasekit.toml

[ai]
# Provider: "ollama" (default), "google-genai", "vertex-ai", "anthropic"
provider         = "ollama"

# Model name (provider-specific).
# Ollama (CI-friendly, no API key):
#   gemma3:4b   — ~2.3 GB, fast, good structured output (DEFAULT)
#   gemma3:1b   — ~815 MB, very fast, min quality for summaries
#   qwen2.5:3b  — ~1.9 GB, strong at structured tasks
#   llama3.2:3b — ~2.0 GB, Meta's compact model
#   phi4-mini   — ~2.2 GB, Microsoft's small reasoning model
# Ollama (local dev, higher quality):
#   gemma3:12b  — ~8 GB, best local quality
#   llama3.1:8b — ~4.7 GB, strong general-purpose
#   qwen2.5:7b  — ~4.4 GB, excellent structured output
#   phi4:14b    — ~9 GB, best local reasoning
# Cloud (API key required):
#   gemini-2.0-flash       — Google GenAI / Vertex AI
#   claude-3-5-sonnet      — Anthropic
model            = "gemma3:4b"

# Temperature (0.0–1.0). Lower = more factual for summarization.
temperature      = 0.2

# Maximum output tokens.
max_output_tokens = 4096

# Enable/disable AI features globally.
enabled          = true

# Which AI features to enable (all enabled when [ai] is present).
# Set to false to disable individual features.
[ai.features]
summarize        = true    # Phase 10: Release note summarization
enhance          = true    # Phase 11a: Changelog enhancement
detect_breaking  = true    # Phase 11b: Breaking change detection
classify         = false   # Phase 11c: Semantic version classification (advisory)
scope            = false   # Phase 11d: Commit scoping (advisory)
migration_guide  = true    # Phase 12a: Migration guide generation
tailor_announce  = false   # Phase 12b: Announcement tailoring
draft_advisory   = false   # Phase 12c: Security advisory drafting
ai_hints         = false   # Phase 12d: Contextual error hints
```

**Environment variable overrides**:

```bash
RELEASEKIT_AI_PROVIDER=google-genai
RELEASEKIT_AI_MODEL=gemini-2.0-flash
RELEASEKIT_AI_ENABLED=false
```

**CLI flag overrides** (highest priority):

```bash
releasekit prepare --summarize                              # Force on
releasekit prepare --no-summarize                           # Force off
releasekit prepare --model ollama/gemma3:4b                 # Override model
releasekit prepare --model google-genai/gemini-2.0-flash    # Cloud model
releasekit prepare --enhance-changelog                      # Enhance entries
releasekit prepare --migration-guide                        # Generate guides
releasekit check --detect-breaking                          # Scan for missed breaks
releasekit version --ai-classify                            # Second-opinion bumps
releasekit announce --ai-tailor                             # Platform-tailored
releasekit advisory --draft                                 # Draft GHSA from OSV
```

---

## Testing Strategy

1. **Unit tests (mock model)** — All tests use a mock Genkit model
   that returns canned responses. No Ollama or network required.
   This is the standard Genkit testing pattern.

2. **Integration test (manual)** — Run `releasekit prepare --summarize
   --dry-run` against the real genkit workspace with Ollama running.
   Verify output quality manually.

3. **Fallback test** — Verify that when `genkit` is not installed
   (or Ollama is down), every feature silently falls back to its
   non-AI behavior without errors.

4. **Cache test** — Run summarization twice with same changelogs,
   verify second call returns cached result (no model invocation).

---

## Ollama Model Caching in CI

Ollama stores downloaded models as blob files under `~/.ollama/models/`.
This directory is fully cacheable — no server state, just files.

### GitHub Actions cache

```yaml
# .github/workflows/release.yml

- name: Cache Ollama model
  uses: actions/cache@v4
  with:
    path: ~/.ollama/models
    # Key on the model name — cache busts only when we change models.
    key: ollama-gemma3-4b

- name: Install Ollama
  run: curl -fsSL https://ollama.com/install.sh | sh

- name: Pull model (cache miss only)
  run: ollama pull gemma3:4b
  # On cache hit, this is a no-op (~0s).
  # On cache miss, downloads ~2.3 GB (~30s on GitHub runners).

- name: Prepare release
  run: releasekit prepare --summarize
```

### Model size comparison (CI impact)

| Model | Download | Cached pull | Inference (67 pkgs) | Quality |
|-------|----------|-------------|--------------------|---------
| `gemma3:1b` | ~815 MB | ~0s | ~5s | ★★★ |
| `gemma3:4b` | ~2.3 GB | ~0s | ~10s | ★★★★ |
| `qwen2.5:3b` | ~1.9 GB | ~0s | ~8s | ★★★★ |
| `gemma3:12b` | ~8 GB | ~0s | ~30s | ★★★★★ |

**Recommendation**: `gemma3:4b` is the sweet spot for CI — fast enough
to not slow down the release pipeline, small enough that even a cache
miss is tolerable (~30s on GitHub's 10 Gbps runners), and capable
enough for high-quality structured summarization.

For **local development** with higher-quality output, users can
override to `gemma3:12b` in their `releasekit.toml` or via
`--model ollama/gemma3:12b`.

### Docker-based caching (alternative)

For self-hosted runners or Cloud Build, bake the model into a custom
image:

```dockerfile
FROM ollama/ollama:latest
RUN ollama pull gemma3:4b
```

---

## Phase E: Changelog & Version Intelligence (Roadmap Phase 11)

**Goal**: Use the Phase A–D infrastructure to improve changelog
quality and version accuracy. All features share the same model
config, Genkit lazy init, and caching layer.

**Prerequisite**: Phase D complete.

### E1: Changelog Enhancement

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **E1** | `enhance.py` | `enhance_changelog(changelog, config) -> Changelog`. Batch-rewrites all `ChangelogEntry.description` fields into user-friendly sentences via a single `ai.generate()` call. Preserves PR/issue references. Returns enhanced changelog with originals in metadata. | ~120 |
| **E2** | `changelog.py` | Add `enhance` kwarg to `generate_changelog()`. When set, pipes output through `enhance_changelog()` before rendering. | ~20 |
| **E3** | `cli.py` | Add `--enhance-changelog` flag to `prepare` and `tag` subcommands. | ~15 |
| **E4** | `tests/rk_enhance_test.py` | Mock model tests: batch rewrite, reference preservation, fallback on failure, empty changelog, idempotency. | ~80 |

### E2: Breaking Change Detection

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **B1** | `detect_breaking.py` | `detect_breaking_changes(commits, vcs, config) -> list[BreakingChangeReport]`. For each commit not tagged as breaking, gets diff via `vcs.diff(sha)`, sends to AI for classification. Returns `BreakingChangeReport` with confidence score and affected symbols. | ~180 |
| **B2** | `detect_breaking.py` | `BreakingChangeReport` dataclass: `sha`, `message`, `is_breaking`, `confidence`, `reason`, `affected_symbols`. | ~30 |
| **B3** | `versioning.py` | Validation pass. After conventional commit parsing, run `detect_breaking_changes()` on non-breaking commits. Warn if AI detects missed breaking changes (never auto-upgrade bump). | ~40 |
| **B4** | `checks/` | Add `ai_breaking_change` check to `releasekit check`. Scans unreleased commits. | ~50 |
| **B5** | `cli.py` | Add `--detect-breaking` to `version` and `check` subcommands. | ~15 |
| **B6** | `tests/rk_detect_breaking_test.py` | Mock tests: signature change, removed function, renamed class, false positive (internal rename), confidence thresholds. | ~120 |

### E3: Semantic Version Classification

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **C1** | `classify.py` | `classify_commits(commits, vcs, config) -> list[ClassificationReport]`. Gets diff, classifies as patch/minor/major. Flags disagreements with conventional commit prefix. | ~120 |
| **C2** | `classify.py` | `ClassificationReport` dataclass: `sha`, `conventional_bump`, `ai_bump`, `confidence`, `reason`, `disagreement`. | ~25 |
| **C3** | `versioning.py` | Optional validation pass. Log warnings for disagreements. `--ai-classify` enables it. | ~30 |
| **C4** | `tests/rk_classify_test.py` | Mock tests: agreement, disagreement, missing prefix, confidence filtering. | ~80 |

### E4: Commit Scoping

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **S1** | `scope.py` | `scope_commit(commit, packages, vcs, config) -> list[ScopeResult]`. Ranks packages by relevance for multi-package commits. | ~80 |
| **S2** | `versioning.py` | Use AI scoping when a commit touches multiple package paths. Falls back to path heuristic. | ~25 |
| **S3** | `tests/rk_scope_test.py` | Mock tests: single-package, multi-package, cross-cutting refactor, utility file. | ~60 |

**Phase E totals**: 17 tasks, ~1,090 est. lines.

---

## Phase F: Content Generation (Roadmap Phase 12)

**Goal**: Generate user-facing content from release data.

**Prerequisite**: Phase D complete. Phase E optional but enriches
output (breaking change data feeds migration guides).

### F1: Migration Guide Generation

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **M1** | `migration.py` | `generate_migration_guide(breaking_changes, vcs, config) -> MigrationGuide`. Gets diff for each breaking change, generates before/after code with explanation. Structured output: `MigrationEntry(change, before_code, after_code, explanation)`. | ~150 |
| **M2** | `migration.py` | `MigrationGuide` + `MigrationEntry` dataclasses. `render_migration_guide(guide) -> str` as markdown. | ~40 |
| **M3** | `release_notes.py` | Add "Migration Guide" section after "Breaking Changes" in release notes. | ~30 |
| **M4** | `cli.py` | Add `--migration-guide` flag to `prepare` and `tag`. | ~10 |
| **M5** | `tests/rk_migration_test.py` | Mock tests: function rename, param change, type change, no breaks (empty). | ~80 |

### F2: Announcement Tailoring

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **A1** | `announce_ai.py` | `tailor_announcement(summary, platform, config) -> str`. Platform-specific prompts: `slack` (markdown + emoji), `twitter` (280 chars), `discord` (community), `linkedin` (professional). | ~120 |
| **A2** | `announce.py` | Wire into `send_announcement()`. When `--ai-tailor` is set, replace template rendering with AI content. | ~30 |
| **A3** | `cli.py` | Add `--ai-tailor` to `announce`. | ~10 |
| **A4** | `tests/rk_announce_ai_test.py` | Mock tests per platform: char limits, markdown, tone. | ~80 |

### F3: Security Advisory Drafting

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **V1** | `advisory.py` | `draft_advisory(osv_record, config) -> SecurityAdvisory`. Generates: summary, impact, affected versions, remediation, CVSS plain-English explanation. | ~120 |
| **V2** | `advisory.py` | `SecurityAdvisory` dataclass + `render_advisory()` as GHSA markdown. | ~40 |
| **V3** | `cli.py` | Add `releasekit advisory --draft` subcommand. | ~30 |
| **V4** | `tests/rk_advisory_test.py` | Mock tests: critical CVE, moderate issue, multiple versions. | ~60 |

### F4: Contextual Error Hints

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **H1** | `hints_ai.py` | `generate_hint(error, context, config) -> str`. Context: config values, recent logs, environment (CI/local), error code. Returns actionable hint. | ~100 |
| **H2** | `errors.py` | Wire into `render_error()` when `--verbose` is active and AI is available. Append below static hint. | ~20 |
| **H3** | `tests/rk_hints_ai_test.py` | Mock tests: publish failed, build failed, config error. | ~60 |

**Phase F totals**: 16 tasks, ~980 est. lines.

---

## Phase G: Final Polish (All Roadmap Phases 10–12)

| Task | Module | What | Est. Lines |
|------|--------|------|-----------|
| **G1** | `README.md` | Document all AI features, config, CLI flags, supported models. | ~50 |
| **G2** | `roadmap.md` | Update Phase 10–12 status to ✅ Complete. | ~10 |
| **G3** | Integration tests | End-to-end test: `prepare --summarize --enhance-changelog --migration-guide --detect-breaking` with mock model. | ~40 |

**Phase G totals**: 3 tasks, ~100 est. lines.

---

## Cross-Phase Dependency Graph

```
Phase A: Foundation (schemas, config, prompts)
    │
    ▼
Phase B: Core Summarization (summarize.py + cache)
    │
    ▼
Phase C: Integration (prepare.py + release_notes.py)
    │
    ▼
Phase D: CLI + Polish (--summarize flags, tests, docs)
    │
    ├──────────────────────────────┐
    ▼                              ▼
Phase E: Changelog Intel        Phase F: Content Gen
(11a enhance, 11b breaking,     (12a migration, 12b announce,
 11c classify, 11d scope)        12c advisory, 12d hints)
    │                              │
    │    12a optionally uses       │
    │    11b breaking data         │
    │         │                    │
    └─────────┼────────────────────┘
              ▼
         Phase G: Final Polish
         (docs, integration tests)
```

**Key insight**: Phases E and F are **independent of each other** and
can be worked on in parallel. They both depend only on Phase D
(the core summarization infrastructure). Phase 12a (migration guides)
is enriched by Phase 11b (breaking change detection) but works
without it by using conventional commit `BREAKING CHANGE:` footers.

---

## Grand Total

| Phase | Roadmap | Tasks | Est. Lines | Focus |
|-------|---------|-------|-----------|-------|
| A | 10 | 6 | ~320 | Foundation |
| B | 10 | 4 | ~430 | Core summarization |
| C | 10 | 3 | ~120 | Wire into existing modules |
| D | 10 | 5 | ~220 | CLI + tests |
| E | 11 | 17 | ~1,090 | Changelog & version intelligence |
| F | 12 | 16 | ~980 | Content generation |
| G | 10–12 | 3 | ~100 | Final polish |
| **Total** | — | **54** | **~3,260** | — |

---

## Open Questions

1. **Default on or off?** — Should `--summarize` be opt-in (flag) or
   default-on when `[ai]` is configured? Recommendation: **opt-in
   initially** (`--summarize` flag), then default-on in a future
   release once battle-tested.

2. **Cache location** — `.releasekit-cache/summaries/` in the workspace
   root? Or `~/.cache/releasekit/`? Recommendation: workspace-local
   so CI builds are isolated.

3. **Prompt tuning** — Should the system prompt be configurable via
   `releasekit.toml`? Recommendation: **no** (too complex). Ship with
   a well-tested default prompt. Allow template override in a future
   release if needed.

4. **Token budget** — With 67 packages × ~500 lines of changelog,
   the input might exceed model context windows. Recommendation:
   pass per-package *summaries* (first heading + top 10 entries) to
   the model, not full changelogs. Full changelogs go in `<details>`.

5. **Feature granularity** — Should each AI feature have its own
   `[ai.features.X]` toggle, or should `[ai] enabled = true` enable
   all? Recommendation: Per-feature toggles with sensible defaults
   (summarize + enhance + detect_breaking on, others off).

