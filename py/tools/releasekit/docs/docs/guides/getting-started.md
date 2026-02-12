---
title: Getting Started
description: Install ReleaseKit and publish your first release.
---

# Getting Started

This guide walks you through installing ReleaseKit, initializing
configuration, and publishing your first release.

## Prerequisites

- **Python 3.10+**
- **uv** (for Python workspaces) or **pnpm** (for JS workspaces)
- **Git** with Conventional Commits

## Installation

=== "uv tool (recommended)"

    ```bash
    uv tool install releasekit
    ```

=== "uvx (no install)"

    ```bash
    uvx releasekit --help
    ```

=== "pip"

    ```bash
    pip install releasekit
    ```

## Workflow Overview

```mermaid
graph LR
    subgraph "One-Time Setup"
        A["releasekit init"] --> B["Edit releasekit.toml"]
    end

    subgraph "Every Release"
        C["releasekit check"] --> D["releasekit plan"]
        D --> E["releasekit publish"]
    end

    B --> C

    style A fill:#1976d2,color:#fff
    style B fill:#1e88e5,color:#fff
    style C fill:#42a5f5,color:#fff
    style D fill:#42a5f5,color:#fff
    style E fill:#42a5f5,color:#fff
```

## Step 1: Initialize Configuration

From your workspace root (the directory containing `pyproject.toml` with
`[tool.uv.workspace]`):

```bash
releasekit init
```

This auto-detects your ecosystem and generates `releasekit.toml`:

```toml
tag_format      = "{name}-v{version}"
umbrella_tag    = "v{version}"
publish_from    = "local"

[groups]
core    = ["genkit"]
plugins = ["genkit-plugin-*"]
```

## Step 2: Discover Your Workspace

```bash
releasekit discover
```

Output:

```
┌──────────────────────────────┬─────────┬──────────────────────────────────┐
│ Package                      │ Version │ Path                             │
├──────────────────────────────┼─────────┼──────────────────────────────────┤
│ genkit                       │ 0.5.0   │ packages/genkit                  │
│ genkit-plugin-google-genai   │ 0.5.0   │ plugins/google-genai             │
│ genkit-plugin-ollama         │ 0.5.0   │ plugins/ollama                   │
│ sample-basic                 │ 0.1.0   │ samples/basic                    │
└──────────────────────────────┴─────────┴──────────────────────────────────┘
```

## Step 3: Visualize Dependencies

```bash
releasekit graph --format ascii
```

```
┌─────────────────────────────────────────────┐
│ Level 0                                     │
│ ┌─────────┐                                 │
│ │ genkit  │                                 │
│ └────┬────┘                                 │
├──────┼──────────────────────────────────────┤
│ Level 1                                     │
│ ┌────┴───────────────────┐ ┌──────────────┐ │
│ │ genkit-plugin-google   │ │ genkit-plg-  │ │
│ │ -genai                 │ │ ollama       │ │
│ └────────────┬───────────┘ └──────────────┘ │
├──────────────┼──────────────────────────────┤
│ Level 2                                     │
│ ┌────────────┴───────────┐                  │
│ │ sample-basic           │                  │
│ └────────────────────────┘                  │
└─────────────────────────────────────────────┘
```

## Step 4: Run Health Checks

```bash
releasekit check
```

This runs all workspace validation checks:

```
✓ dependency_cycles         No circular dependencies
✓ lockfile_staleness        uv.lock is up to date
✓ type_markers              All packages have py.typed
⚠ version_consistency       genkit-plugin-foo has version 0.4.0 (expected 0.5.0)
✓ naming_convention         All names match genkit-plugin-{dir} pattern
```

## Step 5: Preview the Plan

```bash
releasekit plan
```

```
┌──────────────────────────────┬──────────┬───────────┬───────────┐
│ Package                      │   Bump   │ Current   │  Next     │
├──────────────────────────────┼──────────┼───────────┼───────────┤
│ genkit                       │  minor   │ 0.5.0     │ 0.6.0     │
│ genkit-plugin-google-genai   │  patch   │ 0.5.0     │ 0.5.1     │
│ genkit-plugin-ollama         │  none    │ 0.5.0     │ (skip)    │
└──────────────────────────────┴──────────┴───────────┴───────────┘
```

## Step 6: Publish

```bash
# Dry run first
releasekit publish --dry-run

# Publish for real
releasekit publish
```

The publish pipeline for each package:

```
pin ──▶ build ──▶ publish ──▶ poll ──▶ verify ──▶ restore
 │        │         │           │        │          │
 │        │         │           │        │          └─ Restore original
 │        │         │           │        │             pyproject.toml
 │        │         │           │        └─ SHA-256 checksum
 │        │         │           │           verification
 │        │         │           └─ Poll registry until
 │        │         │              version appears
 │        │         └─ Upload to PyPI/npm
 │        └─ uv build / pnpm build
 └─ Pin internal deps to exact versions
```

## Step 7: Enable Shell Completions

=== "Bash"

    ```bash
    eval "$(releasekit completion bash)"
    ```

=== "Zsh"

    ```bash
    eval "$(releasekit completion zsh)"
    ```

=== "Fish"

    ```bash
    releasekit completion fish | source
    ```

## Next Steps

- [Configuration](configuration.md) — Customize `releasekit.toml`
- [CI/CD Integration](ci-cd.md) — Automate releases in CI
- [Error Codes](error-codes.md) — Troubleshoot common issues
