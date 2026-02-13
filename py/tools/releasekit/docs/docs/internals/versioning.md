---
title: Versioning Engine
description: How ReleaseKit computes version bumps from Conventional Commits.
---

# Versioning Engine

The versioning engine reads git history, parses Conventional Commits,
scopes each commit to the package(s) it touches, and computes semver
bumps.

## Algorithm Overview

```mermaid
graph TD
    A["For each package"] --> B["Find last git tag"]
    B --> C["Get commits since tag"]
    C --> D["Filter by package path"]
    D --> E["Parse Conventional Commits"]
    E --> F["Compute max bump type"]
    F --> G["Apply bump to current version"]

    style A fill:#1976d2,color:#fff
    style G fill:#4caf50,color:#fff
```

## Conventional Commit Parsing

Each commit message is parsed against this regex:

```
^(?P<type>\w+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?\:\s*(?P<description>.+)$
```

### Bump Type Mapping

```
┌─────────────────────────────┬───────────┬─────────────────────────────┐
│ Commit Pattern              │ Bump Type │ Example                     │
├─────────────────────────────┼───────────┼─────────────────────────────┤
│ BREAKING CHANGE or "!"      │ major     │ feat!: redesign API         │
│ feat:                       │ minor     │ feat(auth): add OAuth       │
│ fix:, perf:                 │ patch     │ fix: null pointer           │
│ docs:, chore:, ci:, etc.    │ none      │ docs: update README         │
└─────────────────────────────┴───────────┴─────────────────────────────┘
```

### Bump Precedence

When multiple commits affect the same package, the **strongest** bump wins:

```
major > minor > patch > prerelease > none
```

```mermaid
graph LR
    C1["fix: typo → patch"]
    C2["feat: new API → minor"]
    C3["docs: update → none"]
    MAX["max_bump() → minor"]

    C1 --> MAX
    C2 --> MAX
    C3 --> MAX

    style MAX fill:#1976d2,color:#fff
```

## Path-Based Scoping

Commits are scoped to packages by their **file paths**, not commit
message scopes. This ensures accurate attribution even when commit
messages don't specify a scope:

```
Commit: fix: handle edge case
Files changed:
  plugins/google-genai/src/model.py   → genkit-plugin-google-genai
  plugins/google-genai/tests/test.py  → genkit-plugin-google-genai
  packages/genkit/src/core.py         → genkit
```

This commit produces a `patch` bump for both `genkit-plugin-google-genai`
and `genkit`.

## Transitive Propagation

When `synchronize = true`, bumps propagate transitively through the
dependency graph:

```mermaid
graph TD
    subgraph "Step 1: Direct bumps"
        A["genkit: feat → minor"]
        B["plugin-foo: fix → patch"]
        C["plugin-bar: none"]
    end

    subgraph "Step 2: Synchronize"
        A2["genkit: minor"]
        B2["plugin-foo: minor ⬆"]
        C2["plugin-bar: minor ⬆"]
    end

    A --> A2
    B --> B2
    C --> C2

    style B2 fill:#ff9800,color:#fff
    style C2 fill:#ff9800,color:#fff
```

With `synchronize = true`, the highest bump (minor) is applied to
**all** packages, ensuring version lockstep.

## Version Application

The `_apply_bump()` function applies semver rules:

```
┌───────────┬─────────┬────────────┬──────────────────────────────┐
│ Current   │ Bump    │ New        │ Notes                        │
├───────────┼─────────┼────────────┼──────────────────────────────┤
│ 1.2.3     │ major   │ 2.0.0      │ Reset minor + patch          │
│ 1.2.3     │ minor   │ 1.3.0      │ Reset patch                  │
│ 1.2.3     │ patch   │ 1.2.4      │                              │
│ 0.5.0     │ major   │ 0.6.0      │ 0.x default (major_on_zero=false) │
│ 0.5.0     │ major   │ 1.0.0      │ 0.x with major_on_zero=true  │
│ 1.2.3     │ pre     │ 1.2.4-rc.1 │ Prerelease on next patch     │
│ 1.2.3-rc.1│ pre     │ 1.2.3-rc.2 │ Increment prerelease counter │
└───────────┴─────────┴────────────┴──────────────────────────────┘
```

!!! note "0.x semver"
    By default (`major_on_zero = false`), packages with `0.x` versions
    treat `major` bumps as `minor` bumps — breaking changes during
    initial development don't jump to `1.0.0`. Set `major_on_zero = true`
    in `releasekit.toml` to allow `0.x → 1.0.0`.

## Data Types

### `ConventionalCommit`

```python
@dataclass
class ConventionalCommit:
    sha: str           # Full commit SHA
    type: str          # "feat", "fix", "docs", etc.
    description: str   # Commit description
    scope: str = ''    # Optional scope
    breaking: bool = False
    bump: BumpType = BumpType.NONE
    raw: str = ''      # Original message
```

### `BumpType`

```python
class BumpType(StrEnum):
    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'
    PRERELEASE = 'prerelease'
    NONE = 'none'
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant CLI
    participant VER as versioning.py
    participant VCS as VCS Backend
    participant GRAPH as DependencyGraph

    CLI->>VER: compute_bumps(packages, vcs, graph)

    loop For each package
        VER->>VCS: Find last tag for package
        VCS-->>VER: tag or None
        VER->>VCS: log(since=tag, paths=[pkg.path])
        VCS-->>VER: list[Commit]
        VER->>VER: parse_conventional_commit() for each
        VER->>VER: max_bump across all commits
        VER->>VER: _apply_bump(current_version, bump)
    end

    alt synchronize = true
        VER->>VER: Find max bump across ALL packages
        VER->>VER: Apply max bump to ALL packages
    end

    VER-->>CLI: list[PackageVersion]
```
