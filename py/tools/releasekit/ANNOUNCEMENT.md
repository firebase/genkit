# Announcing ReleaseKit: Automated Release Orchestration for the Genkit Python SDK

## TL;DR

**ReleaseKit** is a purpose-built release orchestration tool for the Genkit
Python SDK. It automates the end-to-end process of publishing 60+ Python
packages to PyPI in the correct dependency order — a process that was
previously manual, error-prone, and took hours. With ReleaseKit, a full
release takes **one command** and completes in minutes.

---

## The Problem

The Genkit Python SDK is a [uv](https://docs.astral.sh/uv/) workspace
with **62 interdependent packages**: 1 core framework, 22 plugins, and
39 samples. These packages form a 4-level dependency graph with 121
dependency edges.

Publishing them to PyPI requires:

1. **Correct ordering** — `genkit` (core) must be published *before* any
   plugin that depends on it, and plugins *before* samples that use them.
2. **Ephemeral version pinning** — during build, workspace-sourced
   dependencies (`genkit = { workspace = true }`) must be temporarily
   rewritten to concrete versions (`genkit>=0.5.0`), then restored.
3. **Transitive bump propagation** — if `genkit` bumps from 0.5.0 → 0.6.0,
   every plugin and sample that depends on it must also be bumped.
4. **Crash safety** — if the process fails mid-way through package #37,
   we need to resume from that point, not restart from scratch.

**No existing tool does this.** `uv publish` is a single-package command.
`release-please` doesn't understand Python workspaces. PyPI-specific tools
like `twine` and `flit` have no concept of dependency ordering.

Our previous release process was:
- Manual `uv publish` for each package, one at a time
- Copy-paste version numbers into pyproject.toml files
- Hope we didn't miss a dependency or publish in the wrong order
- If something failed mid-release, start over

---

## The Solution

ReleaseKit automates the entire release lifecycle:

```
releasekit prepare   →   Opens a Release PR with computed version bumps
                          and generated changelogs

releasekit publish   →   Builds and publishes all packages to PyPI
                          in topological dependency order

releasekit release   →   Tags the merge commit and creates a GitHub Release
```

---

## Features

### Dependency Graph Visualization

ReleaseKit discovers all 62 workspace packages and builds a dependency
graph, which can be visualized in 8 output formats (ASCII art, Mermaid,
Graphviz DOT, CSV, JSON, Markdown table, D2, and plain text levels):

![releasekit graph --format ascii](docs/docs/images/releasekit_graph_ascii.png)

The topological sort guarantees that every package is published only after
all its dependencies are available on PyPI.

### Workspace Health Checks

19 automated health checks run on every PR via `bin/lint`, catching
issues before they reach PyPI:

![releasekit check](docs/docs/images/releasekit_check.png)

Checks include: circular dependency detection, missing LICENSE/README
files, version consistency across all plugins, PEP 561 type markers,
lockfile staleness, naming conventions, and PyPI metadata completeness.

### Architecture Overview

The publish pipeline processes each package through 8 stages, with a
dependency-triggered scheduler that maximizes parallelism:

![releasekit architecture](docs/docs/images/releasekit_overview.png)

### Full Feature Matrix

| Feature | Description |
|---------|-------------|
| **Dependency-ordered publishing** | Topological sort ensures correct publish order across 4 levels |
| **Parallel within levels** | Packages at the same dependency level publish concurrently |
| **Conventional commits → semver** | Automatic version bump computation from git history |
| **Transitive propagation** | A change in `genkit` triggers patch bumps for all 61 dependents |
| **Crash-safe resume** | State persistence after each package; resume from failure point |
| **19 pre-publish health checks** | Catch issues at PR time, not after a broken release |
| **Ephemeral pinning** | Workspace deps temporarily pinned to concrete versions for build |
| **Post-publish verification** | SHA-256 checksums verified against PyPI |
| **Smoke testing** | `python -c 'import ...'` after publish to verify installability |
| **Changelog generation** | Per-package changelogs from conventional commits |
| **Git tagging** | Per-package tags (`genkit-v0.5.0`) + umbrella tag (`v0.5.0`) |
| **8 graph formats** | ASCII, CSV, DOT, D2, JSON, Mermaid, Markdown table, levels |
| **Rust-style diagnostics** | Every error has a unique code (e.g. `RK-GRAPH-CYCLE-DETECTED`) |
| **SIGUSR1/SIGUSR2 controls** | Pause/resume the scheduler from another terminal |
| **Release groups** | Publish a subset of packages (e.g. `--group core`) |
| **Rollback** | Delete a tag and its GitHub release with one command |

---

## Architecture

ReleaseKit is built on a **protocol-based backend architecture** that
makes it fully testable with in-memory fakes — no subprocess calls, no
network I/O, no file system side effects in tests:

```
releasekit
├── Backends (DI / Protocol-based)
│   ├── VCS              git operations (tag, commit, push)
│   ├── PackageManager   build, publish, lock (uv)
│   ├── Workspace        package discovery (uv)
│   ├── Registry         package registry queries (PyPI)
│   └── Forge            release / PR management (GitHub CLI + API)
│
├── Core Pipeline
│   ├── workspace.py     discover packages from pyproject.toml
│   ├── graph.py         build & topo-sort dependency graph
│   ├── versioning.py    conventional commits → semver bumps
│   ├── scheduler.py     dependency-triggered queue dispatcher
│   ├── publisher.py     async publish orchestration
│   ├── preflight.py     pre-publish safety checks
│   └── checks.py        standalone workspace health checks
│
├── Formatters           8 output formats (ASCII, CSV, DOT, Mermaid, ...)
├── UX                   Rust-style errors, structured logging, CLI
└── UI                   Rich live progress (TTY) / structured logs (CI)
```

### Publish Pipeline

Each package goes through an 8-stage pipeline:

```
pin → build → checksum → publish → poll → verify_checksum → smoke_test → restore
```

The **dependency-triggered scheduler** is more efficient than level-based
lockstep — each package starts as soon as all its dependencies complete,
not when the entire level finishes.

---

## Impact

| Metric | Before | After |
|--------|--------|-------|
| **Release time** | Hours (manual) | Minutes (automated) |
| **Risk of wrong ordering** | High | Zero (topological sort) |
| **Crash recovery** | Start over | Resume from failure point |
| **Version consistency** | Error-prone | Enforced by 19 checks |
| **Missing metadata** | Found after publish | Caught at PR time |
| **Changelog** | Manual | Auto-generated from commits |
| **PyPI verification** | Manual spot-check | Automated checksum + smoke test |

### CI Integration

ReleaseKit is integrated into CI at two levels:

1. **PR checks** (`bin/lint` → `releasekit check`) — runs 19 health
   checks on every PR touching `py/`. Catches issues before merge.
2. **Publish workflow** (`.github/workflows/publish_python.yml`) —
   orchestrates the full publish pipeline on release tags.

---

## Dependency Graph (62 packages, 121 edges, 4 levels)

```
┌────────────────────────────────────────────────────────┐
│ Level 0                                                │
│   genkit (0.5.0)                                       │
├────────────────────────────────────────────────────────┤
│ Level 1 (19 plugins + 1 sample)                        │
│   genkit-plugin-anthropic (0.5.0)                      │
│   genkit-plugin-google-genai (0.5.0)                   │
│   genkit-plugin-firebase (0.5.0)                       │
│   genkit-plugin-vertex-ai (0.5.0)                      │
│   genkit-plugin-ollama (0.5.0)                         │
│   ... 15 more                                          │
├────────────────────────────────────────────────────────┤
│ Level 2 (35 packages)                                  │
│   genkit-plugin-deepseek (0.5.0)                       │
│   genkit-plugin-flask (0.5.0)                          │
│   provider-google-genai-hello (0.1.0)                  │
│   web-endpoints-hello (0.1.0)                          │
│   ... 31 more                                          │
├────────────────────────────────────────────────────────┤
│ Level 3 (6 packages)                                   │
│   framework-restaurant-demo (0.1.0)                    │
│   provider-vertex-ai-model-garden (0.1.0)              │
│   ... 4 more                                           │
└────────────────────────────────────────────────────────┘
```

---

## Try It

```bash
# From the genkit repo root
cd py/tools/releasekit

# Discover all workspace packages
uv run releasekit discover

# View the dependency graph
uv run releasekit graph --format ascii

# Run workspace health checks
uv run releasekit check

# Preview what a release would look like
uv run releasekit plan
```

---

## Links

- **Source**: `py/tools/releasekit/` in the genkit repo
- **CI PR**: [#4590](https://github.com/firebase/genkit/pull/4590) — enables `releasekit check` in CI
- **Documentation PR**: [#4589](https://github.com/firebase/genkit/pull/4589) — MkDocs engineering docs
- **Publish Workflow**: `.github/workflows/publish_python.yml`
