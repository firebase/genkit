---
title: Module Map
description: Complete breakdown of every module in the ReleaseKit codebase.
---

# Module Map

Every source file in `src/releasekit/` with its purpose, key types,
and dependencies.

## Core Modules

### `cli.py` — Command-Line Interface

| | |
|---|---|
| **Lines** | ~1,280 |
| **Purpose** | Argparse-based CLI with 17 subcommands |
| **Key functions** | `_cmd_publish`, `_cmd_plan`, `_cmd_discover`, `_cmd_graph`, `_cmd_check`, `_cmd_version`, `_cmd_explain`, `_cmd_init`, `_cmd_rollback`, `_cmd_completion` |
| **Entry point** | `_main()` → registered as `releasekit` console_script |

### `config.py` — Configuration

| | |
|---|---|
| **Lines** | ~490 |
| **Purpose** | Parse and validate `releasekit.toml` |
| **Key types** | `ReleaseConfig`, `WorkspaceConfig` (frozen dataclasses) |
| **Key functions** | `load_config()`, `resolve_group_refs()` |
| **Validation** | Typo detection (Levenshtein), type checking, enum validation |

### `graph.py` — Dependency Graph

| | |
|---|---|
| **Lines** | ~394 |
| **Purpose** | Build DAG from workspace packages, detect cycles, topological sort |
| **Key types** | `DependencyGraph` |
| **Key functions** | `build_graph()`, `detect_cycles()`, `topo_sort()`, `forward_deps()`, `reverse_deps()` |
| **Algorithm** | Kahn's algorithm for topological sort with level grouping |

### `versioning.py` — Version Computation

| | |
|---|---|
| **Lines** | ~434 |
| **Purpose** | Parse Conventional Commits and compute semver bumps |
| **Key types** | `BumpType` (enum), `ConventionalCommit` |
| **Key functions** | `compute_bumps()`, `parse_conventional_commit()` |
| **Bump rules** | `BREAKING` → major, `feat` → minor, `fix`/`perf` → patch |

### `scheduler.py` — Async Task Scheduler

| | |
|---|---|
| **Lines** | ~993 |
| **Purpose** | Dependency-triggered async dispatch with retry |
| **Key types** | `Scheduler`, `PackageNode`, `SchedulerResult` |
| **Features** | Worker pool, semaphore concurrency, exponential backoff + full jitter, cancellation |

### `publisher.py` — Publish Pipeline

| | |
|---|---|
| **Lines** | ~499 |
| **Purpose** | Orchestrate the per-package publish pipeline |
| **Key types** | `PublishConfig`, `PublishResult` |
| **Pipeline** | `pin → build → publish → poll → verify → restore` |

### `preflight.py` — Safety Checks

| | |
|---|---|
| **Lines** | ~533 |
| **Purpose** | Pre-publish validation (clean tree, lock, cycles, etc.) |
| **Key types** | `PreflightResult` |
| **Checks** | Lock acquisition, clean worktree, lock file staleness, shallow clone, cycles, forge availability, version conflicts, stale dist artifacts, trusted publisher, pip-audit |

### `prepare.py` — Release Preparation

| | |
|---|---|
| **Lines** | ~364 |
| **Purpose** | Bump versions, generate changelogs, open Release PR |
| **Key types** | `PrepareResult` |
| **Flow** | Preflight → compute bumps → bump pyproject.toml → generate changelogs → commit → push → create PR |

### `release.py` — Tagging & Releases

| | |
|---|---|
| **Lines** | ~326 |
| **Purpose** | Tag a merged Release PR and create GitHub Release |
| **Key types** | `ReleaseResult` |
| **Key functions** | `tag_release()`, `extract_manifest()` |

### `state.py` — Resume State

| | |
|---|---|
| **Lines** | ~328 |
| **Purpose** | Per-package status tracking with crash recovery |
| **Key types** | `PackageStatus` (enum), `PackageState`, `RunState` |
| **Persistence** | Atomic JSON writes via `tempfile` + `os.replace` |

### `errors.py` — Structured Errors

| | |
|---|---|
| **Lines** | ~345 |
| **Purpose** | Error codes, messages, hints in `RK-NAMED-KEY` format |
| **Key types** | `ErrorCode` (enum), `ErrorInfo`, `ReleaseKitError`, `ReleaseKitWarning` |
| **Rendering** | Rust-compiler-style colored output |

### `detection.py` — Ecosystem Detection

| | |
|---|---|
| **Lines** | ~246 |
| **Purpose** | Auto-detect ecosystems (Python, JS, Go, Rust, Dart, Java, Kotlin, Bazel, and more) in a monorepo |
| **Key types** | `Ecosystem` (enum), `DetectedEcosystem` |
| **Key functions** | `find_monorepo_root()`, `detect_ecosystems()` |

