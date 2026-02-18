# releasekit

Release orchestration for polyglot monorepos — publish packages in
topological order with dependency-triggered scheduling, ephemeral version
pinning, retry with jitter, crash-safe file restoration, and post-publish
checksum verification. Supports Python (uv), JavaScript (pnpm), Go,
Dart (Pub), Java (Maven/Gradle), Kotlin (Gradle), Clojure (Leiningen/deps.edn),
Rust (Cargo), and Bazel workspaces — all through protocol-based backends.

## Why This Tool Exists

Modern polyglot monorepos contain dozens (or hundreds) of packages with
inter-dependencies. Publishing them to a registry requires dependency-ordered
builds with ephemeral version pinning — and no existing tool does this well
across ecosystems.

`uv publish` is a **single-package** command. It publishes one wheel or
sdist to PyPI. It does not understand workspaces, dependency graphs, or
multi-package release orchestration. releasekit fills that gap:

| Feature | `uv publish` | `releasekit` |
|---------|:--:|:--:|
| Publish a single package | ✅ | ✅ (calls `uv publish` internally) |
| Dependency graph ordering | ❌ | ✅ topological sort |
| Multi-package workspace publish | ❌ | ✅ all packages in order |
| Version bump computation | ❌ | ✅ git-based semver |
| Transitive dependency propagation | ❌ | ✅ patch bump dependents |
| Concurrency within topo levels | ❌ | ✅ parallel within a level |
| Pre/post-publish checks | ❌ | ✅ preflight + smoke test |
| Retry with backoff | ❌ | ✅ configurable |
| Exclude lists / groups | ❌ | ✅ `exclude`, `exclude_publish`, `exclude_bump` |
| Git tagging | ❌ | ✅ per-package + umbrella |
| Changelog generation | ❌ | ✅ from conventional commits |
| Release manifest | ❌ | ✅ JSON record of what shipped |
| Crash-safe resume | ❌ | ✅ state file + `--resume` |
| SIGUSR1/SIGUSR2 pause/resume | ❌ | ✅ live scheduler control |

`uv publish` is the low-level primitive. releasekit is the orchestrator
that calls it per-package at the right time in the right order.

See [docs/docs/roadmap.md](docs/docs/roadmap.md) for the full design rationale and
implementation plan.

## How Does releasekit Compare?

| Feature | releasekit | release-please | semantic-release | release-it | changesets | nx release | knope | goreleaser |
|---------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 🏗️ Monorepo | ✅ | ✅ | ❌ | ⚠️ | ✅ | ✅ | ✅ | ❌ |
| 🌐 Polyglot (Py/JS/Go/Rust/Java/Dart/Bazel + more planned) | ✅ | ✅ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ❌ |
| 📝 Conventional Commits | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| 📦 Changeset files | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| 🔀 Dependency graph | ✅ | ⚠️ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| 📊 Topo-sorted publish | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 🩺 Health checks (42) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔧 Auto-fix (`--fix`) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🏭 Multi-forge | ✅ GH/GL/BB | ❌ GH | ✅ GH/GL/BB | ✅ GH/GL | ❌ GH | ❌ | ⚠️ GH/Gitea | ❌ GH |
| 🏷️ Pre-release | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 🧪 Dry-run | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| ⏪ Rollback | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔮 Version preview | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| 📈 Graph visualization | ✅ 8 formats | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 🐚 Shell completions | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| 🔍 Error explainer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔄 Retry with backoff | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔒 Release lock | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ✍️ Signing / provenance | ✅ Sigstore | ❌ | ⚠️ npm | ❌ | ❌ | ❌ | ❌ | ✅ GPG/Cosign |
| 📋 SBOM | ✅ CycloneDX+SPDX | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 📢 Announcements (6 channels) | ✅ Slack/Discord/Teams/Twitter/LinkedIn/Webhook | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 🤖 AI release notes | ✅ Genkit | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🏷️ AI release codenames | ✅ 28 themes | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🛡️ AI safety guardrails | ✅ 3-layer | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 📊 Plan profiling | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔭 OpenTelemetry tracing | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔄 Migrate from alternatives | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🔁 Continuous deploy mode | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| ⏰ Cadence / scheduled releases | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🪝 Lifecycle hooks | ✅ | ❌ | ✅ plugins | ✅ | ❌ | ❌ | ❌ | ✅ |
| 🌿 Branch → channel mapping | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 📅 CalVer support | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🛡️ OSPS Baseline compliance | ✅ L1–L3 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🌍 Ecosystem-specific security | ✅ 6 ecosystems | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ⏭️ Per-package check skipping | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 🤖 AI-powered features | ✅ Genkit | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Legend:** ✅ = supported, ⚠️ = partial, ❌ = not supported, 🔜 = planned

See [docs/docs/competitive-gap-analysis.md](docs/docs/competitive-gap-analysis.md) for
the full analysis with issue tracker references, and
[docs/docs/roadmap.md](docs/docs/roadmap.md) for the detailed roadmap with dependency graphs
and execution phases.

## Screenshots

<!-- Plan output showing version bumps and publish order -->

```text
$ releasekit plan --format full
┌──────────────────────────────────────────────────────────────┐
│ Level 0 (parallel)                                           │
│   📦 genkit 0.9.0 → 0.10.0 (minor)                          │
│                           │                                  │
│                           ▼                                  │
├──────────────────────────────────────────────────────────────┤
│ Level 1 (parallel)                                           │
│   📦 genkit-plugin-google-genai 0.9.0 → 0.10.0 (minor)      │
│   📦 genkit-plugin-vertex-ai 0.9.0 → 0.10.0 (minor)         │
│   📦 genkit-plugin-firebase 0.9.0 → 0.10.0 (minor)          │
└──────────────────────────────────────────────────────────────┘

     Level  Package                       Current  Next    Bump   Status    Reason
     ─────  ───────                       ───────  ────    ────   ──────    ──────
  📦 0      genkit                        0.9.0    0.10.0  minor  included  feat: add streaming support
  📦 1      genkit-plugin-google-genai    0.9.0    0.10.0  minor  included  dependency bump
  📦 1      genkit-plugin-vertex-ai       0.9.0    0.10.0  minor  included  dependency bump
  📦 1      genkit-plugin-firebase        0.9.0    0.10.0  minor  included  dependency bump
  ⏭️  1      genkit-plugin-ollama          0.9.0    —       none   skipped   no changes

Total: 5 packages (4 included, 1 skipped)
```

<!-- Health check output with Rust-style diagnostics -->

```text
$ releasekit check
  ✓ dependency_cycles         No circular dependencies
  ✓ lockfile_staleness        uv.lock is up to date
  ✓ type_markers              All packages have py.typed
  ⚠ version_consistency       genkit-plugin-foo has version 0.4.0 (expected 0.5.0)
     --> plugins/foo/pyproject.toml:3
      |
    3 | version = "0.4.0"
      |           ^^^^^^^ expected 0.5.0
      |
     = hint: Run 'releasekit check --fix' or update the version manually.
  ✓ naming_convention         All names match pattern
  ✓ metadata_completeness     All required fields present

  42 checks run: 41 passed, 1 warning, 0 errors
```

<!-- Compliance report -->

