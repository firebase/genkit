---
title: Release Groups
description: Publish subsets of workspace packages independently.
---

# Release Groups

Release groups let you partition your monorepo into independently
releasable subsets. This enables different release cadences for core
packages vs. plugins vs. samples.

---

## Configuration

Define groups as glob patterns in `releasekit.toml`:

```toml
[groups]
core = ["genkit", "genkit-plugin-*"]
samples = ["sample-*"]
tools = ["releasekit", "releasekit-*"]
```

A package is included in a group if its name matches **any** pattern.

---

## Usage

Pass `--group` to filter the release to a specific group:

```bash
# Release only the core packages.
releasekit publish --group core

# Preview the plan for samples only.
releasekit plan --group samples

# Run health checks for a specific group.
releasekit check --group core
```

---

## Listing Groups

Groups are defined in `releasekit.toml` and can be inspected directly.
Use `releasekit discover` to see which packages are discovered:

```bash
releasekit discover
# Discovered 23 packages in workspace 'py'
```

Then pass `--group` to filter commands to a specific group.

---

## Auto-Detection

`releasekit init` auto-detects groups from your workspace directory
structure. Packages under `packages/` go into a `"packages"` group,
plugins under `plugins/` go into a `"plugins"` group, etc. When a
directory contains many packages, a glob pattern (e.g. `genkit-plugin-*`)
is used instead of listing every name.

---

## Validation

ReleaseKit warns about patterns that match zero packages:

```bash
releasekit check --group core
# ⚠ Pattern 'genkit-plugin-*' in group 'core' matches 0 packages.
```

This helps catch typos in group definitions.
