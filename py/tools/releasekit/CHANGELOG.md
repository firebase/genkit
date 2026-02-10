# Changelog

All notable changes to releasekit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