```text
$ releasekit compliance
  ID             Control                          Level  Status
  ─────────────  ───────────────────────────────  ─────  ──────
  OSPS-SCA-01    SBOM generation                  L1     ✅ met
  OSPS-GOV-01    Security policy (SECURITY.md)    L1     ✅ met
  OSPS-LEG-01    License declared                 L1     ✅ met
  OSPS-SCA-02    Signed release artifacts         L2     ✅ met
  OSPS-SCA-03    Provenance attestation           L2     ✅ met
  OSPS-BLD-01    Build isolation (SLSA Build L3)  L3     ✅ met
  OSPS-BLD-02    Signed provenance                L3     ✅ met
  ECO-PY-01      PEP 561 type markers             L1     ✅ met
  ECO-PY-02      PEP 740 attestations             L2     ❌ gap

  8/9 controls met.
```

## Getting Started

```bash
# 1. Install (or run directly with uvx)
uv tool install releasekit

# 2. Initialize config in your workspace root
releasekit init

# 3. Preview what would happen
releasekit plan

# 4. Publish all changed packages
releasekit publish

# 5. Enable shell completions (bash, zsh, or fish)
eval "$(releasekit completion bash)"
```

Or run without installing:

```bash
uvx releasekit discover
uvx releasekit graph --format table
uvx releasekit check
```

### GitHub Action

Use the reusable composite action to run any releasekit command in CI
with zero setup — Python, uv, git config, output parsing, and job
summaries are handled automatically:

```yaml
- uses: ./py/tools/releasekit  # or your-org/releasekit@v1
  with:
    command: release
    workspace: py
    dry-run: ${{ env.DRY_RUN }}
```

The action supports all commands (`prepare`, `release`, `publish`,
`rollback`, `plan`, `discover`, etc.) and all ecosystems. It captures
outputs (`release-url`, `pr-url`, `first-tag`, `has-bumps`) and writes
a GitHub Actions Job Summary with rollback links automatically.

See the [sample workflows](github/workflows/) for production-ready
templates for Python/uv, Go, JS/pnpm, Rust/Cargo, Dart/pub, and
Java/Gradle.

### CI Authentication

The workflow `auth` job supports three authentication modes in
priority order. Use the `auth_method` dropdown in the workflow
dispatch UI to override auto-detection (default: `auto`).

| Mode | Priority | Secrets/Variables | CLA | CI Trigger |
|------|:--------:|-------------------|:---:|:----------:|
| **GitHub App** | 1st | `RELEASEKIT_APP_ID` (variable) + `RELEASEKIT_APP_PRIVATE_KEY` (secret) | ✅ | ✅ |
| **PAT** | 2nd | `RELEASEKIT_TOKEN` (secret) | ✅ | ✅ |
| **GITHUB_TOKEN** | 3rd | Built-in (no setup) | ⚠️ | ❌ |

**Auto** (`auth_method: auto`) tries App first, then PAT, then
GITHUB_TOKEN — based on which secrets/variables are configured.

#### Option A: GitHub App (recommended)

1. Create a GitHub App at your org settings → Developer settings → GitHub Apps
2. Permissions: **Contents** (Read & write), **Pull requests** (Read & write)
3. Install the App on the target repository
4. Add repo **variable**: `RELEASEKIT_APP_ID` = the App ID
5. Add repo **secret**: `RELEASEKIT_APP_PRIVATE_KEY` = the PEM private key

#### Option B: Personal Access Token

1. Create a fine-grained PAT scoped to the repository
2. Permissions: **Contents** (Read & write), **Pull requests** (Read & write)
3. Add repo **secret**: `RELEASEKIT_TOKEN` = the PAT

#### Option C: GITHUB_TOKEN with CLA-signed identity

If you can't set up an App or PAT, set these repo **variables** so
that Release PR commits use your CLA-signed identity:

```
RELEASEKIT_GIT_USER_NAME  = Your Name
RELEASEKIT_GIT_USER_EMAIL = your-email@example.com
```

The GITHUB_TOKEN fallback reads these variables and uses them for
`git config user.name` and `user.email`, so CLA checks pass on
the Release PR. Without these variables, commits are attributed to
`github-actions[bot]` which may fail CLA.

> **Note:** GITHUB_TOKEN PRs will **not** trigger downstream CI
> workflows (GitHub limitation). Use App or PAT for full CI integration.

#### `auth_method` dropdown

The workflow dispatch UI includes an `auth_method` choice:

| Value | Behavior |
|-------|----------|
| `auto` | Auto-detect from configured secrets (default) |
| `app` | Force GitHub App token (fails if not configured) |
| `pat` | Force PAT (fails if not configured) |
| `github-token` | Force built-in GITHUB_TOKEN |

### Bootstrap Tags

When adopting releasekit on a repo that already has releases,
`releasekit init` automatically creates bootstrap tags so version
bumps start from the correct baseline. The init command:

1. Scans existing git tags and classifies them by workspace
2. Picks the latest tag per workspace and writes `bootstrap_sha`
3. Discovers all packages and creates per-package tags at the
   bootstrap commit for any package that doesn't already have one
4. Creates the umbrella tag if configured and missing

```bash
# Preview what init will do
releasekit init --dry-run

# Run init — scaffolds config, scans tags, creates bootstrap tags
releasekit init

# Push the created tags to the remote
git push origin --tags
```

Tags are created locally. After verifying them with `git tag -l`,
push to the remote with `git push origin --tags`.

## Commands

| Command | Description |
|---------|-------------|
| `discover` | List all workspace packages (8 graph formats + JSON) |
| `graph` | Print the dependency graph (8 output formats) |
| `plan` | Preview version bumps and publish order (formats: table, json, csv, ascii, full) |
| `publish` | Build and publish packages to registries in dependency order |
| `prepare` | Bump versions, generate changelogs, open a Release PR |
| `release` | Tag a merged Release PR and create a GitHub Release |
| `check` | Run 42 workspace health checks (`--fix` to auto-fix 22 issues) |
| `doctor` | Diagnose inconsistent state between workspace, git tags, and platform releases |
| `validate` | Run validators against release artifacts (provenance, SBOM, attestations) |
| `compliance` | Evaluate OSPS Baseline compliance (L1–L3) across all ecosystems |
| `rollback` | Delete git tags + platform releases; optionally yank from registries |
| `snapshot` | Compute snapshot/dev versions for CI preview builds |
| `promote` | Promote pre-release packages to stable (`1.0.0rc1` → `1.0.0`) |
| `should-release` | Check if a release is needed (for CI cron integration) |
| `sign` | Sign release artifacts with Sigstore (keyless OIDC) |
| `verify` | Verify Sigstore bundles and SLSA provenance |
| `verify-install` | Verify published packages are installable from the registry |
| `bump` | Bump version for one or all packages |
| `init` | Scaffold `releasekit.toml` config with auto-detected groups |
| `migrate` | Auto-detect existing tags and set `bootstrap_sha` for mid-stream adoption |
| `explain` | Look up any error code (e.g. `releasekit explain RK-GRAPH-CYCLE-DETECTED`) |
| `changelog` | Generate per-package CHANGELOG.md from Conventional Commits |
| `version` | Show computed version bumps |
| `completion` | Generate shell completion scripts (bash/zsh/fish) |

## Features

### Graph Formatters

`releasekit graph --format <fmt>` supports 8 output formats:

