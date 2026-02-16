---
title: ReleaseKit
description: Release orchestration for monorepo workspaces.
---

# ReleaseKit

**Release orchestration for monorepo workspaces** — publish packages in
topological order with dependency-triggered scheduling, ephemeral version
pinning, retry with jitter, crash-safe file restoration, and post-publish
checksum verification.

---

## What is ReleaseKit?

ReleaseKit is a CLI tool and GitHub Action that automates the entire release
lifecycle for monorepo workspaces:

```mermaid
graph LR
    A[discover] --> B[plan]
    B --> C[prepare]
    C --> D[publish]
    D --> E[release]
    style A fill:#1976d2,color:#fff
    style B fill:#1976d2,color:#fff
    style C fill:#1976d2,color:#fff
    style D fill:#1976d2,color:#fff
    style E fill:#1976d2,color:#fff
```

| Stage | What it does |
|-------|-------------|
| **Discover** | Scans the workspace for packages and their dependencies |
| **Plan** | Computes version bumps from Conventional Commits |
| **Prepare** | Bumps versions, generates changelogs, opens a Release PR |
| **Publish** | Builds and uploads packages to registries in dependency order |
| **Release** | Tags the repo, creates GitHub Releases with notes |

## Key Features

<div class="grid cards" markdown>

-   :material-graph-outline:{ .lg .middle } **Dependency-Aware Scheduling**

    ---

    Packages publish as soon as their dependencies finish — no waiting
    for entire topological levels.

-   :material-package-variant-closed-check:{ .lg .middle } **Multi-Ecosystem**

    ---

    Supports Python (uv), JavaScript (pnpm), Go, Dart (Pub),
    Java (Maven/Gradle), Kotlin, Clojure, Rust (Cargo), and Bazel
    workspaces in a single monorepo.

-   :material-shield-check:{ .lg .middle } **Crash-Safe Publishing**

    ---

    Atomic state tracking with resume support. Interrupted releases
    pick up exactly where they left off.

-   :material-source-branch:{ .lg .middle } **Multi-Forge Support**

    ---

    Works with GitHub, GitLab, and Bitbucket with graceful
    degradation for forge-specific features.

-   :material-refresh:{ .lg .middle } **Retry with Jitter**

    ---

    Exponential backoff with full jitter for transient registry
    failures. Configurable max retries.

-   :material-check-decagram:{ .lg .middle } **Checksum Verification**

    ---

    Post-publish SHA-256 verification ensures uploaded artifacts
    match local builds.

-   :material-clock-outline:{ .lg .middle } **Cadence Releases**

    ---

    Scheduled daily, weekly, or per-commit releases with built-in
    cooldown, release windows, and minimum-bump thresholds.

-   :material-hook:{ .lg .middle } **Lifecycle Hooks**

    ---

    Run custom scripts at key points: before/after publish, after
    tag, before prepare. Template variables for version and name.

</div>

## Quick Start

```bash
# Install (or run directly with uvx)
uv tool install releasekit

# Initialize config
releasekit init

# Preview what would happen
releasekit plan

# Publish all changed packages
releasekit publish
```

## Architecture at a Glance

```
src/releasekit/
├── cli.py              # CLI entry point (argparse + subcommands)
├── config.py           # releasekit.toml parser & validator
├── detection.py        # Multi-ecosystem auto-detection
├── graph.py            # DAG construction & topological sort
├── scheduler.py        # Dependency-triggered async scheduler
├── versioning.py       # Conventional Commits → semver bumps
├── publisher.py        # Publish pipeline orchestration
├── preflight.py        # Pre-publish safety checks
├── prepare.py          # Version bump + changelog + Release PR
├── release.py          # Tag creation + GitHub Release
├── state.py            # Crash-safe status tracking
├── errors.py           # Structured error system (RK-* codes)
├── backends/           # Pluggable backend protocols
│   ├── forge/          #   GitHub, GitLab, Bitbucket
│   ├── pm/             #   uv, pnpm (package managers)
│   ├── registry/       #   PyPI, npm
│   ├── vcs/            #   Git, Mercurial
│   └── workspace/      #   uv workspace, pnpm workspace
└── formatters/         # Graph output (ASCII, Mermaid, DOT, ...)
```

For the full module breakdown, see [Module Map](architecture/module-map.md).
