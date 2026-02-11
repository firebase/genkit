# releasekit Implementation Roadmap

Release orchestration for uv workspaces -- publish Python packages in
topological order with ephemeral version pinning, level gating, and
crash-safe file restoration.

**Target location**: `py/tools/releasekit/` in `firebase/genkit`
**Published as**: `releasekit` on PyPI
**Invocation**: `uvx releasekit publish`

---

## Progress

| Phase | Status | Notes |
|-------|--------|-------|
| 0: Foundation + Backends | ✅ Complete | 1,812 lines src, 864 lines tests, 82 tests pass |
| 1: Discovery | ✅ Complete | 3 modules, 65 tests pass, named error codes |
| 2: Version + Pin | ✅ Complete | 4 modules, 64 tests (incl. 6 integration), 211 total tests pass |
| 3: Publish MVP | ⬜ Not started | Critical milestone |
| 4: Harden | ⬜ Not started | |
| 5: Post-Pipeline + CI | ⬜ Not started | |
| 6: UX Polish | ⬜ Not started | |
| 7: Quality + Ship | ⬜ Not started | |

---

## Why This Tool Exists

The genkit Python SDK is a uv workspace with 21+ packages that have
inter-dependencies. Publishing them to PyPI requires dependency-ordered
builds with ephemeral version pinning -- and no existing tool does this.

**Why not use an existing tool?**

