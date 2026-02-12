# Changelog

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

