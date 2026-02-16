---
title: Commit-Back PRs
description: Automatically bump to dev versions after a release.
---

# Commit-Back PRs

After a release, the workspace needs to be bumped to the next
**development version** (e.g. `0.5.0` → `0.5.1.dev0`) so that
in-progress work doesn't look like a published release. ReleaseKit
automates this with commit-back PRs.

---

## How It Works

```text
Release published (v0.5.0)
     │
     ▼
Create branch: chore/post-release-0.5.0
     │
     ▼
For each bumped package:
    bump pyproject.toml → 0.5.1.dev0
     │
     ▼
Commit → Push → Create PR
```

The commit-back PR:

- Creates a new branch from the release commit.
- Bumps all released packages to their next `.dev0` version.
- Opens a pull request via the Forge backend.

---

## Triggering Commit-Back

Commit-back runs automatically after `releasekit release` when
`auto_commitback = true` in the workspace config:

```bash
# Release creates tags + GitHub Release, then auto-creates
# a commit-back PR if auto_commitback is enabled.
releasekit release
```

To preview what the commit-back would do, use a dry run:

```bash
releasekit release --dry-run
```

---

## Configuration

```toml
[workspace.py]
# Enable automatic commit-back after publish (default: false).
auto_commitback = true

# Branch prefix for commit-back PRs.
commitback_branch_prefix = "chore/post-release"

# Base branch for the PR (default: "main").
commitback_base = "main"
```

---

## Dev Version Format

| Release Version | Dev Version |
|----------------|-------------|
| `0.5.0` | `0.5.1.dev0` |
| `1.2.3` | `1.2.4.dev0` |
| `0.5.0rc1` | `0.5.0.dev0` |

Pre-release suffixes are stripped before computing the dev version.