| Tool | Why it doesn't work for us |
|------|---------------------------|
| **python-semantic-release** | Monorepo support has been the [#1 most requested feature](https://github.com/python-semantic-release/python-semantic-release/issues/168) since **Feb 2020** -- still unresolved. No workspace discovery, no dependency graph, no topological publish, no ephemeral pinning. |
| **changesets** | npm only. No topological ordering. [No --dry-run for publish](https://github.com/changesets/changesets/issues/614) (open since 2021). Suffers from [unexpected major version bumps](https://github.com/changesets/changesets/issues/1011) (62 upvotes) from transitive deps. |
| **lerna** | npm only. [Lock file not updated](https://github.com/lerna/lerna/issues/1171) after internal dep version bumps (40 upvotes, open since **Dec 2017**). [No --dry-run](https://github.com/lerna/lerna/issues/51) (open since **Feb 2016**). |
| **cargo-release** | Rust only. [Can't exclude unchanged crates](https://github.com/crate-ci/cargo-release/issues/298) by default (open since 2021). Not portable to Python. |
| **Bash scripts** | Current approach. No dependency ordering, no resume, no safety, untestable. |

These tools have had critical gaps open for years. Rather than wait,
releasekit solves these problems natively for Python/uv workspaces.

**Problems we avoid by design** (learned from their issue trackers):

- **Lock file staleness**: `uv lock --upgrade-package` after version bump,
  included in the version commit. (lerna #1171, open since 2017)
- **Prerelease changelog empty on full release**: rollup mode merges
  prerelease entries into the final release. (PSR #555, open since 2023)
- **Unchanged packages published needlessly**: skip packages with no commits
  since last tag. (cargo-release #298, open since 2021)
- **Concurrent release race conditions**: advisory lock + CI concurrency
  key guidance. (PSR #168 comments)
- **No dry run**: `--dry-run` and `plan` alias from day one.
  (lerna #51, open since 2016; changesets #614, open since 2021)
- **Protected branch conflicts**: `--publish-from=ci` creates a PR, never
  pushes directly. (lerna #1957, cargo-release #119)

---

## Major Design Issues Addressed

Issues found through cross-verification with `uv` docs, PSR, cargo-release,
changesets, and lerna issue trackers.

| ID | Sev. | Issue | Solution | Phase |
|----|------|-------|---------|-------|
| D-1 | Crit | **Version commit missing from pipeline.** Both PSR and cargo-release do: version bump -> commit -> tag -> publish. Without a commit step, git tags point to a commit with the *old* version. | Add commit step after version bump: `versioning.py` -> `uv lock --upgrade-package` -> `git commit` -> `git tag` -> publish. | 2 |
| D-2 | Crit | **`uv.lock` stale after version bump.** Same bug open on [lerna since 2017](https://github.com/lerna/lerna/issues/1171) (40 upvotes). PSR [documents the fix](https://python-semantic-release.readthedocs.io/en/stable/configuration/configuration-guides/uv_integration.html). | Run `uv lock --upgrade-package <pkg>` for each bumped package, `git add uv.lock` before version commit. | 2 |
| D-3 | Crit | **`uv build --no-sources` required.** [uv docs](https://docs.astral.sh/uv/guides/package/) recommend `--no-sources` for publishing to verify the package builds without workspace source overrides. | Use `uv build --no-sources` in `publisher.py`. | 3 |
| D-4 | High | **Prerelease changelog empty on full release.** [PSR #555](https://github.com/python-semantic-release/python-semantic-release/issues/555) (open since 2023). Promoting rc1 to stable produces empty changelog. | `changelog_prerelease_mode = "rollup"` (default): merge prerelease entries into full release. | 5 |
| D-5 | High | **Unchanged packages published needlessly.** [cargo-release #298](https://github.com/crate-ci/cargo-release/issues/298) (open since 2021). | Skip packages with no commits since last tag. `--force-unchanged` to override. | 2, 3 |
| D-6 | High | **Concurrent CI release race condition.** [PSR #168](https://github.com/python-semantic-release/python-semantic-release/issues/168) comments. | Advisory lock locally. `concurrency: release` in CI. Detect in-progress draft releases in preflight. | 3 |
| D-7 | High | **`uv publish` has native retry flags.** `--check-url` and `--skip-existing` handle partial upload retries. | Use `uv publish --check-url` instead of custom 409 handling. | 3 |
| D-8 | Med | **Attestation support.** `uv publish` auto-discovers `.publish.attestation` files. | Document support. Don't interfere with attestation files. Passthrough `--no-attestations`. | 4 |
| D-9 | Med | **`resolve_check` uses wrong tool.** Plan said `pip install --dry-run`. | Use `uv pip install --dry-run` for consistency. | 3 |
| D-10 | Med | **`gh` CLI not installed.** | Graceful degradation: skip GitHub Releases with warning. Core publish works without `gh`. | 3, 5 |
| D-11 | Med | **Transitive major bump propagation.** [changesets #1011](https://github.com/changesets/changesets/issues/1011) (62 upvotes). | Per-package bump from own commits only. No transitive propagation. | 2 |
| D-12 | Med | **`uv version` command overlap.** `uv version --bump` already handles PEP 440. | Evaluate delegating version writing to `uv version --frozen` during Phase 2. | 2 |

### Corrected Pipeline (incorporating D-1 through D-12)

All external tool calls go through the backend shim layer (see Phase 0).
`vcs.*` = VCS/GitBackend, `pm.*` = PackageManager/UvBackend,
`forge.*` = Forge/GitHubBackend, `registry.*` = Registry/PyPIBackend.

```
 0. preflight         vcs.is_clean(), pm.lock() --check, forge.is_available() (D-10),
                      forge.list_releases() concurrent detection (D-6),
                      vcs.is_shallow(), OSS file checks
 1. versioning        vcs.log() + vcs.diff_files() -> compute semver (skip unchanged D-5)
 2. lock update       pm.lock(upgrade_package=<pkg>) for each bumped package (D-2)
 3. commit            vcs.commit("chore(release): <umbrella_tag>") (D-1)
 4. tag               vcs.tag() per-package tags + umbrella tag
 5. for each topo level:
      pin ──► pm.build(no_sources=True) (D-3) ──► verify ──► checksum
          ──► pm.publish(check_url=...) (D-7) ──► pm.resolve_check() (D-9)
          ──► registry.poll_available() ──► registry.verify_checksum()
          ──► pm.smoke_test() ──► restore
 6. push              vcs.push() commit + tags
 7. GitHub Release    forge.create_release() (graceful skip, D-10)
 8. changelog         vcs.log() + prerelease rollup mode (D-4)
 9. commitback        vcs.commit() + vcs.push() + forge.create_pr() (optional)
```

---

## Module Dependency Graph

### ASCII (viewable in any editor / terminal / git diff)

```
Phase 0: Foundation  ✅ COMPLETE
┌─────────────────────────────────────────────────────────┐
│  scaffold (pyproject.toml, __init__.py, py.typed)       │
│  errors.py (diagnostic lib, RK-NAMED-KEY codes)             │
│  logging.py (structlog + Rich)                          │
│                                                         │
│  backends/ (Protocol-based shim layer):                 │
│    _run.py ──► logging.py (subprocess abstraction)      │
│    pm.py ──► _run.py (PackageManager + UvBackend)       │
│    vcs.py ──► _run.py (VCS + GitBackend)                │
│    forge.py ──► _run.py (Forge + GitHubBackend, async)  │
│    registry.py ──► net.py (Registry + PyPIBackend,async)│
│  net.py ──► logging.py (httpx connection pool, retry)   │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 1: Discovery         ▼
┌─────────────────────────────────────────────────────────┐
│  config.py ──► errors.py, logging.py                    │
│  workspace.py ──► config.py                             │
│  graph.py ──► logging.py                                │
│                                                         │
│  ✓ releasekit discover                                 │
│  ✓ releasekit graph                                    │
│  ✓ releasekit check-cycles                             │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 2: Version + Pin     ▼
┌─────────────────────────────────────────────────────────┐
│  versioning.py ──► config.py, workspace.py              │
│    + skip unchanged packages (D-5)                      │
│    + uv lock --upgrade-package (D-2)                    │
│    + git commit version bump (D-1)                      │
│  pin.py ──► logging.py                                  │
│  bump.py ──► logging.py                                 │
│  versions.py ──► logging.py                             │
│                                                         │
│  ✓ releasekit version (skips unchanged)                │
│  ✓ releasekit pin --apply                              │
│  ✓ Version commit includes uv.lock                      │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 3: Publish MVP ★     ▼    ← CRITICAL MILESTONE ✅ COMPLETE
┌─────────────────────────────────────────────────────────┐
│  lock.py ──► logging.py                                 │
│  state.py ──► logging.py                                │
│  plan.py ──► graph.py (ExecutionPlan + table/JSON/CSV)  │
│  preflight.py (basic) ──► lock, graph, config, backends │
│    + forge.is_available() check (D-10, graceful)        │
│    + concurrent release detection (D-6)                 │
│  publisher.py (basic) ──► pin, state, preflight,        │
│                           versions, bump, errors,       │
│                           backends (pm, vcs, forge, reg)│
│    + pm.build(no_sources=True) (D-3)                    │
│    + pm.publish(check_url=...) (D-7)                    │
│    + pm.resolve_check() (D-9)                           │
│  cli.py (basic) ──► publisher, plan                     │
│    + --force-unchanged (D-5)                            │
│                                                         │
│  ★ releasekit publish --publish-from=local             │
│  ★ Corrected: preflight → version → uv lock → commit   │
│    → tag → [pin → build → publish → poll → smoke →     │
│    restore] per level → push                            │
│  ✓ Dry run validated: 60 packages, 4 levels, 0 errors  │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 4: Harden            ▼    🔶 IN PROGRESS
┌─────────────────────────────────────────────────────────┐
│  ui.py ──► logging.py                                   │
│  checks.py ──► graph.py, preflight.py, workspace.py     │
│    + 10 standalone health checks (replaces check-cycles)│
│  preflight.py (full) ──► + pip-audit,                   │
│                            metadata validation          │
│  publisher.py (full) ──► + staging, manifest, Test PyPI,│
│                            resume-from-registry,        │
│                            attestation passthrough (D-8)│
│                                                         │
│  ✓ Rich progress table (PR #4558)                       │
│  ✓ releasekit check (PR #4563)                          │
│  ✓ --stage, --index=testpypi, --resume-from-registry    │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 4b: Streaming Core   ▼    ⬜ PLANNED
┌─────────────────────────────────────────────────────────┐
│  scheduler.py ──► graph.py, workspace.py                │
│    + asyncio.Queue-based dependency-triggered dispatch  │
│    + Per-package dep counters, not level-based lockstep  │
│  publisher.py refactor ──► scheduler.py                 │
│    + Workers consume from queue, not level iteration    │
│    + _publish_one unchanged, only dispatch loop changes │
│                                                         │
│  ★ Streaming-ready for CI pipelines + dynamic feeds     │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 5: Post-Pipeline     ▼
┌─────────────────────────────────────────────────────────┐
│  tags.py ──► config, versions, vcs, forge               │
│    (graceful forge.is_available() skip, D-10)           │
│  changelog.py ──► config, vcs (prerelease rollup, D-4) │
│  release_notes.py ──► changelog, vcs, forge             │
│  commitback.py ──► bump, vcs, forge                     │
│  .github/workflows/publish_python_v2.yml                │
│                                                         │
│  ✓ releasekit publish --publish-from=ci                │
│  ✓ Structured changelog + rich release notes            │
│  ✓ GitHub Releases + draft/promote                      │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 6: UX Polish         ▼
┌─────────────────────────────────────────────────────────┐
│  init.py ──► config, workspace                          │
│  formatters/ (6 formats) ──► graph                      │
│  cli.py (full) ──► + rollback, completion, --explain,   │
│                      --no-tag, --no-push, --version-only│
│                                                         │
│  ✓ releasekit init                                     │
│  ✓ releasekit graph --format dot|mermaid|ascii|d2|json │
│  ✓ releasekit rollback                                 │
│  ✓ releasekit completion bash|zsh|fish                 │
└──────────────────────────┬──────────────────────────────┘
                           │
Phase 7: Quality + Ship    ▼
┌─────────────────────────────────────────────────────────┐
│  tests (90%+ coverage, all 30 modules)                  │
│  type checking (ty, pyright, pyrefly -- zero errors)    │
│  README.md (21 sections, mermaid diagrams)              │
│  workspace config (releasekit init on genkit repo)     │
│                                                         │
│  ✓ Ship v0.1.0 to PyPI                                  │
└─────────────────────────────────────────────────────────┘
```

### Mermaid (renders on GitHub / docs)

```mermaid
flowchart TD
    subgraph phase0 ["Phase 0: Foundation + Backends"]
        scaffold["pyproject.toml + init + py.typed"]
        errorsmod[errors.py]
        loggingmod[logging.py]
        netmod["net.py -- httpx pool"]
        runmod["backends/_run.py"]
        pmmod["backends/pm.py -- UvBackend"]
        vcsmod["backends/vcs.py -- GitBackend"]
        forgemod["backends/forge.py -- GitHubBackend"]
        registrymod["backends/registry.py -- PyPIBackend"]
    end

    subgraph phase1 ["Phase 1: Discovery"]
        configmod[config.py]
        workspacemod[workspace.py]
        graphmod[graph.py]
    end

    subgraph phase2 ["Phase 2: Version + Pin"]
        versioningmod[versioning.py]
        pinmod[pin.py]
        bumpmod[bump.py]
        versionsmod[versions.py]
    end

    subgraph phase3 ["Phase 3: Publish MVP"]
        lockmod[lock.py]
        statemod[state.py]
        planmod["plan.py -- ExecutionPlan"]
        preflightBasic["preflight.py -- basic"]
        publisherBasic["publisher.py -- basic"]
        cliBasic["cli.py -- basic"]
    end

    subgraph phase4 ["Phase 4: Harden"]
        uimod[ui.py]
        preflightFull["preflight.py -- full"]
        publisherFull["publisher.py -- full"]
    end

    subgraph phase5 ["Phase 5: Post-Pipeline + CI"]
        tagsmod[tags.py]
        changelogmod[changelog.py]
        releaseNotesmod[release_notes.py]
        commitbackmod[commitback.py]
        workflowmod[CI workflow]
    end

    subgraph phase6 ["Phase 6: UX Polish"]
        initmod[init.py]
        formattersmod["formatters/ -- 6 formats"]
        cliFull["cli.py -- full"]
    end

    subgraph phase7 ["Phase 7: Quality + Ship"]
        testsmod["tests -- 90%+ coverage"]
        typecheckmod["ty + pyright + pyrefly"]
        readmemod[README.md]
    end

    %% Phase 0 internal edges
    runmod --> loggingmod
    pmmod --> runmod
    vcsmod --> runmod
    forgemod --> runmod
    registrymod --> netmod
    netmod --> loggingmod

    %% Phase 1 edges
    configmod --> loggingmod
    configmod --> errorsmod
    workspacemod --> configmod
    graphmod --> loggingmod

    %% Phase 2 edges
    versioningmod --> configmod
    versioningmod --> workspacemod
    versioningmod --> vcsmod
    versioningmod --> pmmod
    pinmod --> loggingmod
    bumpmod --> loggingmod
    versionsmod --> loggingmod

    %% Phase 3 edges
    lockmod --> loggingmod
    statemod --> loggingmod
    planmod --> graphmod
    preflightBasic --> lockmod
    preflightBasic --> graphmod
    preflightBasic --> configmod
    preflightBasic --> vcsmod
    preflightBasic --> pmmod
    preflightBasic --> forgemod
    preflightBasic --> registrymod
    publisherBasic --> pinmod
    publisherBasic --> statemod
    publisherBasic --> preflightBasic
    publisherBasic --> versionsmod
    publisherBasic --> bumpmod
    publisherBasic --> errorsmod
    publisherBasic --> pmmod
    publisherBasic --> vcsmod
    publisherBasic --> forgemod
    publisherBasic --> registrymod
    cliBasic --> publisherBasic
    cliBasic --> planmod

    %% Phase 4 edges
    uimod --> loggingmod
    preflightFull --> preflightBasic
    publisherFull --> publisherBasic

    %% Phase 5 edges
    tagsmod --> configmod
    tagsmod --> versionsmod
    tagsmod --> vcsmod
    tagsmod --> forgemod
    changelogmod --> configmod
    changelogmod --> vcsmod
    releaseNotesmod --> changelogmod
    releaseNotesmod --> vcsmod
    releaseNotesmod --> forgemod
    commitbackmod --> bumpmod
    commitbackmod --> vcsmod
    commitbackmod --> forgemod

    %% Phase 6 edges
    initmod --> configmod
    initmod --> workspacemod
    formattersmod --> graphmod
    cliFull --> cliBasic

    %% Phase ordering
    phase0 --> phase1
    phase1 --> phase2
    phase2 --> phase3
    phase3 --> phase4
    phase4 --> phase5
    phase5 --> phase6
    phase6 --> phase7
```

---

## Phase Details

### Phase 0: Foundation + Backends  ✅ Complete

| Module | Description | Est. Lines | Actual | Status |
|--------|-------------|-----------|--------|--------|
| `pyproject.toml` | Package scaffold with `[project.scripts]`, hatchling build, 8 deps | ~40 | 68 | ✅ |
| `__init__.py` | `__version__` only | ~3 | 32 | ✅ |
| `py.typed` | PEP 561 marker | 0 | 0 | ✅ |
| `README.md` | Quick-start usage and project description | ~30 | 34 | ✅ |
| `errors.py` | Structured error system with `RK-NAMED-KEY` codes, `StrEnum`, `ErrorInfo`, error catalog, `explain()`. | ~150 | 261 | ✅ |
| `logging.py` | `structlog` configuration. Rich console when TTY, JSON for machines. `--verbose` / `--quiet`. | ~60 | 128 | ✅ |
| `backends/_run.py` | Central `run_command()` subprocess abstraction. Dry-run, structured logging, timeout. | ~60 | 192 | ✅ |
| `backends/pm.py` | `PackageManager` Protocol + `UvBackend`. `build()`, `publish()`, `lock()`, `version_bump()`, `resolve_check()`, `smoke_test()`. | ~120 | 281 | ✅ |
| `backends/vcs.py` | `VCS` Protocol + `GitBackend`. `is_clean()`, `is_shallow()`, `log()`, `commit()`, `tag()`, `push()`, etc. | ~100 | 278 | ✅ |
| `backends/forge.py` | `Forge` Protocol + `GitHubBackend`. `is_available()`, `create_release()`, `list_releases()`, `create_pr()`, etc. Graceful degradation. | ~120 | 307 | ✅ |
| `backends/registry.py` | `Registry` Protocol + `PyPIBackend`. `check_published()`, `poll_available()`, `project_exists()`, `latest_version()`. Async HTTP. | ~80 | 192 | ✅ |
| `net.py` | HTTP utilities: connection pooling, retry with exponential backoff, structured logging. | ~60 | 173 | ✅ |
| **Tests** | 82 tests across 8 test files. Protocol conformance, dry-run, integration (git, PyPI). | — | 864 | ✅ |

**Totals**: 1,812 lines source (estimated ~750), 864 lines tests.

**Done when**: `import releasekit` works, errors render with Rich formatting,
structlog outputs to stderr. All 4 backend protocols defined with default
implementations. `run_command()` logs and supports dry-run.

**Milestone**: Project skeleton passes `uv build`. Backends are injectable and mockable.

### Phase 1: Discovery  ✅ Complete

| Module | Description | Est. Lines | Actual | Status |
|--------|-------------|-----------|--------|--------|
| `config.py` | Read `[tool.releasekit]` from root `pyproject.toml`. `ReleaseConfig` dataclass. Config validation with fuzzy suggestions for typos (`difflib.get_close_matches`). Value type checking. Group integrity validation. | ~120 | 225 | ✅ |
| `workspace.py` | Discover packages from `[tool.uv.workspace].members` globs. Parse each member's `pyproject.toml`. Classify internal vs external deps. Return `list[Package]`. | ~100 | 248 | ✅ |
| `graph.py` | `DependencyGraph` dataclass, `build_graph()`, `detect_cycles()` (DFS), `topo_sort()` (Kahn's returning levels), `reverse_deps()` (BFS), `forward_deps()` (transitive closure), `filter_graph()` (dependency-aware: auto-include deps, group/package/exclude filters). | ~200 | 310 | ✅ |
| **Tests** | 65 tests across 3 test files: config_test.py (16), workspace_test.py (15), graph_test.py (34). Named error codes (RK-NAMED-KEY format). | — | 435 | ✅ |

**Done when**: `releasekit discover` prints JSON package list,
`releasekit graph` prints topological levels,
`releasekit check-cycles` exits 0 on acyclic graph.

**Milestone**: Can discover and visualize the genkit workspace.

**Smoke test results** (against real genkit workspace):
- Discovered 60 packages, 4 topological levels.
- Caught a real bug: `genkit-plugin-flask` lists itself as a dependency.
- Level 0: `genkit`, Level 1: 19 plugins, Level 2: 34 samples/plugins, Level 3: 5 packages.

### Phase 2: Version + Pin  ✅ Complete

| Module | Description | Est. Lines | Actual | Status |
|--------|-------------|-----------|--------|--------|
| `versioning.py` | Parse Conventional Commits via `vcs.log(paths=[pkg.path])`, compute per-package semver bumps. Monorepo-aware scoping. Configurable `tag_format`. PEP 440 compliance. Skip unchanged packages (D-5). No transitive bump propagation (D-11). `--prerelease`, `--force-unchanged`. | ~220 | 361 | ✅ |
| `pin.py` | Ephemeral `tomlkit`-based pinning. Context manager with triple-layer crash safety (atexit + SIG_DFL/os.kill + `.bak` backup). `shutil.move` atomic restore. SHA-256 verification. `packaging.Requirement` for PEP 508 dep parsing. | ~120 | 279 | ✅ |
| `bump.py` | Version string rewriting in `pyproject.toml` (tomlkit, comment-preserving) and arbitrary files (`__init__.py`, constants). Regex-based with `BumpTarget(path, pattern)` config. | ~80 | 195 | ✅ |
| `versions.py` | JSON version manifest. `ReleaseManifest` + `PackageVersion` dataclasses. Fail-fast on missing required fields. `bumped`/`skipped` filter properties. | ~80 | 188 | ✅ |
| **Tests** | 64 tests across 4 test files: rk_versioning_test.py (33 incl. 6 integration with FakeVCS), rk_bump_test.py (12), rk_pin_test.py (9), rk_versions_test.py (10). | — | ~550 | ✅ |

**Totals**: 1,023 lines source (estimated ~500), ~550 lines tests.

**Done when**: `releasekit version` shows computed bumps (skipping unchanged),
`releasekit pin --apply` modifies and restores pyproject.toml correctly,
version commit includes updated `uv.lock`.

**Milestone**: Version computation, ephemeral pinning, and version commit work
end-to-end.

**Key review learnings (PR #4555)**:
- Per-package commit scoping via `vcs.log(paths=...)` (not global fetch + diff_files mapping)
- Signal handlers use `SIG_DFL + os.kill`, not `default_int_handler`
- `shutil.move` for atomic restore (not `copy2 + unlink`)
- `packaging.Requirement` for robust dep parsing (not chained `.split()`)
- Fail-fast `KeyError → ValueError` on required manifest fields
- Integration tests with `FakeVCS` catch scoping bugs unit tests miss

### Phase 3: Publish MVP (Critical Path) ✅ COMPLETE

This is the most important milestone. Everything before it is a prerequisite;
everything after it is enhancement.

| Module | Description | Est. Lines | Status |
|--------|-------------|-----------|--------|
| `lock.py` | Advisory lock file (`.releasekit.lock`). PID/hostname/timestamp. Stale detection. `atexit` cleanup. | ~60 | ✅ |
| `state.py` | `RunState` dataclass. Per-package status tracking. Atomic save via `tempfile` + `os.replace`. Resume support with git SHA validation. | ~100 | ✅ |
| `plan.py` | `ExecutionPlan` dataclass. Per-package rows: order, level, name, current version, next version, status, reason. Output as Rich table (with emoji status), JSON, or CSV. Shared between `plan` and `publish` subcommands. Status values: `included`, `skipped`, `excluded`, `already_published`, `dependency_only`. | ~80 | ✅ |
| `preflight.py` (basic) | Receives `vcs: VCS`, `pm: PackageManager`, `forge: Forge`, `registry: Registry` via DI. Lock acquisition, `vcs.is_clean()`, `pm.lock()` check, cycle detection, `registry.latest_version()` validation, `vcs.is_shallow()` detection, `forge.is_available()` check (D-10), concurrent release detection via `forge.list_releases()` (D-6). | ~150 | ✅ |
| `publisher.py` (basic) | Receives all 4 backends via DI. Async level-by-level orchestration. Atomic step: `pin -> pm.build(no_sources=True) (D-3) -> verify -> checksum -> pm.publish(check_url=...) (D-7) -> pm.resolve_check() (D-9) -> registry.poll_available() -> pm.smoke_test() -> restore`. Semaphore concurrency, retry, fail-fast. | ~350 | ✅ |
| `cli.py` (basic) | Constructs backends, injects into modules. argparse with `publish`, `plan` (ExecutionPlan table/JSON/CSV output), `discover`, `graph`, `check`. `--dry-run`, `--force/-y`, `--force-unchanged`, `--publish-from=local`. TTY-aware confirmation. | ~220 | ✅ |

**Done when**: `releasekit publish --publish-from=local` executes the full
corrected pipeline via backend shims. `releasekit plan` outputs an
ExecutionPlan table with status/emoji/reason for each package, and `--format=json`
outputs machine-readable JSON.

**Milestone**: Can release the genkit Python SDK to PyPI with a single command.

**Dry run validated**: `releasekit publish --dry-run --force` successfully
processed all 60 packages across 4 topological levels (pin → build →
publish → poll → verify) with zero failures.

### Phase 4: Harden

| Module | Description | Est. Lines | Status |
|--------|-------------|-----------|--------|
| `ui.py` | **Rich Live progress table** with observer pattern. `RichProgressUI` (TTY), `LogProgressUI` (CI), `NullProgressUI` (tests). 9 pipeline stages with emoji/color/progress bars. ETA estimation. Error panel. Auto-detects TTY via `create_progress_ui()`. Integrated into `publisher.py` via `PublishObserver` callbacks. | ~560 | ✅ Done (PR #4558) |
| `checks.py` | **Standalone workspace health checks** (`releasekit check`) with `CheckBackend` protocol. 6 universal checks (cycles, self_deps, orphan_deps, missing_license, missing_readme, stale_artifacts) + 4 language-specific via `PythonCheckBackend` (type_markers, version_consistency, naming_convention, metadata_completeness). Extensible for future language backends. Found flask self-dep bug (#4562). | ~420 | ✅ Done (PR #4563) |
| `preflight.py` (full) | Added: `dist_clean` (stale dist/ detection, blocking), `trusted_publisher` (OIDC check, advisory). Remaining: `pip-audit` vulnerability scan (warn by default, `--strict-audit` to block, `--skip-audit` to skip), metadata validation (wheel METADATA fields). | +80 | 🔶 Partial |
| `registry.py` (full) | Added: `verify_checksum()` — downloads SHA-256 from PyPI JSON API (`urls[].digests.sha256`) and compares against locally-computed checksums. `ChecksumResult` dataclass with matched/mismatched/missing. | +100 | ✅ Done |
| `publisher.py` (full) | Added: post-publish SHA-256 checksum verification (step 6), `verify_checksums` config flag. Remaining: `--stage` two-phase, `--index=testpypi`, manifest mode, `--resume-from-registry`, rate limiting, attestation passthrough (D-8). | +30 | 🔶 Partial |

**`ui.py` — Rich Live Progress Table (Detailed Spec)**:

Visual mockup (TTY mode):

```
 ╭──────────────────────────────────────────────────────────────────────────╮
 │ releasekit publish ─ 12 packages across 4 levels (concurrency: 5)       │
 ╰──────────────────────────────────────────────────────────────────────────╯

 Level  Package                       Stage           Progress     Duration
 ─────  ────────────────────────────  ──────────────  ───────────  ────────
 0      genkit                        ✅ published    ██████████    12.3s
 0      genkit-plugin-checks          ✅ published    ██████████     8.7s
 0      genkit-plugin-ollama          📤 publishing   ██████░░░░     6.1s
 0      genkit-plugin-compat-oai      🔨 building     ████░░░░░░     4.2s
 0      genkit-plugin-pinecone        🔧 pinning      ██░░░░░░░░     1.8s
 1      genkit-plugin-google-genai    ⏳ waiting       ░░░░░░░░░░       —
 1      genkit-plugin-vertex-ai       ⏳ waiting       ░░░░░░░░░░       —
 2      genkit-plugin-firebase        ⏳ waiting       ░░░░░░░░░░       —
 3      web-endpoints-hello           ⏭️  skipped       ──────────       —

 ── Summary ────────────────────────────────────────────────────────────────
 Published: 2/12  │  Building: 2  │  Publishing: 1  │  Waiting: 4  │  Skipped: 1
 Elapsed: 14.2s   │  ETA: ~45s
```

Stage indicators (pipeline order):

| Stage       | Icon | Description                          |
|-------------|------|--------------------------------------|
| waiting     | ⏳   | Blocked by previous level            |
| pinning     | 🔧   | Pinning internal deps to exact versions |
| building    | 🔨   | Running `uv build --no-sources`      |
| publishing  | 📤   | Running `uv publish`                 |
| polling     | 🔍   | Waiting for PyPI indexing            |
| verifying   | 🧪   | Running smoke test                   |
| published   | ✅   | Successfully published               |
| failed      | ❌   | Failed (error shown below table)     |
| skipped     | ⏭️    | No changes / excluded                |

Implementation notes:

- Uses `rich.live.Live` with a `rich.table.Table` that refreshes on every state transition
- Progress bars use block characters (`█` filled, `░` empty)
- Duration tracked via `time.monotonic()` per package
- ETA estimated from average per-package duration × remaining
- Non-TTY (CI) mode: falls back to one structured log line per state transition
- Observer protocol: `PublishObserver` with `on_stage`, `on_error`, `on_complete`, `on_level_start`
- Three implementations: `RichProgressUI` (TTY), `LogProgressUI` (CI), `NullProgressUI` (tests)
- Error details for failed packages shown below table in a `rich.panel.Panel`

**Done when**: Rich progress UI shows real-time status during publish. Staging
workflow completes both phases. Pre-flight catches common mistakes.
`releasekit check` validates workspace health standalone.

**Milestone**: Production-hardened publish with rich UI and safety checks.

### Phase 4b: Streaming Publisher Core

Refactor the publisher from level-based lockstep dispatch to a
dependency-triggered streaming queue. This is a foundational change
that makes the core efficient for future expansion (CI pipelines,
distributed builds, dynamic package feeds).

**Why**: The level-based approach has a fundamental inefficiency —
if one package in level N is slow, all level N+1 packages wait even
if their specific dependencies are already done. With 60 packages
across 4 levels, this can waste significant time.

**Architecture**:

```
Current (level-based lockstep):

  Level 0: [A, B, C]  ─── all must finish ───▶  Level 1: [D, E, F]
                                                  ↑
                                        D waits for C even though
                                        D only depends on A

Proposed (dependency-triggered queue):

  A completes ──▶ D starts immediately (A is D's only dep)
  B completes ──▶ E starts immediately (B is E's only dep)
  C completes ──▶ F starts immediately (A + C are F's deps)
```

| Component | Description | Est. Lines |
|-----------|-------------|-----------|
| `scheduler.py` | **Dependency-aware task scheduler**. Maintains per-package dependency counters. When a package publishes, decrements counters of its dependents. When a counter hits zero, the package is enqueued. Semaphore controls max concurrency. | ~150 |
| `publisher.py` refactor | Replace level iteration with `asyncio.Queue` consumption. `_publish_one` pulls from queue, publishes, then notifies scheduler to resolve dependents. | ~±100 |

**Key design**:

```python
@dataclass
class PackageNode:
    """A node in the dependency-aware scheduler."""
    name: str
    remaining_deps: int          # Starts at len(internal_deps)
    dependents: list[str]        # Packages that depend on this one

class Scheduler:
    """Dependency-triggered task scheduler.

    Enqueues packages as their dependencies complete, rather than
    waiting for an entire topological level to finish.
    """
    _queue: asyncio.Queue[PackageNode]
    _nodes: dict[str, PackageNode]
    _semaphore: asyncio.Semaphore

    def mark_done(self, name: str) -> None:
        """Mark a package as published and enqueue ready dependents."""
        for dep_name in self._nodes[name].dependents:
            node = self._nodes[dep_name]
            node.remaining_deps -= 1
            if node.remaining_deps == 0:
                self._queue.put_nowait(node)

    async def run(self, publish_fn) -> PublishResult:
        """Consume from queue until all packages are published."""
        # Seed: enqueue all packages with zero deps.
        for node in self._nodes.values():
            if node.remaining_deps == 0:
                self._queue.put_nowait(node)

        # Worker pool consumes from queue.
        async def worker():
            while True:
                node = await self._queue.get()
                async with self._semaphore:
                    await publish_fn(node.name)
                    self.mark_done(node.name)
                self._queue.task_done()

        workers = [asyncio.create_task(worker())
                   for _ in range(concurrency)]
        await self._queue.join()
        # Cancel workers, collect results...
```

**Benefits**:

- **Faster**: Packages start as soon as their deps complete, not when the level completes
- **Streaming-ready**: The `Queue` naturally accepts dynamically-fed packages
- **Composable**: Same scheduler works for CI pipelines, distributed builds, dynamic DAGs
- **Observer-compatible**: Each `mark_done` / dequeue can notify the existing `PublishObserver`
- **Resume-compatible**: `RunState` still tracks per-package status; resume re-seeds the queue

**Backward compatibility**: `publish_workspace` signature stays the same.
The `levels` parameter can be dropped (computed internally from graph).
`_publish_one` stays unchanged — only the dispatch loop changes.

**Done when**: `releasekit publish --dry-run` produces identical results but
packages start as soon as deps complete (visible in timestamp ordering).

**Milestone**: Core scheduler is streaming-ready for future expansion.

### Phase 5: Post-Pipeline + CI

| Module | Description | Est. Lines |
|--------|-------------|-----------|
| `tags.py` | Git tag creation via `vcs.tag()` + `vcs.push()`. GitHub Release via `forge.create_release()` / `forge.promote_release()` (graceful skip via `forge.is_available()`, D-10). Configurable `tag_format` / `umbrella_tag_format`. Dual-mode: CI (draft + manifest + workflow trigger) and local (tags after publish). Tag-exists handling. Rate limit awareness. | ~180 |
| `changelog.py` | Structured changelog grouped by Conventional Commits type (Breaking Changes, Features, Bug Fixes, etc.). Commit data via `vcs.log()`. Exclusion patterns. PR references preserved. Prerelease-to-release rollup mode (D-4). | ~100 |
| `release_notes.py` | Umbrella release notes. Data collection via `vcs.log()`, `forge.pr_data()`, `vcs.diff_files()`, `vcs.tag_exists()`. Jinja2 template rendering (default + custom). AI drafting stub (off by default, future). | ~220 |
| `commitback.py` | Post-release PR to bump to next dev version. Branch creation via `vcs.commit()` + `vcs.push()`, PR creation via `forge.create_pr()`. Uses `bump.py` + `tomlkit`. | ~150 |
| CI workflow | `.github/workflows/publish_python_v2.yml`: download manifest from draft release, `uvx releasekit publish --publish-from=local --manifest=...`, promote release. | ~50 |

**Done when**: `releasekit publish --publish-from=ci` creates tags + draft
release + manifest, triggers CI workflow, CI publishes and promotes release.
Structured changelog and rich release notes appear in GitHub Release body.

**Milestone**: Full CI-driven release pipeline with GitHub Releases.

### Phase 6: UX Polish

| Module | Description | Est. Lines |
|--------|-------------|-----------|
| `init.py` | Workspace-aware config scaffolding. Auto-detect groups from directory structure. Generate/update `[tool.releasekit]` in root + per-package `pyproject.toml`. Update `.gitignore`. Show diff, prompt on TTY. Idempotent. | ~120 |
| `formatters/` | 6 graph output formats: `dot.py` (Graphviz), `json_fmt.py`, `levels.py`, `ascii_art.py`, `mermaid.py`, `d2.py`. All are pure functions: `graph -> str`. | ~300 |
| `cli.py` (full) | Add: `rollback` subcommand, `init` subcommand, `completion` subcommand, `--explain RK-NAMED-KEY`, granular flags (`--no-tag`, `--no-push`, `--no-release`, `--version-only`), `--rdeps`/`--deps` on graph, `rich-argparse` formatter, `argcomplete` shell completion. | +150 |

**Done when**: `releasekit init` scaffolds config for the genkit workspace.
All 6 graph formats produce correct output. Rollback automates tag/release
deletion. Shell completion works in bash/zsh/fish.

**Milestone**: Developer experience is polished and discoverable.

### Phase 7: Quality + Ship

| Item | Description | Est. Lines |
|------|-------------|-----------|
| Tests | 90%+ line coverage across all 30 modules. Mocked subprocess calls via `run_command()` abstraction. Snapshot tests for formatters. Integration tests with `--dry-run`. | ~2000 |
| Type checking | Zero errors from `ty`, `pyright`, and `pyrefly` in strict mode. | config |
| `README.md` | 21 sections with Mermaid workflow diagrams, CLI reference, config reference, testing workflow, vulnerability scanning, migration guide. | ~800 |
| Workspace config | Run `releasekit init` on the genkit repo. Review auto-detected groups. Commit generated config. | config |

**Done when**: `pytest --cov-fail-under=90` passes, all three type checkers
report zero errors, README is complete.

**Milestone**: Ship `releasekit` v0.1.0 to PyPI.

---

## Critical Path

The critical path runs through the modules that block the first usable release:

```
scaffold ──► errors.py ──► logging.py ──► config.py ──► workspace.py
    │                                         │
    │                                         ▼
    │                                     graph.py
    │                                         │
    ▼                                         ▼
versioning.py ──► uv lock ──► git commit ──► git tag
                                                │
                                                ▼
               pin.py ──► publisher.py ──► cli.py
                                │
                     ┌──────────┼──────────┐
                     ▼          ▼          ▼
                  net.py    state.py   preflight.py
```

**Phase 3 is the gate**: once `publisher.py` and `cli.py` (basic) are done,
the tool can publish packages with the corrected pipeline (D-1 through D-7).
Everything else (UI, changelog, release notes, init, formatters, rollback,
shell completion) is enhancement.

---

## Estimated Effort

| Phase | Modules | Est. Lines | Actual Lines | Status |
|-------|---------|-----------|-------------|--------|
| 0: Foundation + Backends | 8 (+scaffolding) | ~750 | 1,812 src + 864 tests | ✅ Complete |
| 1: Discovery | 3 (+tests) | ~420 | 783 src + 435 tests | ✅ Complete |
| 2: Version + Pin | 4 (+tests) | ~500 | 1,023 src + ~550 tests | ✅ Complete |
| 3: Publish MVP | 6 | ~960 | ~1,660 src | ✅ Complete |
| 4: Harden | 5 (extended) | ~450 | ~973 src (ui.py + checks.py + registry.py done) | 🔶 In progress |
| 4b: Streaming Publisher | 2 | ~250 | — | ⬜ Planned |
| 5: Post-Pipeline | 4 (+CI workflow) | ~700 | — | ⬜ Not started |
| 6: UX Polish | 3 (+ 6 formatters) | ~570 | — | ⬜ Not started |
| 7: Quality + Ship | tests + docs | ~2800 | — | ⬜ Not started |

Total: ~38 modules (including 6 formatters), ~4600 lines of production code,
~2800 lines of tests + docs.

---

## Dependencies (pyproject.toml)

```toml
[project]
name = "releasekit"
version = "0.1.0"
description = "Release orchestration for uv workspaces"
requires-python = ">=3.10"
license = "Apache-2.0"
dependencies = [
  "tomlkit>=0.13.0",       # Style-preserving TOML manipulation
  "structlog>=25.1.0",     # Structured logging
  "rich>=13.0.0",          # Rich terminal UI + progress
  "rich-argparse>=1.6.0",  # Colorful CLI help
  "argcomplete>=3.0.0",    # Shell tab completion
  "jinja2>=3.1.0",         # Release notes templates
  "diagnostic>=3.0.0",     # Rust-style error rendering
  "httpx>=0.27.0",         # Async HTTP with connection pooling (PyPIBackend)
]

[project.scripts]
releasekit = "releasekit.cli:main"
uvx-releasekit = "releasekit.cli:main"  # backward-compat shim

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

8 runtime dependencies, ~6MB total installed size.

---

## Scalability

releasekit is designed to scale from a handful of packages (genkit today) to
hundreds (releasekit v2 vision):

- **Async-first pipeline**: `publisher.py` uses `asyncio.Semaphore` for
  controlled parallelism within each topological level. `Forge` and `Registry`
  protocols are `async def` from day one, avoiding a sync-to-async migration
  later.

- **Connection pooling**: `net.py` provides a shared `httpx.AsyncClient` with
  configurable pool size (`[tool.releasekit] http_pool_size = 10`). Reused
  across all PyPI API calls within a run.

- **Batch operations**: `vcs.push()` pushes all tags in a single `git push`
  call. `forge.create_release()` can be batched with `asyncio.gather()` per
  level.

- **Graph efficiency**: Kahn's algorithm in `graph.py` is O(V+E), already
  efficient for hundreds of nodes. Level-based processing avoids redundant
  traversals.

- **UI at scale**: `ui.py` uses Rich Live with virtual scrolling. Only visible
  rows are rendered, capped at terminal height. Summary footer shows
  aggregated counts. Works for 500+ packages without lag.

- **Memory management**: Streaming git log parsing (no full history in memory).
  Wheel verification reads in chunks. State file is per-package append-only.

---

## Growth Path to releasekit v2

The Protocol-based backend shim layer makes releasekit v1 a foundation for v2:

| What stays (v1 -> v2) | What changes |
|------------------------|-------------|
| `PackageManager` protocol | Add `NpmBackend`, `CargoBackend`, `PnpmBackend` |
| `VCS` protocol + `GitBackend` | Unchanged (git is universal) |
| `Forge` protocol + `GitHubBackend` | Add `GitLabBackend`, `BitbucketBackend` |
| `Registry` protocol + `PyPIBackend` | Add `NpmRegistryBackend`, `CratesBackend` |
| Graph algorithms | Unchanged (language-agnostic) |
| Error system (RK-NAMED-KEY) | Expand code categories |
| Rich UI, structured logging | Unchanged |
| CLI structure | Add language auto-detection |

**Migration path**: No breaking changes. v2 adds new backends and a
`language` field to package config. Existing `[tool.releasekit]` configs
continue to work. The `uvx-releasekit` shim ensures old invocations keep
working.

---

## File Tree

```
py/tools/releasekit/
  pyproject.toml
  README.md
  roadmap.md                          ← this file
  src/
    releasekit/
      __init__.py
      py.typed
      errors.py                       ← diagnostic lib, RK-NAMED-KEY codes
      logging.py                      ← structlog + Rich
      backends/                       ← Protocol-based shim layer
        __init__.py                   ← re-exports all protocols + defaults
        _run.py                       ← run_command() subprocess abstraction
        pm.py                         ← PackageManager protocol + UvBackend
        vcs.py                        ← VCS protocol + GitBackend
        forge.py                      ← Forge protocol + GitHubBackend (async)
        registry.py                   ← Registry protocol + PyPIBackend (async)
      net.py                          ← httpx connection pool, retry, rate limit
      cli.py                          ← argparse + rich-argparse + argcomplete
      config.py                       ← [tool.releasekit] reader + validator
      workspace.py                    ← uv workspace discovery
      graph.py                        ← dep graph, topo sort, filter
      plan.py                         ← ExecutionPlan dataclass + table/JSON/CSV
      formatters/
        __init__.py
        dot.py                        ← Graphviz DOT
        json_fmt.py                   ← JSON adjacency list
        levels.py                     ← human-readable levels
        ascii_art.py                  ← box-drawing diagram
        mermaid.py                    ← Mermaid syntax
        d2.py                         ← D2 syntax
      init.py                         ← workspace config scaffolding
      versioning.py                   ← Conventional Commits -> semver
      pin.py                          ← ephemeral version pinning
      bump.py                         ← version string rewriting
      versions.py                     ← JSON manifest + ReleaseManifest
      lock.py                         ← advisory lock file
      state.py                        ← run state + resume
      preflight.py                    ← safety checks + pip-audit
      publisher.py                    ← level-by-level orchestration
      tags.py                         ← git tags + GitHub Releases
      changelog.py                    ← structured changelog
      release_notes.py                ← umbrella release notes (Jinja2)
      commitback.py                   ← post-release version bump PR
      ui.py                           ← Rich Live progress table
      templates/
        release_notes.md.j2           ← default release notes template
  tests/
    conftest.py
    errors_test.py
    logging_test.py
    backends/
      run_test.py
      pm_test.py
      vcs_test.py
      forge_test.py
      registry_test.py
    net_test.py
    plan_test.py
    cli_test.py
    config_test.py
    workspace_test.py
    graph_test.py
    formatters/
      dot_test.py
      json_fmt_test.py
      levels_test.py
      ascii_art_test.py
      mermaid_test.py
      d2_test.py
    init_test.py
    versioning_test.py
    pin_test.py
    bump_test.py
    versions_test.py
    lock_test.py
    state_test.py
    preflight_test.py
    publisher_test.py
    tags_test.py
    changelog_test.py
    release_notes_test.py
    commitback_test.py
    ui_test.py
```

---

## What This Replaces

The existing release process uses:

| Current tool | What it does | Problem |
|-------------|-------------|---------|
| `py/bin/publish_pypi.sh` | Single-package publish | No dependency ordering |
| `py/bin/build_dists` | Build all packages | No topological order |
| `py/bin/bump_version` | Bump all to same version | No per-package semver |
| `.github/workflows/publish_python.yml` | Matrix publish | No level gating |

`releasekit` replaces all four with: `uvx releasekit publish`
