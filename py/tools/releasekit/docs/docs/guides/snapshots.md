---
title: Snapshots & Pre-Releases
description: Create snapshot builds, pre-releases, and promote to stable.
---

# Snapshots & Pre-Releases

ReleaseKit supports three kinds of non-stable versions:

| Type | Command | Example Version | Use Case |
|------|---------|----------------|----------|
| **Snapshot** | `releasekit snapshot` | `0.6.0.dev20260215+g1a2b3c4` | CI preview builds, PR previews |
| **Pre-release** | `releasekit publish --prerelease rc` | `0.6.0rc1` or `0.6.0-rc.1` | Release candidates, betas |
| **Promote** | `releasekit promote` | `0.6.0` (from `0.6.0rc1`) | Graduate RC to stable |

## ELI5: Snapshot vs Pre-Release

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Snapshot = "Here's what main looks like RIGHT NOW"             │
│  → Throwaway, not published to production registry              │
│  → Version includes git SHA or timestamp                        │
│  → Example: 0.6.0.dev20260215+g1a2b3c4                         │
│                                                                 │
│  Pre-release = "This is ALMOST ready for production"            │
│  → Published to the real registry                               │
│  → Users opt in with pip install genkit==0.6.0rc1               │
│  → Example: 0.6.0rc1 (PEP 440) or 0.6.0-rc.1 (semver)         │
│                                                                 │
│  Promote = "The RC is good, ship it as stable"                  │
│  → Strips the pre-release suffix                                │
│  → 0.6.0rc1 → 0.6.0                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Snapshots

### Basic usage

```bash
# Snapshot using git SHA (default)
releasekit snapshot
```

```
  Snapshot version: 0.6.0.dev20260215+g1a2b3c4

  📦 genkit: 0.5.0 → 0.6.0.dev20260215+g1a2b3c4
  📦 genkit-plugin-foo: 0.5.0 → 0.5.1.dev20260215+g1a2b3c4
```

### With PR number

```bash
releasekit snapshot --pr 1234
```

```
  Snapshot version: 0.6.0.dev1234+g1a2b3c4

  📦 genkit: 0.5.0 → 0.6.0.dev1234+g1a2b3c4
```

### With timestamp

```bash
releasekit snapshot --timestamp
```

```
  Snapshot version: 0.6.0.dev20260215143022

  📦 genkit: 0.5.0 → 0.6.0.dev20260215143022
```

### JSON output (for CI)

```bash
releasekit snapshot --format json
```

```json
[
  {
    "name": "genkit",
    "old_version": "0.5.0",
    "new_version": "0.6.0.dev20260215+g1a2b3c4",
    "bump": "minor",
    "skipped": false
  }
]
```

### CI: PR Preview Builds

```yaml
# .github/workflows/preview.yml
name: PR Preview

on:
  pull_request:

jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install
        run: uv sync --active
        working-directory: py

      - name: Compute snapshot versions
        run: |
          uv run releasekit snapshot \
            --pr ${{ github.event.pull_request.number }} \
            --format json > snapshot.json
        working-directory: py

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const snapshot = JSON.parse(fs.readFileSync('py/snapshot.json'));
            const lines = snapshot
              .filter(s => !s.skipped)
              .map(s => `| ${s.name} | ${s.old_version} | ${s.new_version} | ${s.bump} |`);
            const body = [
              '## 📦 Snapshot Preview',
              '| Package | Current | Snapshot | Bump |',
              '|---------|---------|----------|------|',
              ...lines
            ].join('\n');
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body
            });
```

## Pre-Releases

### Creating a release candidate

```bash
releasekit publish --prerelease rc
```

The pre-release label format depends on the versioning scheme:

| Scheme | Label | Result |
|--------|-------|--------|
| `pep440` | `rc` | `0.6.0rc1` |
| `pep440` | `alpha` | `0.6.0a1` |
| `pep440` | `beta` | `0.6.0b1` |
| `pep440` | `dev` | `0.6.0.dev1` |
| `semver` | `rc` | `0.6.0-rc.1` |
| `semver` | `alpha` | `0.6.0-alpha.1` |
| `semver` | `beta` | `0.6.0-beta.1` |

### Pre-release channels

Use branches to create pre-release channels:

```toml
# releasekit.toml
[workspace.py.branches]
main = "latest"
next = "next"
beta = "beta"
```

Pushes to the `beta` branch produce beta versions; pushes to `main`
produce stable versions.

## Promoting to Stable

When a pre-release is ready for production:

```bash
releasekit promote
```

```
  📦 genkit: 0.6.0rc1 → 0.6.0
  📦 genkit-plugin-foo: 0.5.1rc1 → 0.5.1

  2 package(s) promoted
```

Only packages with pre-release versions are affected. Stable packages
are skipped.

## Version Lifecycle

```mermaid
graph LR
    DEV["0.6.0.dev1<br/>(snapshot)"]
    ALPHA["0.6.0a1<br/>(alpha)"]
    BETA["0.6.0b1<br/>(beta)"]
    RC["0.6.0rc1<br/>(release candidate)"]
    STABLE["0.6.0<br/>(stable)"]

    DEV --> ALPHA --> BETA --> RC --> STABLE

    style DEV fill:#90caf9,color:#000
    style ALPHA fill:#64b5f6,color:#000
    style BETA fill:#42a5f5,color:#fff
    style RC fill:#1e88e5,color:#fff
    style STABLE fill:#4caf50,color:#fff
```

!!! note
    You don't have to go through every stage. Most projects go
    directly from development to RC to stable.

## Next Steps

- [Versioning Schemes](versioning-schemes.md) — How pre-release formats differ
- [Publish Pipeline](publish-pipeline.md) — Full publish flow
- [Workflow Templates](workflow-templates.md) — CI templates
