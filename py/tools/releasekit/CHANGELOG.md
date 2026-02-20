# Changelog

## 0.2.0 (2026-02-17)

### Features

- **ci**: standardize releasekit-uv workflow to use composite action pattern (6686f0f, #4717) — @Yesudeep Mangalapilly
- **releasekit**: standardize template workflows and update docs (7367eb8, #4718) — @Yesudeep Mangalapilly
- **releasekit**: graph based licensing (03cc19b, #4705) — @Yesudeep Mangalapilly
- **releasekit**: genkit.ai (f2dde35, #4702) — @Yesudeep Mangalapilly
- **releasekit**: supply-chain security, multi-ecosystem orchestration, and CI hardening (29d3ec1, #4682) — @Yesudeep Mangalapilly
- **releasekit**: add default branch detection, and packaging (202431c, #4650) — @Yesudeep Mangalapilly
- **py/releasekit**: refactor checks into subpackage, add new checks/fixers (824e6bd, #4643) — @Yesudeep Mangalapilly
- **conform**: unified multi-runtime UX with native runner default (007c5a0, #4601) — @Yesudeep Mangalapilly
- **releasekit**: add 'l' keyboard shortcut to toggle log view (bdabeaa, #4587) — @Yesudeep Mangalapilly
- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **releasekit**: async refactoring and test suite updates (587643c, #4574) — @Yesudeep Mangalapilly
- **releasekit**: Phase 6 UX polish — formatters, init, completion, diagnostics (05540c7, #4572) — @Yesudeep Mangalapilly
- **releasekit**: add Phase 5 modules — tags, changelog, release notes, commitback (3367443, #4570) — @Yesudeep Mangalapilly
- **releasekit**: add dependency-triggered scheduler with interactive controls (dd88024, #4565) — @Yesudeep Mangalapilly
- **releasekit**: Phase 4 hardening — checksum verification + preflight checks (10939bd, #4564) — @Yesudeep Mangalapilly
- **releasekit**: replace check-cycles with comprehensive check command (359aef9, #4563) — @Yesudeep Mangalapilly
- **releasekit**: add Phase 4 Rich Live progress table (a4b591f, #4558) — @Yesudeep Mangalapilly
- **releasekit**: add Phase 3 Publish MVP modules (89e29bc, #4556) — @Yesudeep Mangalapilly
- **py/tools**: releasekit phase 2 — versioning, bump, pin, manifest (eb16643, #4555) — @Yesudeep Mangalapilly
- **py/tools**: releasekit phase 1 — workspace discovery + dependency graph (8843661, #4550) — @Yesudeep Mangalapilly
- **py/tools**: add releasekit — release orchestration for uv workspaces (03b2d9c, #4548) — @Yesudeep Mangalapilly

### Bug Fixes

- **releasekit**: skip git hooks in release commits and pushes (3fc9667, #4723) — @Yesudeep Mangalapilly
- **ci**: python genkit v0.5.0 tags (064a5d7, #4712) — @Yesudeep Mangalapilly
- **ci**: fix reelasekit-uv.yml force release pr creation (9df395a, #4710) — @Yesudeep Mangalapilly
- **conform,anthropic**: native executors, tool schema handling, and CLI consolidation (f9223b5, #4698) — @Yesudeep Mangalapilly
- **releasekit**: truncate PR body to fit GitHub's 65,536 char limit (defaeb1, #4696) — @Yesudeep Mangalapilly
- **ci**: fix invalid YAML and expression errors in releasekit-uv workflow (1fd1f6e, #4690) — @Yesudeep Mangalapilly
- **releasekit**: fix git push argument order, boost test coverage to 92%, fix lint errors (59d9dc3, #4667) — @Yesudeep Mangalapilly
- **py**: relocate tools of model-config test and sample-flow test (1043245, #4669) — @Elisa Shen
- **releasekit**: ensure command output is visible in CI on failure (a58c2f2, #4666) — @Yesudeep Mangalapilly
- **releasekit**: add set_upstream to VCS push and fail fast on errors (e983b22, #4662) — @Yesudeep Mangalapilly
- **releasekit**: replace literal null byte with git %x00 escape in changelog format (4866724, #4661) — @Yesudeep Mangalapilly
- **ci**: use working-directory, RELEASEKIT_DIR, and expose max_retries (b6f0102, #4659) — @Yesudeep Mangalapilly
- **ci**: use working-directory and RELEASEKIT_DIR for consistent paths (2cc1f38, #4655) — @Yesudeep Mangalapilly
- **ci**: python releasekit-uv workflow (0f5107a, #4651) — @Yesudeep Mangalapilly
- issues reported by releasekit (fba9ed1, #4646) — @Yesudeep Mangalapilly
- **py**: add missing LICENSE file and license metadata to samples (4ddd8a3, #4571) — @Yesudeep Mangalapilly

### Documentation

- **py**: audit and fix stale Python documentation (97f0451, #4658) — @Yesudeep Mangalapilly
- **py/releasekit**: analyze gaps (f95e492, #4647) — @Yesudeep Mangalapilly
- **py/releasekit**: update docs for checks subpackage refactor (5340380, #4644) — @Yesudeep Mangalapilly
- **releasekit**: add announcement with feature screenshots (f3ff86f, #4591) — @Yesudeep Mangalapilly
- **releasekit**: add MkDocs engineering documentation (4880e36, #4589) — @Yesudeep Mangalapilly
- **releasekit**: update README, roadmap, and CHANGELOG to match current state (6943f78, #4585) — @Yesudeep Mangalapilly
- **releasekit**: adopt release-please model (b700a54, #4575) — @Yesudeep Mangalapilly

All notable changes to releasekit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Phase 2: Version + Pin**
  - `versioning.py`: Conventional Commits parser with per-package semver bump
    computation, monorepo-aware scoping via `vcs.diff_files()`, configurable
    `tag_format`, prerelease support, and skip-unchanged logic.
  - `bump.py`: Version string rewriting in `pyproject.toml` (via tomlkit) and
    arbitrary files (via regex). Configurable `BumpTarget(path, pattern)`.
  - `pin.py`: Ephemeral dependency pinning context manager with triple-layer
    crash safety (atexit + signal + `.bak` backup) and SHA-256 restore
    verification.
  - `versions.py`: `ReleaseManifest` and `PackageVersion` dataclasses for
    JSON version manifest — CI handoff and audit trail.
  - 57 new tests (204 total across phases 0, 1, and 2).

- **Phase 4b: Streaming Publisher Core**
  - `scheduler.py`: Dependency-triggered task scheduler using `asyncio.Queue`
    with semaphore-controlled worker pool. Per-package dep counters trigger
    dependents on completion — no level-based lockstep.
  - Retry with exponential backoff + full jitter (configurable `max_retries`,
    `retry_base_delay`). Prevents thundering-herd retries.
  - Per-task timeout (`--task-timeout`, default `None` in scheduler, 600s via
    CLI). Prevents hung builds from blocking workers forever.
  - Suspend/resume via `pause()`/`resume()` methods (`asyncio.Event` gate).
  - Cancellation safety: `CancelledError` always calls `task_done()` via
    `try/finally` — `_queue.join()` never hangs.
  - Duplicate completion guard (idempotent `mark_done()`).
  - `already_published` parameter for resume-after-crash.
  - Refactored `publisher.py` to use `Scheduler.run()` instead of level loop.
  - CLI args: `--max-retries`, `--retry-base-delay`, `--task-timeout` threaded
    through `PublishConfig` → `Scheduler.from_graph()`.
  - 27 new tests covering all scheduler features.

- **Phase 4c: UI States & Interactivity**
  - `observer.py`: Extracted `PublishStage`, `SchedulerState`, `ViewMode`,
    `DisplayFilter` enums and `PublishObserver` protocol from `ui.py` — clean
    dependency graph between scheduler and UI modules.
  - `RETRYING` and `BLOCKED` per-package stage indicators with appropriate
    emojis and colors in both Rich and Log UIs.
  - `SchedulerState` enum (`RUNNING`, `PAUSED`, `CANCELLED`) with visual
    banner in Rich UI panel (yellow border when paused, red when cancelled).
  - Sliding window for large workspaces (>30 packages): shows active +
    recently completed + failed rows; collapses waiting/completed into
    summary count.
  - Keyboard shortcuts: `p`=pause, `r`=resume, `q`=cancel, `a`=show all,
    `w`=sliding window, `f`=cycle filter (all→active→failed). Async key
    listener with `select()`-based polling and terminal restore on exit.
  - `SIGUSR1`/`SIGUSR2` signal handlers for external pause/resume from
    another terminal (`kill -USR1 <pid>`).
  - `_block_dependents`: recursively marks all transitive dependents as
     `BLOCKED` when a package fails (with observer notifications).
  - ETA estimate and control hints in Rich UI footer.
  - 243 tests pass (all modules).

- **Dynamic Scheduler**
  - `scheduler.py`: `add_package()` — live node insertion into running scheduler.
    Wires up dependents, updates `_total`, enqueues immediately if all deps
    are already completed. Unknown deps silently ignored.
  - `scheduler.py`: `remove_package()` — marks node for cancellation via
    `_cancelled` set. Workers skip on dequeue. Optional `block_dependents`
    parameter for recursive transitive blocking.
  - 13 new tests (7 add + 6 remove).

- **Phase 5: Post-Pipeline**
  - `tags.py`: Git tag creation and GitHub Release management. Per-package
    tags via configurable `tag_format`, umbrella tag via `umbrella_tag_format`.
    Tag-exists detection (idempotent for resume). Graceful `forge.is_available()`
    skip. Dual-mode: local (published release) vs CI (draft release with
    manifest asset). `delete_tags()` for rollback.
  - 27 new tests for tags (format_tag, create, skip, error, forge, delete).

- **Phase 1: Workspace Discovery + Dependency Graph**
  - `config.py`: Reads `releasekit.toml` from the workspace root with typed
    validation, fuzzy "did you mean?" suggestions for typos, and a frozen
    `ReleaseConfig` dataclass with sensible defaults.
  - `workspace.py`: Discovers packages from `[tool.uv.workspace].members`
    globs, parses each `pyproject.toml`, classifies deps as internal or
    external, normalizes names per PEP 503.
  - `graph.py`: Builds a `DependencyGraph` with forward/reverse edges, detects
    cycles via DFS, computes topological sort with level grouping for parallel
    publishing, transitive deps via BFS, and `filter_graph` with automatic
    dependency inclusion.
  - Named error codes (`RK-CONFIG-NOT-FOUND`, etc.) for self-documenting errors.
  - 65 new tests (147 total across phases 0 and 1).

- **Phase 0: Foundation + Backends**
  - `errors.py`: Structured error handling with error codes, hints, and context.
  - `logging.py`: Structured logging via structlog.
  - `net.py`: HTTP client with connection pooling.
  - `backends/`: Pluggable backend interfaces for VCS, package manager, registry,
    forge, and subprocess execution.
  - 82 tests.

### Changed

- All test files renamed to `rk_*_test.py` to avoid basename collisions across
  the monorepo workspace.