## Supporting Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `bump.py` | ~200 | Rewrite `version = "..."` in `pyproject.toml` |
| `changelog.py` | ~300 | Generate per-package changelogs from commits |
| `checks/` | ~2,900 | Workspace health checks subpackage: `_protocol.py` (CheckBackend), `_constants.py`, `_universal.py` (8 checks + 3 fixers), `_python.py` (PythonCheckBackend, 27 checks), `_python_fixers.py` (16 fixers), `_runner.py` (run_checks orchestrator) |
| `commitback.py` | ~230 | Commit and push changes back to the repo |
| `groups.py` | ~190 | Package group filtering from config |
| `init.py` | ~200 | Scaffold `releasekit.toml` with auto-detected groups |
| `lock.py` | ~220 | Advisory file-based locking for concurrent releases |
| `logging.py` | ~90 | Structured `structlog` logger factory |
| `net.py` | ~130 | HTTP client with connection pooling (`httpx`) |
| `observer.py` | ~120 | Publish event observer protocol for UI feedback |
| `pin.py` | ~260 | Ephemeral version pinning (rewrite deps to exact versions) |
| `plan.py` | ~280 | Build and display execution plans |
| `release_notes.py` | ~271 | Generate umbrella release notes from manifest |
| `tags.py` | ~487 | Create/delete per-package + umbrella git tags |
| `ui.py` | ~100 | Rich progress UI for publish operations |
| `versions.py` | ~160 | `PackageVersion` and `ReleaseManifest` types |
| `distro.py` | ~820 | Distro packaging dep sync (Debian, Fedora, Homebrew) |
| `workspace.py` | ~490 | `Package` type, `discover_packages()` (ecosystem-aware: Python/JS) |

## Backends

### `backends/forge/` — Code Forges

| Module | Forge | Transport |
|--------|-------|-----------|
| `github.py` | GitHub | `gh` CLI |
| `github_api.py` | GitHub | REST API (`httpx`) |
| `gitlab.py` | GitLab | `glab` CLI |
| `bitbucket.py` | Bitbucket | REST API (`httpx`) |
| `__init__.py` | — | `Forge` protocol definition |

### `backends/pm/` — Package Managers

| Module | Manager | Used for |
|--------|---------|----------|
| `uv.py` | uv | Build, publish, lock check |
| `pnpm.py` | pnpm | Build, publish, lock check |
| `cargo.py` | cargo | Build, publish, lock check |
| `dart.py` | dart pub | Build, publish, lock check |
| `go.py` | go | Build, publish (via git tags) |
| `maven.py` | mvn / gradle | Build, publish, deploy |
| `bazel.py` | bazel | Build, publish (polyglot) |
| `maturin.py` | maturin | Build, publish (Rust+Python) |
| `__init__.py` | — | `PackageManager` protocol |

### `backends/registry/` — Package Registries

| Module | Registry | Used for |
|--------|----------|----------|
| `pypi.py` | PyPI | Version check, checksum verify |
| `npm.py` | npm | Version check, checksum verify |
| `crates_io.py` | crates.io | Version check, yank |
| `goproxy.py` | Go module proxy | Version check |
| `maven_central.py` | Maven Central | Version check |
| `pubdev.py` | pub.dev | Version check |
| `__init__.py` | — | `Registry` protocol |

### `backends/vcs/` — Version Control

| Module | VCS | Used for |
|--------|-----|----------|
| `git.py` | Git | Tags, log, diff, status |
| `mercurial.py` | Mercurial | Tags, log, diff, status |
| `__init__.py` | — | `VCS` protocol |

### `backends/workspace/` — Workspace Discovery

| Module | Tool | Used for |
|--------|------|----------|
| `uv.py` | uv | Discover packages from `uv` workspace |
| `pnpm.py` | pnpm | Discover packages from `pnpm-workspace.yaml` |
| `cargo.py` | cargo | Discover crates from `Cargo.toml` workspace |
| `dart.py` | dart/melos | Discover packages from `pubspec.yaml` files |
| `go.py` | go | Discover modules from `go.work` / `go.mod` |
| `maven.py` | mvn/gradle | Discover modules from `pom.xml` / `settings.gradle.kts` |
| `bazel.py` | bazel | Discover targets from `MODULE.bazel` / `BUILD` files |
| `_edn.py` | — | EDN parser for Clojure `deps.edn` / `project.clj` |
| `__init__.py` | — | `Workspace` protocol |

### `formatters/` — Graph Output

| Module | Format | Use case |
|--------|--------|----------|
| `ascii_art.py` | Box-drawing | Terminal viewing |
| `csv_fmt.py` | RFC 4180 CSV | Spreadsheets, data pipelines |
| `d2.py` | D2 | Terrastruct diagrams |
| `dot.py` | DOT | Graphviz rendering |
| `json_fmt.py` | JSON | Programmatic consumption |
| `levels.py` | Level list | Quick level overview |
| `mermaid.py` | Mermaid | Markdown-embedded diagrams |
| `table.py` | Rich table | Formatted terminal output |
| `registry.py` | — | Formatter registry + dispatch |