| Format | Output | Use case |
|--------|--------|----------|
| `ascii` | Box-drawing art | Terminal viewing |
| `csv` | RFC 4180 + UTF-8 BOM | Excel, Google Sheets, data pipelines |
| `d2` | D2 diagram DSL | `d2 render` |
| `dot` | Graphviz DOT | `dot -Tpng` / `dot -Tsvg` |
| `json` | Structured JSON | Scripting, CI, jq |
| `levels` | Simple text (default) | Quick inspection |
| `mermaid` | Mermaid flowchart | GitHub READMEs, docs |
| `table` | Markdown table | READMEs, docs, PRs |

```bash
# Render as Mermaid for a README
releasekit graph --format mermaid > deps.mmd

# Export as CSV for a spreadsheet
releasekit graph --format csv > deps.csv

# Render as Graphviz SVG
releasekit graph --format dot | dot -Tsvg -o deps.svg

# Show as a Markdown table
releasekit graph --format table
```

### AI-Powered Features (Genkit)

ReleaseKit uses [Genkit](https://github.com/firebase/genkit) for AI-powered
release intelligence. All AI features are **on by default** and degrade
gracefully when no model is available.

| Feature | What It Does | Module |
|---------|-------------|--------|
| **AI release summaries** | Structured changelog → highlights, breaking changes, stats | `summarize.py` |
| **AI release codenames** | Themed codenames (28 built-in themes) with history tracking | `codename.py` |
| **Dotprompt templates** | `.prompt` files with Handlebars templates + YAML frontmatter | `prompts/` |
| **3-layer safety** | Prompt rules + curated themes + Aho-Corasick blocklist filter | `_wordfilter.py` |
| **Custom blocklist** | Extend built-in blocked words with a project-specific file | `_wordfilter.py` |
| **10 AI feature toggles** | Per-feature on/off: summarize, codename, enhance, detect_breaking, classify, scope, migration_guide, tailor_announce, draft_advisory, ai_hints | `config.py` |
| **Model fallback chain** | Try models in order (Ollama → Google GenAI) | `ai.py` |
| **Content-hash caching** | Skip re-summarization when changelog hasn't changed | `summarize.py` |

```toml
# releasekit.toml
[ai]
models = ["ollama/gemma3:4b", "google-genai/gemini-3.0-flash-preview"]
codename_theme = "mountains"   # 28 built-in themes or any custom string
blocklist_file = ""             # custom blocked-words file (extends built-in list)

[ai.features]
summarize       = true   # AI release note summarization
codename        = true   # AI-generated release codenames
enhance         = true   # Changelog entry enhancement
detect_breaking = true   # Breaking change detection
classify        = false  # Semantic version classification
scope           = false  # Commit scoping
migration_guide = true   # Migration guide generation
tailor_announce = false  # Announcement tailoring per channel
draft_advisory  = false  # Security advisory drafting
ai_hints        = false  # Contextual error hints
```

```bash
# CLI overrides
releasekit publish --no-ai              # Disable all AI features
releasekit publish --model ollama/gemma3:12b  # Override model
releasekit publish --codename-theme galaxies  # Override theme
```

**Safety guardrails** (3 layers):
1. **Prompt rules** — System prompt enforces "safe for all audiences" with explicit constraints
2. **Curated themes** — 28 built-in themes (mountains, animals, galaxies, flowers, ...)
3. **Post-generation blocklist** — Aho-Corasick trie-based filter with word-boundary semantics rejects unsafe codenames/summaries in O(n) time. Supports exact and prefix/stem matches. Configurable via `ai.blocklist_file` to extend the built-in list

### Publish Pipeline

Each package goes through:

```
pin → build → checksum → publish → poll → verify_checksum → smoke_test → restore
```

Packages are dispatched via a **dependency-triggered queue** — each
package starts as soon as all its dependencies complete (no level-based
lockstep). Workers pull from the queue as fast as they can.

Granular control:

```bash
releasekit publish --dry-run             # Preview mode
releasekit publish --version-only        # Bump versions, skip build/publish
releasekit publish --no-tag --no-push    # Publish without tagging/pushing
releasekit publish --no-release          # Skip GitHub release creation
releasekit publish --max-retries 3       # Retry failed publishes
releasekit publish --concurrency 10      # Max parallel per level
releasekit publish --build-only          # SLSA L3: build only, no upload
releasekit publish --upload-only         # SLSA L3: upload pre-built artifacts
releasekit publish --upload-only --dist-dir dist/  # Custom artifact dir
```

On failure, the scheduler retries with exponential backoff + full jitter.
Failed packages block their dependents (fail-fast for the dependency chain).

### Workspace Initialization

```bash
releasekit init              # Auto-detect groups, write config
releasekit init --dry-run    # Preview generated config
releasekit init --force      # Overwrite existing config
```

Scaffolds `releasekit.toml` in the workspace root with auto-detected
package groups (plugins, samples, core). Also adds `.releasekit-state/`
to `.gitignore`.

### Migrate (Mid-Stream Adoption)

When adopting releasekit on a repo that already has releases, the `migrate`
command automates setting `bootstrap_sha` by scanning existing git tags:

```bash
# Preview what would be written
releasekit migrate --dry-run

# Write bootstrap_sha to releasekit.toml
releasekit migrate
```

The command:
1. Scans all git tags in the repo.
2. Classifies each tag against workspace `tag_format`, `umbrella_tag`,
   and `secondary_tag_format` patterns.
3. Picks the latest semver tag per workspace.
4. Resolves the commit SHA the tag points to.
5. Writes `bootstrap_sha` into `releasekit.toml` (comment-preserving).

### Rollback

```bash
releasekit rollback genkit-v0.5.0                      # Delete tag + GitHub release
releasekit rollback genkit-v0.5.0 --all-tags            # Delete ALL tags from the release
releasekit rollback genkit-v0.5.0 --all-tags --yank     # Also yank from registries
releasekit rollback genkit-v0.5.0 --dry-run             # Preview what would be deleted
```

See the [Rollback guide](docs/docs/guides/rollback.md) for the full
one-click-from-GitHub-Release workflow.

### Rust-Style Diagnostics

All errors and warnings use Rust-compiler-style formatting:

```
error[RK-GRAPH-CYCLE-DETECTED]: Circular dependency detected in the workspace dependency graph.
  |
  = hint: Run 'releasekit check' to identify the cycle.
```

Every error code can be looked up:

```bash
releasekit explain RK-PREFLIGHT-DIRTY-WORKTREE
```

### Shell Completions

```bash
# Bash — add to ~/.bashrc
eval "$(releasekit completion bash)"

# Zsh — add to ~/.zshrc
eval "$(releasekit completion zsh)"

# Fish — save to completions dir
releasekit completion fish > ~/.config/fish/completions/releasekit.fish
```

### Health Checks

`releasekit check` runs 42 checks split into two categories:

**Universal checks** (15 — always run):
- `cycles` — circular dependency chains
- `self_deps` — package depends on itself
- `orphan_deps` — internal dep not in workspace
- `missing_license` — no LICENSE file
- `missing_readme` — no README.md
- `stale_artifacts` — leftover .bak or dist/ files
- `ungrouped_packages` — all packages appear in at least one `[groups]` pattern
- `lockfile_staleness` — `uv.lock` is in sync with `pyproject.toml`
- `spdx_headers` — SPDX license identifier headers in source files
- `license_compatibility` — dependency licenses compatible with project license (with transitive dep resolution via `uv.lock`)
- `deep_license_scan` — embedded/vendored code license detection
- `license_changes` — detect license changes between dependency versions
- `dual_license_choice` — dual-licensed deps (SPDX `OR`) have a documented choice
- `patent_clauses` — flag deps with patent grant/retaliation clauses (data-driven from `licenses.toml`)
- `license_text_completeness` — LICENSE file text matches declared SPDX ID

**Language-specific checks** (27 — via `CheckBackend` protocol):
- `type_markers` — py.typed PEP 561 marker
- `version_consistency` — plugin version matches core
- `naming_convention` — directory matches package name
- `metadata_completeness` — pyproject.toml required fields
- `python_version` — consistent `requires-python` across packages
- `python_classifiers` — Python version classifiers (3.10–3.14)
- `dependency_resolution` — `uv pip check` passes
- `namespace_init` — no `__init__.py` in namespace directories
- `readme_field` — publishable packages declare `readme` in `[project]`
- `changelog_url` — publishable packages have `Changelog` in `[project.urls]`
- `publish_classifier_consistency` — `exclude_publish` agrees with `Private :: Do Not Upload`
- `test_filename_collisions` — no duplicate test file paths across packages
- `build_system` — `[build-system]` present with `build-backend`
- `version_field` — `version` present or declared dynamic
- `duplicate_dependencies` — no duplicate entries in `[project.dependencies]`
- `pinned_deps_in_libraries` — libraries don't pin deps with `==`
- `requires_python` — publishable packages declare `requires-python`
- `readme_content_type` — readme file extension matches content-type
- `version_pep440` — versions are PEP 440 compliant
- `placeholder_urls` — no placeholder URLs in `[project.urls]`
- `legacy_setup_files` — no leftover `setup.py` or `setup.cfg`
- `deprecated_classifiers` — no deprecated trove classifiers
- `license_classifier_mismatch` — license classifiers match LICENSE file
- `unreachable_extras` — optional-dependencies reference valid packages
- `self_dependencies` — no package lists itself in dependencies
- `typing_classifier` — `Typing :: Typed` and `License :: OSI Approved` classifiers present
- `keywords_and_urls` — `keywords` and standard `[project.urls]` entries present
- `distro_deps` — distro packaging dep sync

The `CheckBackend` protocol enables language-specific checks across
6 ecosystems — Python, Go, JS/TS, Rust, Java/Kotlin, and Dart — each
with its own check backend and auto-fixers.

#### Source-Level Diagnostics

Health checks produce **source-level context** via `SourceContext`
objects that point to the exact file and line causing a warning or
failure. The CLI renders these as Rust-compiler-style diagnostics
with source excerpts:

```text
  ⚠️  warning[build_system]: Missing [build-system] section
   --> py/plugins/foo/pyproject.toml:1
    |
  1 | [project]
  2 | name = "foo"
    | ^^^ build-backend missing
  3 | version = "1.0"
    |
  = hint: Add [build-system] with build-backend = "hatchling.build".
```

Helpers for check authors:

- `SourceContext(path, line, key, label)` — frozen dataclass for file locations
- `find_key_line(content, key, section=)` — find 1-based line of a TOML key
- `read_source_snippet(path, line, context_lines=)` — read lines around a location

### Auto-Fixers

`releasekit check --fix` runs 22 auto-fixers:

**Universal fixers** (6):
- `fix_missing_readme` — create empty README.md
- `fix_missing_license` — copy bundled Apache 2.0 LICENSE
- `fix_stale_artifacts` — delete .bak files and dist/ directories
- `fix_missing_spdx_headers` — add SPDX license headers to source files (via `addlicense`)
- `fix_missing_license_files` — async fetch LICENSE text from SPDX list / GitHub for packages missing them
- `fix_missing_notice` — generate NOTICE file with attribution for all deps (including transitive)

**Python-specific fixers** (16 — via `PythonCheckBackend.run_fixes()`):
- `fix_publish_classifiers` — sync `Private :: Do Not Upload` with `exclude_publish`
- `fix_readme_field` — add `readme = "README.md"` to `[project]`
- `fix_changelog_url` — add `Changelog` to `[project.urls]`
- `fix_namespace_init` — delete `__init__.py` in namespace directories
- `fix_type_markers` — create `py.typed` PEP 561 markers
- `fix_deprecated_classifiers` — replace/remove deprecated classifiers
- `fix_duplicate_dependencies` — deduplicate `[project.dependencies]`
- `fix_requires_python` — add `requires-python` (inferred from classifiers)
- `fix_build_system` — add `[build-system]` with hatchling
- `fix_version_field` — add `"version"` to `dynamic` list
- `fix_readme_content_type` — fix content-type to match file extension
- `fix_placeholder_urls` — remove placeholder URLs
- `fix_license_classifier_mismatch` — fix license classifier to match LICENSE file
- `fix_self_dependencies` — remove self-referencing dependencies
- `fix_typing_classifier` — add `Typing :: Typed` and `License :: OSI Approved` classifiers
- `fix_keywords_and_urls` — add `keywords` and standard `[project.urls]` entries

### Preflight Checks

`run_preflight` gates the publish pipeline with environment checks.
Checks are split into **universal** (always run) and **ecosystem-specific**
(gated by `ecosystem` parameter):

**Universal checks:**
- Clean git worktree
- Lock file up to date
- No shallow clone
- No dependency cycles
- No stale dist/ directories
- Trusted publisher (OIDC) detection
- Version conflict check against the registry

**Python-specific checks** (`ecosystem='python'`):
- `metadata_validation` — pyproject.toml has description, license, authors
- `pip_audit` — vulnerability scan (advisory, opt-in via `run_audit=True`)

The `ecosystem` parameter enables forward-compatible extensibility: future
ecosystems (Node/npm, Rust/cargo, Go) can add their own checks (e.g.
`npm audit`, `cargo audit`, `govulncheck`) without modifying universal logic.

### Design Invariants

Every command, backend, and orchestrator must uphold these invariants.
Violations are treated as P0 bugs. Each invariant has a named key used
in tests (`tests/rk_invariants_test.py`) and documentation (`GEMINI.md`).

| Key | Invariant | One-liner |
|-----|-----------|----------|
| `INV-IDEMPOTENCY` | Idempotency | Re-running a command is always safe |
| `INV-CRASH-SAFETY` | Crash Safety / Resume | Interrupted releases resume without re-publishing |
| `INV-ATOMICITY` | Atomicity | Each publish fully succeeds or fully fails |
| `INV-DETERMINISM` | Determinism | Same inputs always produce same outputs |
| `INV-OBSERVABILITY` | Observability | Every action emits structured logs |
| `INV-DRY-RUN` | Dry-Run Fidelity | `--dry-run` exercises real code paths |
| `INV-GRACEFUL-DEGRADATION` | Graceful Degradation | Missing optional components degrade to no-ops |
| `INV-TOPO-ORDER` | Topological Correctness | Packages publish in dependency order |
| `INV-SUPPLY-CHAIN` | Supply Chain Integrity | Published artifacts are verified against checksums |

### Resume / State

Every publish run persists state to `.releasekit-state.json` after each
package completes. On crash or failure:

```bash
# Resume from where we left off
releasekit publish --resume

# Force restart from scratch
releasekit publish --fresh
```

The state file tracks:
- Per-package status (`pending`, `building`, `published`, `failed`)
- Git SHA at start (refuses to resume if HEAD changed)
- Checksums of published artifacts

### Keyboard Shortcuts

During a live publish (TTY only), single-key shortcuts are active:

| Key | Action |
|-----|--------|
| `p` | Pause — finish current packages, stop starting new ones |
| `r` | Resume — continue processing the queue |
| `q` | Cancel — graceful shutdown |
| `a` | Show all packages (no sliding window) |
| `w` | Sliding window (active + recently completed) |
| `f` | Cycle display filter: all → active → failed → all |
| `l` | Toggle log view — show per-stage event log instead of table |

### SIGUSR1/SIGUSR2 Controls

From another terminal, you can pause and resume the scheduler:

```bash
kill -USR1 <pid>   # Pause: finish current packages, stop starting new ones
kill -USR2 <pid>   # Resume: continue processing the queue
```

## Configuration

releasekit reads configuration from a standalone `releasekit.toml` file
in the workspace root. Use `releasekit init` to scaffold one:

```toml
# releasekit.toml
forge            = "github"
repo_owner       = "firebase"
repo_name        = "genkit"
default_branch   = "main"
pr_title_template = "chore(release): v{version}"

[workspace.py]
ecosystem      = "python"
tool           = "uv"              # defaults from ecosystem if omitted
root           = "py"
tag_format     = "{name}@{version}"
umbrella_tag   = "py/v{version}"
changelog      = true
smoke_test     = true
major_on_zero  = false
max_commits    = 500              # limit git log depth for large repos
extra_files    = []

exclude_publish = ["group:samples"]

[workspace.py.groups]
core = ["genkit"]
samples = ["*-hello", "*-demo", "web-*"]
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `tag_format` | `{name}/v{version}` | Git tag template |
| `umbrella_tag` | `v{version}` | Umbrella tag for the release |
| `synchronize` | `false` | Lockstep versioning (all packages same version) |
| `concurrency` | `5` | Max parallel publish workers |
| `smoke_test` | `true` | Run `python -c 'import ...'` after publish |
| `verify_checksums` | `true` | Verify SHA-256 against registry |
| `exclude` | `[]` | Glob patterns to exclude from discovery entirely |
| `exclude_publish` | `[]` | Glob patterns to skip during publish (still discovered + bumped) |
| `exclude_bump` | `[]` | Glob patterns to skip during version bumps (still discovered + checked) |
| `poll_timeout` | `300.0` | Seconds to wait for package availability |
| `max_retries` | `0` | Retry count per package on transient failure |
| `major_on_zero` | `false` | Allow `0.x → 1.0.0` on breaking changes (default: downgrade to minor) |
| `pr_title_template` | `"chore(release): v{version}"` | Template for the Release PR title. Placeholder: `{version}` |
| `extra_files` | `[]` | Extra files with version strings to bump (path or `path:regex` pairs) |
| `max_commits` | `0` | Limit git log depth (0 = unlimited; useful for large repos) |
| `versioning_scheme` | *(auto)* | `"semver"`, `"pep440"`, or `"calver"` (auto-detected from ecosystem) |

### Default Versioning Schemes

When `versioning_scheme` is not explicitly set, releasekit applies the
appropriate default based on the workspace ecosystem:

| Ecosystem | Default | Registry | Why |
|-----------|---------|----------|-----|
| `python` | `pep440` | PyPI | PyPI **requires** [PEP 440](https://peps.python.org/pep-0440/) (`1.0.0a1`, `1.0.0rc1`) |
| `js` | `semver` | npm | [Semantic Versioning 2.0.0](https://semver.org/) (`1.0.0-rc.1`) |
| `go` | `semver` | Go proxy | [Go module versioning](https://go.dev/ref/mod#versions) |
| `rust` | `semver` | crates.io | [Cargo SemVer](https://doc.rust-lang.org/cargo/reference/semver.html) |
| `dart` | `semver` | pub.dev | [Dart versioning](https://dart.dev/tools/pub/versioning) |
| `java` | `semver` | Maven Central | [Maven versioning](https://maven.apache.org/pom.html#Version) |
| `jvm` | `semver` | Maven Central | Same as Java |
| `kotlin` | `semver` | Maven Central | Same as Java |
| `clojure` | `semver` | Clojars | [Leiningen versioning](https://codeberg.org/leiningen/leiningen) |
| `bazel` | `semver` | BCR | [Bazel Central Registry](https://registry.bazel.build/) |
| `swift` | `semver` | Swift Package Index | Git-tag-based versioning (🔜 planned) |
| `ruby` | `semver` | RubyGems.org | [RubyGems versioning](https://guides.rubygems.org/patterns/) (🔜 planned) |
| `dotnet` | `semver` | NuGet Gallery | [NuGet versioning](https://learn.microsoft.com/en-us/nuget/concepts/package-versioning) (🔜 planned) |
| `php` | `semver` | Packagist | [Composer versioning](https://getcomposer.org/doc/articles/versions.md) (🔜 planned) |

Python is the only ecosystem that defaults to PEP 440 because PyPI
requires it. All other registries use or recommend Semantic Versioning.

### Per-Package Configuration

Individual packages can override workspace-level settings via
`[workspace.<label>.packages.<name>]` sections. This is useful for
mixed-ecosystem workspaces (e.g. Python + JS in one workspace):

```toml
[workspace.mono]
ecosystem = "python"
root = "."
versioning_scheme = "pep440"  # default for all packages

[workspace.mono.groups]
js-libs = ["my-js-*"]

# JS packages use semver instead of pep440
[workspace.mono.packages.js-libs]
versioning_scheme = "semver"
dist_tag = "latest"

# One package publishes to test PyPI
[workspace.mono.packages."genkit-experimental"]
registry_url = "https://test.pypi.org"
major_on_zero = true
```

Resolution order: exact package name → group membership → workspace default.

Supported per-package keys: `versioning_scheme`, `calver_format`,
`prerelease_label`, `changelog`, `changelog_template`, `smoke_test`,
`major_on_zero`, `extra_files`, `dist_tag`, `registry_url`, `provenance`,
`skip_checks`.

### Exclusion Hierarchy

The three exclude levels control how much of the pipeline a package participates in:

| Level | Discovered | Checked | Version-bumped | Published |
|-------|:--:|:--:|:--:|:--:|
| *(normal)* | ✅ | ✅ | ✅ | ✅ |
| `exclude_publish` | ✅ | ✅ | ✅ | ❌ |
| `exclude_bump` | ✅ | ✅ | ❌ | ❌ |
| `exclude` | ❌ | ❌ | ❌ | ❌ |

### Group References

All exclude lists support `group:<name>` references that expand to the
patterns defined in `[groups]`. Groups can reference other groups
recursively — cycles are detected and reported as errors.

```toml
[groups]
core = ["genkit"]
google_plugins = ["genkit-plugin-firebase", "genkit-plugin-google-*"]
community_plugins = ["genkit-plugin-anthropic", "genkit-plugin-ollama"]
all_plugins = ["group:google_plugins", "group:community_plugins"]
samples = ["*-hello", "*-demo", "web-*"]

exclude_publish = [
  "group:samples",              # entire group
  "genkit-plugin-amazon-bedrock", # specific package
]
```

## Architecture

```
releasekit
├── Backends (DI / Protocol-based)
│   ├── VCS              git / hg operations (tag, commit, push)
│   │   ├── git.py         GitCLIBackend (default)
│   │   └── mercurial.py   MercurialCLIBackend
│   ├── PackageManager   build, publish, lock
│   │   ├── uv.py          UvBackend (default)
│   │   └── pnpm.py        PnpmBackend
│   ├── Workspace        package discovery
│   │   ├── uv.py          UvWorkspace (Python, default)
│   │   ├── pnpm.py        PnpmWorkspace (JS)
│   │   ├── go.py          GoWorkspace (Go)
│   │   ├── dart.py        DartWorkspace (Dart)
│   │   ├── maven.py       MavenWorkspace (Java/Kotlin/Gradle)
│   │   ├── cargo.py       CargoWorkspace (Rust)
│   │   └── bazel.py       BazelWorkspace (Bazel)
│   ├── Registry         package registry queries
│   │   ├── pypi.py        PyPIBackend (default)
│   │   ├── npm.py         NpmRegistry
│   │   ├── crates_io.py   CratesIoBackend
│   │   ├── goproxy.py     GoProxyBackend
│   │   ├── maven_central.py MavenCentralBackend
│   │   └── pubdev.py      PubDevBackend
│   └── Forge            release / PR management
│       ├── github.py      GitHubCLIBackend (default)
│       ├── github_api.py  GitHubAPIBackend (REST, for CI)
│       ├── gitlab.py      GitLabCLIBackend
│       └── bitbucket.py   BitbucketAPIBackend
│
├── Core Pipeline
│   ├── workspace.py     discover packages from pyproject.toml
│   ├── graph.py         build & topo-sort dependency graph
│   ├── versioning.py    conventional commits parsing + semver bumps
│   ├── versions.py      version data structures (ReleaseManifest, PackageVersion)
│   ├── bump.py          rewrite version in pyproject.toml
│   ├── pin.py           ephemeral dep pinning with crash-safe restore
│   ├── changelog.py     changelog generation from commits
│   ├── preflight.py     pre-publish safety checks
│   ├── checks/          standalone workspace health checks (subpackage)
│   │   ├── __init__.py    re-exports public API
│   │   ├── _protocol.py   CheckBackend protocol
│   │   ├── _base.py       BaseCheckBackend (shared defaults)
│   │   ├── _constants.py  shared regex, classifiers, patterns
│   │   ├── _universal.py  universal checks + universal fixers
│   │   ├── _python.py     PythonCheckBackend (27 checks + run_fixes)
│   │   ├── _python_fixers.py  16 Python-specific fixer functions
│   │   ├── _dart.py       DartCheckBackend (pubspec, analysis_options)
│   │   ├── _dart_fixers.py    Dart-specific fixers
│   │   ├── _go.py         GoCheckBackend (go.mod, go.sum)
│   │   ├── _go_fixers.py      Go-specific fixers
│   │   ├── _java.py       JavaCheckBackend (pom.xml, build.gradle)
│   │   ├── _java_fixers.py    Java/Kotlin-specific fixers
│   │   ├── _js.py         JsCheckBackend (package.json, npm)
│   │   ├── _js_fixers.py      JS/TS-specific fixers
│   │   ├── _rust.py       RustCheckBackend (Cargo.toml, Cargo.lock)
│   │   ├── _rust_fixers.py    Rust-specific fixers
│   │   └── _runner.py     run_checks() orchestrator
│   ├── scheduler.py     dependency-triggered queue dispatcher
│   ├── publisher.py     async publish orchestration
│   ├── prepare.py       release preparation (bump + changelog + PR)
│   ├── release.py       release tagging (tag merge commit + create Release)
│   ├── plan.py          execution plan preview
│   ├── state.py         crash-safe publish state persistence
│   ├── lock.py          lockfile management
│   ├── net.py           async HTTP utilities
│   ├── tags.py          git tag utilities
│   ├── release_notes.py release notes generation
│   ├── commitback.py    commit-back version bumps
│   ├── detection.py     multi-ecosystem auto-detection
│   ├── groups.py        release group filtering
│   ├── sbom.py          CycloneDX + SPDX SBOM generation
│   ├── profiling.py     pipeline step timing + bottleneck analysis
│   ├── tracing.py       optional OpenTelemetry tracing (graceful no-op)
│   ├── doctor.py        release state consistency checker
│   ├── distro.py        distro packaging dep sync (Debian/Fedora/Homebrew)
│   ├── branch.py        default branch resolution
│   └── commit_parsing/  conventional commit parser (subpackage)
│
├── Formatters
│   ├── ascii_art.py     box-drawing terminal art
│   ├── csv_fmt.py       RFC 4180 CSV with UTF-8 BOM
│   ├── d2.py            D2 diagram DSL
│   ├── dot.py           Graphviz DOT
│   ├── json_fmt.py      structured JSON
│   ├── levels.py        simple text listing (default)
│   ├── mermaid.py       Mermaid flowchart
│   ├── table.py         Markdown table
│   └── registry.py      format dispatcher
│
├── UX
│   ├── errors.py        error catalog + Rust-style render_error/render_warning
│   ├── logging.py       structured logging setup
│   ├── config.py        TOML config loading + validation (workspace-aware)
│   ├── init.py          workspace config scaffolding
│   └── cli.py           argparse + rich-argparse + shell completion
│
├── AI (Genkit-powered)
│   ├── ai.py            Genkit init, model fallback, load_prompt_folder
│   ├── _wordfilter.py   Aho-Corasick trie-based blocked-word filter
│   ├── prompts.py       PROMPTS_DIR, inline fallback constants
│   ├── prompts/         Dotprompt .prompt files (source of truth)
│   │   ├── summarize.prompt   changelog → ReleaseSummary JSON
│   │   └── codename.prompt    theme → ReleaseCodename JSON (with safety rules)
│   ├── schemas_ai.py    ReleaseSummary, ReleaseStats, ReleaseCodename
│   ├── summarize.py     AI changelog summarization + content-hash caching
│   └── codename.py      AI codenames, SAFE_BUILTIN_THEMES, safety filter
│
├── Observer
│   └── observer.py      PublishStage, SchedulerState, PublishObserver
│
└── UI
    ├── RichProgressUI   live progress table (TTY) + sliding window
    ├── LogProgressUI    structured logs (CI)
    ├── NullProgressUI   no-op (tests)
    └── Controls         p=pause r=resume q=cancel a=all w=window f=filter l=log
```

### Scheduler Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                          Scheduler                                │
│                                                                   │
│  from_graph() ──▶ seed level-0 ──▶ Queue                          │
│                                      │                            │
│         ┌────────────────────────────┼──────────┐                 │
│         │          Semaphore(N)      │          │                 │
│         │                            ▼          │                 │
│     ┌────────┐ ┌────────┐ ... ┌────────┐       │                 │
│     │Worker 0│ │Worker 1│     │Worker N│       │                 │
│     └───┬────┘ └───┬────┘     └───┬────┘       │                 │
│         │          │              │             │                 │
│         └──────────┴──────┬───────┘             │                 │
│                           │                     │                 │
│                     publish_fn(name)             │                 │
│                           │                     │                 │
│                    ┌──────┴──────┐              │                 │
│                    │  mark_done  │              │                 │
│                    └──────┬──────┘              │                 │
│                           │                     │                 │
│              decrement dependents' counters      │                 │
│              enqueue newly-ready packages        │                 │
│                           │                     │                 │
│                    ┌──────┴──────┐              │                 │
│                    │    Queue    │◀─────────────┘                 │
│                    └─────────────┘                                │
└───────────────────────────────────────────────────────────────────┘
```

### Backend Protocols

All I/O goes through protocol-defined backends. This enables:
- **Testing** with in-memory fakes (no subprocess calls)
- **Future ecosystems** by implementing new backends (e.g. `CargoBackend`)
- **CI/local parity** — same code path, different backends

```python
# Protocols defined in:
#   releasekit.backends.vcs         VCS
#   releasekit.backends.pm          PackageManager
#   releasekit.backends.workspace   Workspace
#   releasekit.backends.registry    Registry
#   releasekit.backends.forge       Forge

# Concrete implementations:
#   VCS:            GitCLIBackend, MercurialCLIBackend
#   PackageManager: UvBackend, PnpmBackend
#   Workspace:      UvWorkspace, PnpmWorkspace, GoWorkspace, DartWorkspace,
#                   MavenWorkspace, CargoWorkspace, BazelWorkspace, ClojureWorkspace
#   Registry:       PyPIBackend, NpmRegistry, CratesIoBackend, GoProxyBackend,
#                   MavenCentralBackend, PubDevBackend
#   Forge:          GitHubCLIBackend, GitHubAPIBackend, GitLabCLIBackend, BitbucketAPIBackend
```

### Ecosystem Abstraction

Some operations are currently Python-specific but follow a pattern that
enables multi-ecosystem support:

| Module | Current State | Abstraction Path |
|--------|--------------|------------------|
| `bump.py` | Rewrites `pyproject.toml` | → `Workspace.rewrite_version()` |
| `pin.py` | Rewrites deps in `pyproject.toml` | → `Workspace.rewrite_dependency_version()` |
| `config.py` | Reads `releasekit.toml` | ✅ Already standalone (ecosystem-agnostic) |
| `checks/` | `PythonCheckBackend` | ✅ Already protocol-based (subpackage) |
| `preflight.py` | `pip-audit`, metadata | ✅ Gated by `ecosystem=` param |

## Testing

The test suite has **4,500+ tests** across 137 test files:

```bash
# Run all tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=releasekit --cov-report=term-missing

# Specific module
uv run pytest tests/rk_publisher_test.py -v
```

### Testing Strategy

- All backends are injected via **dependency injection** — tests use
  in-memory fakes that satisfy the protocol contracts.
- No subprocess calls, no network I/O, no file system side effects
  (except `tmp_path`).
- Standard library assertions (`if/else` + `raise AssertionError`)
  following the want/got pattern.
- Complex comparisons use `dataclasses.asdict` for readable diffs.

## Security & Compliance

### ELI5: What Does "Supply Chain Security" Mean?

```text
Imagine you're baking a cake and sharing the recipe:

  🧁 Your code       = the recipe
  📦 Your package    = the cake you bake from the recipe
  🏪 PyPI / npm      = the bakery shelf where people pick up cakes
  🔒 Signing         = a tamper-evident seal on the box
  📋 SBOM            = the ingredient list on the label
  📜 Provenance      = a certificate saying "this cake was baked
                        in THIS kitchen from THIS recipe at THIS time"
  🔍 Checksums       = weighing the cake to make sure nobody
                        swapped it on the shelf

Supply chain security = making sure the cake on the shelf
is EXACTLY the one you baked, with no tampering in between.
```

### Security Features

| Feature | What It Does | Module |
|---------|-------------|--------|
| **No credentials in code** | PyPI tokens from env (`UV_PUBLISH_TOKEN`) or OIDC trusted publishing | `publisher.py` |
| **Sigstore keyless signing** | Sign artifacts + verify bundles via ambient OIDC credentials | `signing.py` |
| **SLSA provenance (L0–L3)** | in-toto attestation v1 envelopes; auto-detects CI → L3 on hosted runners | `provenance.py` |
| **SLSA L3 build/upload isolation** | `--build-only` / `--upload-only` split build and upload into separate CI jobs | `publisher.py` |
| **Post-publish verification** | `verify-install` installs packages from registry + smoke-tests imports | `verify_install.py` |
| **Artifact validation** | Validate provenance, SBOM, attestations, SECURITY-INSIGHTS post-build | `backends/validation/` |
| **SBOM generation** | CycloneDX 1.5 + SPDX 2.3 from workspace metadata | `sbom.py` |
| **Checksum verification** | SHA-256 computed locally, verified against registry post-publish | `publisher.py` |
| **PEP 740 attestations** | PyPI Trusted Publisher attestations for Python packages | `attestations.py` |
| **OCI container signing** | cosign keyless signing + SBOM attestation for containers | `signing.py` |
| **OSPS Baseline compliance** | Evaluate L1–L3 controls across 6 ecosystems with `releasekit compliance` | `compliance.py` |
| **Ephemeral pinning** | Crash-safe backup/restore with `.bak` files | `pin.py` |
| **State file integrity** | Resume refuses if HEAD SHA differs | `state.py` |

### SLSA Build L3 Compliance

ReleaseKit achieves [SLSA Build Level 3](https://slsa.dev/spec/v1.0/levels#build-l3)
by splitting the publish pipeline into isolated CI jobs. This prevents a
compromised build step from tampering with the upload or forging provenance.

```
release --> build --[artifacts]--> provenance --[attested]--> upload --> verify
              |                       |                         |
              +-- digests (base64) ---+                        |
              +-- manifest, SBOMs, attestations                |
                                                        verify <-+
```

| Requirement | Mechanism | Job(s) |
|-------------|-----------|--------|
| Hardened build platform | GitHub-hosted `ubuntu-latest` | build |
| Build/upload isolation | `--build-only` + `--upload-only` | build, upload |
| Non-falsifiable provenance | `slsa-github-generator` (L3) | provenance |
| Hermetic build | `--build-only` (no registry I/O) | build |
| Pinned dependencies | All actions pinned to commit SHA | all |
| Ephemeral environment | Fresh VM per job run | all |
| OIDC identity | `id-token: write` (Sigstore) | build, upload |
| Provenance before upload | provenance runs between build and upload | provenance |
| Verification | `slsa-verifier` + `verify-install` | verify |

Four reusable composite actions encapsulate the pipeline:

| Action | Purpose |
|--------|---------|
| `compute-artifact-digests` | SHA-256 digests in base64 for `slsa-github-generator` |
| `attest-build-artifacts` | GitHub artifact attestation via `actions/attest-build-provenance` |
| `upload-release-artifacts` | Upload artifacts, manifest, SBOMs to GitHub Release |
| `verify-slsa-provenance` | Download provenance + run `slsa-verifier` |

See the [SLSA Provenance guide](docs/docs/guides/slsa-provenance.md) for
full details and the [workflow templates](github/workflows/) for
production-ready CI pipelines for all 7 ecosystems.

### OSPS Baseline Compliance

releasekit evaluates your repository against the [OpenSSF OSPS Baseline](https://best.openssf.org/Concise-Guide-for-Evaluating-Open-Source-Software)
framework. Run `releasekit compliance` to see your status.

#### ELI5: What Is OSPS Baseline?

```text
Think of OSPS Baseline like a safety checklist for open-source projects:

  Level 1 (L1) = "Do you have a seatbelt?"
    → LICENSE file, SECURITY.md, SBOM, manifest files

  Level 2 (L2) = "Do you have airbags too?"
    → Signed artifacts, provenance, lockfiles, vuln scanning

  Level 3 (L3) = "Is your car crash-tested by an independent lab?"
    → Isolated builds, signed provenance on hosted runners
```

#### Universal Controls (All Ecosystems)

| ID | Control | Level | Module | NIST SSDF |
|----|---------|:-----:|--------|-----------|
| `OSPS-SCA-01` | SBOM generation | L1 | `sbom.py` | PS.3.2 |
| `OSPS-GOV-01` | Security policy (SECURITY.md) | L1 | `scorecard.py` | PO.1.1 |
| `OSPS-LEG-01` | License declared | L1 | — | PO.1.3 |
| `OSPS-SCA-02` | Signed release artifacts | L2 | `signing.py` | PS.2.1 |
| `OSPS-SCA-03` | Provenance attestation | L2 | `provenance.py` | PS.3.1 |
| `OSPS-SCA-04` | Vulnerability scanning | L2 | `osv.py` | RV.1.1 |
| `OSPS-SCA-05` | Dependency pinning (lockfile) | L2 | `preflight.py` | PS.1.1 |
| `OSPS-SCA-06` | Automated dependency updates | L2 | `scorecard.py` | PS.1.1 |
| `OSPS-BLD-01` | Build isolation (SLSA Build L3) | L3 | `provenance.py` | PW.6.1 |
| `OSPS-BLD-02` | Signed provenance | L3 | `signing.py` | PS.2.1 |

#### Ecosystem-Specific Controls

releasekit auto-detects which ecosystems are present and evaluates
ecosystem-specific security requirements:

**Python**

| ID | Control | Level | What It Checks |
|----|---------|:-----:|----------------|
| `ECO-PY-01` | PEP 561 type markers | L1 | `py.typed` files for type-safe packages |
| `ECO-PY-02` | PEP 740 attestations | L2 | PyPI Trusted Publisher attestations |
| `ECO-PY-03` | requires-python declared | L1 | Prevents install on wrong Python version |

**Go**

| ID | Control | Level | What It Checks |
|----|---------|:-----:|----------------|
| `ECO-GO-01` | go.mod present | L1 | Module dependency management |
| `ECO-GO-02` | go.sum integrity | L2 | Cryptographic hash verification of deps |
| `ECO-GO-03` | govulncheck in CI | L2 | Go vulnerability database scanning |

**JavaScript / Node.js**

| ID | Control | Level | What It Checks |
|----|---------|:-----:|----------------|
| `ECO-JS-01` | package.json present | L1 | npm/pnpm manifest |
| `ECO-JS-02` | npm provenance | L2 | `npm publish --provenance` attestations |
| `ECO-JS-03` | .npmrc registry config | L1 | Prevents registry substitution attacks |

**Java (Maven / Gradle)**

| ID | Control | Level | What It Checks |
|----|---------|:-----:|----------------|
| `ECO-JV-01` | Build system manifest | L1 | pom.xml or build.gradle present |
| `ECO-JV-02` | Gradle dep verification | L2 | Checksum/signature verification of deps |
| `ECO-JV-03` | Maven Central signing | L2 | GPG-signed artifacts for Maven Central |

**Rust**

| ID | Control | Level | What It Checks |
|----|---------|:-----:|----------------|
| `ECO-RS-01` | Cargo.toml present | L1 | Rust package manifest |
| `ECO-RS-02` | Cargo.lock committed | L2 | Reproducible builds |
| `ECO-RS-03` | cargo-audit in CI | L2 | RustSec advisory database scanning |
| `ECO-RS-04` | cargo-deny policy | L2 | License allowlist + advisory bans |

**Dart / Flutter**

| ID | Control | Level | What It Checks |
|----|---------|:-----:|----------------|
| `ECO-DT-01` | pubspec.yaml present | L1 | Dart/Flutter package manifest |
| `ECO-DT-02` | pubspec.lock committed | L2 | Reproducible builds |
| `ECO-DT-03` | analysis_options.yaml | L1 | Static analysis for type safety |

### Per-Package Check Skipping

Individual packages can opt out of specific checks via `skip_checks`
in `releasekit.toml`. This is useful when a package legitimately
doesn't need a particular check (e.g., an internal tool that doesn't
need `requires-python`).

#### ELI5: Why Skip Checks?

```
Imagine your school has a dress code (checks). Most students follow it.
But the gym teacher (internal tool) doesn't need to wear a tie.
skip_checks = ["tie_check"] for the gym teacher only.
Everyone else still gets checked.
```

#### Configuration

```toml
# Skip checks for ALL packages in this workspace
[workspace.py]
skip_checks = ["stale_artifacts"]

# Skip checks for ONE specific package
[workspace.py.packages."my-internal-tool"]
skip_checks = ["requires_python", "publish_classifier_consistency"]
```

The effective skip set for each package is the **union** of workspace-level
and per-package skips. Check names match the check IDs listed in the
[Health Checks](#health-checks) section above.

#### How It Works

```
┌──────────────────────────────────────────────────────────┐
│                    Check Runner                            │
│                                                          │
│  For each check (e.g. "requires_python"):                │
│                                                          │
│    packages = [A, B, C, D]                               │
│                                                          │
│    skip_map = {                                          │
│      "C": {"requires_python", "stale_artifacts"},        │
│    }                                                     │
│                                                          │
│    filtered = [A, B, D]   ← C is excluded for this check │
│                                                          │
│    run check on [A, B, D] only                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Standalone Repository

releasekit is designed to live in its own repository. The core is fully
agnostic — all external interactions go through 6 injectable Protocol
interfaces:

| Protocol | Abstraction | Default Backend | Alternatives |
|----------|-------------|-----------------|-------------|
| 🔀 `VCS` | Version control (commit, tag, push) | `GitCLIBackend` | `MercurialCLIBackend` |
| 📦 `PackageManager` | Build, publish, lock | `UvBackend` | `PnpmBackend`, `CargoBackend`, `DartBackend`, `GoBackend`, `MavenBackend`, `BazelBackend`, `MaturinBackend` |
| 🔍 `Workspace` | Package discovery, version rewrite | `UvWorkspace` | `PnpmWorkspace`, `CargoWorkspace`, `DartWorkspace`, `GoWorkspace`, `MavenWorkspace`, `BazelWorkspace` |
| 🌐 `Registry` | Package registry queries | `PyPIBackend` | `NpmRegistry`, `CratesIoBackend`, `GoProxyBackend`, `MavenCentralBackend`, `PubDevBackend` |
| 🏭 `Forge` | Releases, PRs, labels | `GitHubCLIBackend` | `GitHubAPIBackend`, `GitLabCLIBackend`, `BitbucketAPIBackend` |
| 🔭 `Telemetry` | Tracing spans, metrics | `NullTelemetry` | `OTelTelemetry` (OpenTelemetry) |

No module in `releasekit` imports from any parent package. The tool
discovers its workspace root by locating `releasekit.toml` at runtime.
To move to a standalone repo:

```bash
# 1. Copy the releasekit directory
cp -r py/tools/releasekit /path/to/new/repo

# 2. It already has its own:
#    - pyproject.toml (with build system + entry point)
#    - tests/ (full test suite)
#    - docs/ (mkdocs site)
#    - LICENSE
#    - README.md

# 3. Add CI workflows and publish to PyPI
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
