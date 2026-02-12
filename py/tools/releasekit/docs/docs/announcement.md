# Announcing ReleaseKit

Release orchestration for the Genkit Python SDK — publish 60+ packages
to PyPI in the correct dependency order with one command.

## TL;DR

**ReleaseKit** automates the end-to-end process of publishing the Genkit
Python SDK's 62 interdependent packages to PyPI. It computes version bumps
from conventional commits, builds and publishes in topological dependency
order, verifies checksums against the registry, and resumes from failure.
A full release takes **one command** and completes in minutes.

---

## The Problem

The Genkit Python SDK is a [uv](https://docs.astral.sh/uv/) workspace
with **62 interdependent packages**: 1 core framework, 22 plugins, and
39 samples. These form a 4-level dependency graph with 121 edges.

Publishing requires:

1. **Correct ordering** — `genkit` (core) must be published *before* any
   plugin that depends on it, and plugins *before* samples that use them.
2. **Ephemeral version pinning** — workspace-sourced dependencies
   (`genkit = { workspace = true }`) must be temporarily rewritten to
   concrete versions (`genkit>=0.5.0`), then restored.
3. **Transitive bump propagation** — if `genkit` bumps from 0.5.0 → 0.6.0,
   every plugin and sample that depends on it must also be bumped.
4. **Crash safety** — if the process fails at package #37,
   resume from that point, not from scratch.

**No existing tool does this.** `uv publish` is a single-package command.
`release-please` doesn't understand Python workspaces. PyPI-specific tools
like `twine` and `flit` have no concept of dependency ordering.

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
Graphviz DOT, CSV, JSON, Markdown table, D2, and plain text):

<figure markdown="span">
  ![releasekit graph --format ascii](images/releasekit_graph_ascii.png){ width="600" }
  <figcaption><code>releasekit graph --format ascii</code> — 62 packages across 4 topological levels</figcaption>
</figure>

The topological sort guarantees that every package is published only after
all its dependencies are available on PyPI.

### Workspace Health Checks

19 automated health checks run on every PR via `bin/lint`, catching
issues before they reach PyPI:

<figure markdown="span">
  ![releasekit check](images/releasekit_check.png){ width="600" }
  <figcaption><code>releasekit check</code> — 19 workspace health checks</figcaption>
</figure>

Checks include: circular dependency detection, missing LICENSE/README
files, version consistency across all plugins, PEP 561 type markers,
lockfile staleness, naming conventions, and PyPI metadata completeness.

### Architecture Overview

The publish pipeline processes each package through 8 stages, with a
dependency-triggered scheduler that maximizes parallelism:

<figure markdown="span">
  ![releasekit architecture](images/releasekit_overview.png){ width="700" }
  <figcaption>Publish pipeline, scheduler architecture, and key metrics</figcaption>
</figure>

---

## Feature Matrix

| Feature | Description |
|---------|-------------|
| **Dependency-triggered publishing** | Packages publish as soon as their dependencies complete, maximizing parallelism |
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
