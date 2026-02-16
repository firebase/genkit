---
title: Release Channels
description: Map git branches to release channels for dist-tags and pre-release labels.
---

# Release Channels

Release channels map git branches to distribution tags (npm) or
pre-release labels (semver/PEP 440). This enables publishing from
multiple branches with predictable version labels.

---

## Configuration

Define branch-to-channel mappings in `releasekit.toml`:

```toml
[branches]
main           = "latest"       # Stable releases (default channel).
next           = "next"         # Next major preview.
beta           = "beta"         # Beta releases.
"release/v1.*" = "v1-maint"    # Maintenance releases (glob pattern).
```

---

## How Channels Work

| Branch | Channel | npm dist-tag | semver pre-release |
|--------|---------|-------------|-------------------|
| `main` | `latest` | *(default)* | *(none — stable)* |
| `next` | `next` | `next` | `1.0.0-next.1` |
| `beta` | `beta` | `beta` | `1.0.0-beta.1` |
| `release/v1.5` | `v1-maint` | `v1-maint` | *(patch only)* |

---

## Pattern Matching

Channel resolution uses this priority:

1. **Exact match** — branch name matches a key exactly.
2. **Glob pattern** — branch name matches via `fnmatch` (e.g.
   `release/v1.*` matches `release/v1.5`).
3. **Default** — falls back to `"latest"` if no match.

---

## Usage with npm

When publishing JavaScript packages, the resolved channel becomes the
npm dist-tag:

```bash
# From the "next" branch:
npm publish --tag next
# Users install with: npm install genkit@next
```

---

## Usage with Python

For Python packages, non-`latest` channels produce PEP 440 pre-release
versions:

```text
Channel "beta" + version 1.0.0  →  1.0.0b1
Channel "next" + version 1.0.0  →  1.0.0rc1
```
