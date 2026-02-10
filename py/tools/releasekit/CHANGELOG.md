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

- **Phase 1: Workspace Discovery + Dependency Graph**
  - `config.py`: Reads `[tool.releasekit]` from `pyproject.toml` with typed
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

