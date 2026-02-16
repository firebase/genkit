---
title: Architecture Overview
description: High-level architecture of the ReleaseKit system.
---

# Architecture Overview

ReleaseKit follows a **layered architecture** with clean separation between
the CLI surface, orchestration logic, and pluggable backends.

## Layered Design

```mermaid
graph TB
    subgraph "User Interface"
        CLI["cli.py — argparse subcommands"]
        GHA["action.yml — GitHub Action"]
    end

    subgraph "Orchestration Layer"
        PREP["prepare.py"]
        PUB["publisher.py"]
        REL["release.py"]
        PLAN["plan.py"]
    end

    subgraph "Core Engine"
        GRAPH["graph.py — DAG"]
        SCHED["scheduler.py"]
        VER["versioning.py"]
        STATE["state.py"]
        CHECK["checks/ (subpackage)"]
        PRE["preflight.py"]
    end

    subgraph "Backend Protocols"
        VCS["VCS — Git, Mercurial"]
        PM["PackageManager — uv, pnpm"]
        FORGE["Forge — GitHub, GitLab, Bitbucket"]
        REG["Registry — PyPI, npm"]
        WS["Workspace — uv, pnpm"]
    end

    CLI --> PREP & PUB & REL & PLAN
    GHA --> CLI
    PREP --> GRAPH & VER & CHECK & PRE
    PUB --> SCHED & STATE
    REL --> VCS & FORGE
    SCHED --> PUB
    GRAPH --> WS
    VER --> VCS
    PRE --> VCS & PM & REG & FORGE
    PUB --> PM & REG & VCS

    style CLI fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style GHA fill:#90caf9,stroke:#1565c0,color:#0d47a1
```

## Design Principles

### 1. Backend Abstraction via Protocols

Every external system (git, PyPI, GitHub, uv) is accessed through a
Python `Protocol` class. This enables:

- **Testing** — Fake backends for deterministic unit tests
- **Extensibility** — New ecosystems without touching core logic
- **Forge agnosticism** — Same flow works on GitHub, GitLab, Bitbucket

### 2. Dependency Injection

All backends are instantiated in `cli.py` and passed as arguments to
orchestration functions. No module ever creates its own backend instance.

```python
# cli.py creates backends once
vcs = GitBackend(workspace_root)
pm = UvPackageManager(workspace_root)
forge = GitHubCLIBackend()
registry = PyPIBackend()

# Orchestration functions receive them
result = publish_workspace(
    vcs=vcs, pm=pm, forge=forge, registry=registry, ...
)
```

### 3. Crash Safety

The publish pipeline writes state to `.releasekit-state.json` after
every step. If the process crashes, `releasekit publish` detects the
state file and resumes from the last checkpoint.

### 4. Topological Ordering with Parallelism

Packages are published in dependency order (leaf packages first), but
packages at the same level can publish concurrently via the
[Scheduler](scheduler.md).

## Module Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Preflight
    participant Versioning
    participant Graph
    participant Scheduler
    participant Publisher
    participant State

    User->>CLI: releasekit publish
    CLI->>Preflight: run_preflight(vcs, pm, forge, registry)
    Preflight-->>CLI: PreflightResult (pass/fail)
    CLI->>Versioning: compute_bumps(packages, vcs)
    Versioning-->>CLI: list[PackageVersion]
    CLI->>Graph: build_graph(packages) → topo_sort()
    Graph-->>CLI: list[list[Package]] (levels)
    CLI->>Scheduler: Scheduler.from_graph(graph, publishable)
    CLI->>Publisher: publish_workspace(scheduler, ...)
    loop For each ready package
        Publisher->>State: set_status(BUILDING)
        Publisher->>State: set_status(PUBLISHING)
        Publisher->>State: set_status(VERIFYING)
        Publisher->>State: set_status(PUBLISHED)
        Publisher->>Scheduler: mark_done(name)
        Scheduler->>Publisher: enqueue dependents
    end
    Publisher-->>CLI: PublishResult
```
