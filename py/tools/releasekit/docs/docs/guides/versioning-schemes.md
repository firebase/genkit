---
title: Versioning Schemes
description: Understand semver, PEP 440, and CalVer — and when to use each.
---

# Versioning Schemes

ReleaseKit supports three versioning schemes. Each ecosystem gets a
sensible default, but you can override it per-workspace or per-package.

## ELI5: What Is a Versioning Scheme?

Think of a version number like a mailing address — it tells people
*where* your software is in its journey. Different communities use
different address formats:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Version Number Anatomy                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  semver:   1  .  2  .  3  -  rc.1                               │
│            │     │     │     └── pre-release label               │
│            │     │     └── PATCH (bug fixes)                     │
│            │     └── MINOR (new features, backwards compatible)  │
│            └── MAJOR (breaking changes)                          │
│                                                                 │
│  pep440:   1  .  2  .  3  rc  1                                 │
│            │     │     │   └── no dots or hyphens!               │
│            │     │     └── micro (same as PATCH)                 │
│            │     └── minor                                       │
│            └── major                                             │
│                                                                 │
│  calver:   2026  .  02  .  3                                    │
│            │       │      └── MICRO (release count this month)   │
│            │       └── month                                     │
│            └── year                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts

| Concept | ELI5 Explanation |
|---------|-----------------|
| **semver** | "I promise: MAJOR = I broke something, MINOR = I added something, PATCH = I fixed something." Used by npm, Cargo, Go, pub.dev, Maven. |
| **PEP 440** | Python's version format. Like semver but pre-releases use suffixes like `a1`, `b1`, `rc1` instead of `-alpha.1`. Required by PyPI. |
| **CalVer** | "The version IS the date." Good for projects that release on a schedule (e.g., Ubuntu `24.04`). |

## Default Schemes by Ecosystem

When you set `ecosystem = "python"` in your workspace config, ReleaseKit
automatically picks the right versioning scheme:

| Ecosystem | Default | Registry | Why This Default? |
|-----------|---------|----------|-------------------|
| `python` | **pep440** | PyPI | PyPI **rejects** non-PEP 440 versions |
| `js` | **semver** | npm | npm requires [semver](https://semver.org/) |
| `go` | **semver** | Go proxy | Go modules use [semver with `v` prefix](https://go.dev/ref/mod#versions) |
| `rust` | **semver** | crates.io | Cargo enforces [semver](https://doc.rust-lang.org/cargo/reference/semver.html) |
| `dart` | **semver** | pub.dev | Dart/Flutter use [semver](https://dart.dev/tools/pub/versioning) |
| `java` | **semver** | Maven Central | Maven recommends semver-style versioning |
| `kotlin` | **semver** | Maven Central | Same as Java |
| `clojure` | **semver** | Clojars | Leiningen uses semver |
| `bazel` | **semver** | BCR | Bazel Central Registry uses semver |

!!! tip "Rule of thumb"
    If your package goes to PyPI → `pep440`. Everything else → `semver`.
    You almost never need to think about this.

## How Pre-Releases Look

The biggest visible difference between schemes is how pre-release
versions are formatted:

```
┌──────────────┬─────────────────┬──────────────────┐
│ Label        │ semver          │ PEP 440          │
├──────────────┼─────────────────┼──────────────────┤
│ alpha        │ 1.2.3-alpha.1   │ 1.2.3a1          │
│ beta         │ 1.2.3-beta.1    │ 1.2.3b1          │
│ rc           │ 1.2.3-rc.1      │ 1.2.3rc1         │
│ dev          │ 1.2.3-dev.1     │ 1.2.3.dev1       │
│ post         │ (not standard)  │ 1.2.3.post1      │
└──────────────┴─────────────────┴──────────────────┘
```

## Overriding the Default

### Per-Workspace

```toml
[workspace.py]
ecosystem = "python"
versioning_scheme = "semver"  # override pep440 default
```

### Per-Package

For mixed-ecosystem workspaces where some packages need a different
scheme:

```toml
[workspace.mono]
ecosystem = "python"
root = "."
# All packages default to pep440 (from ecosystem)

[workspace.mono.packages."my-js-wrapper"]
versioning_scheme = "semver"  # this JS package uses semver

[workspace.mono.packages."my-calver-lib"]
versioning_scheme = "calver"
calver_format = "YYYY.MM.MICRO"
```

### Resolution Order

```
┌─────────────────────────────────────────────────────────┐
│              Config Resolution (most specific wins)      │
│                                                         │
│  1. [workspace.X.packages."pkg-name"]  ← exact match   │
│           │                                             │
│           ▼ (if not set)                                │
│  2. [workspace.X.packages.group-name]  ← group match   │
│           │                                             │
│           ▼ (if not set)                                │
│  3. [workspace.X] versioning_scheme    ← workspace      │
│           │                                             │
│           ▼ (if not set)                                │
│  4. DEFAULT_VERSIONING_SCHEMES[ecosystem] ← auto        │
│           │                                             │
│           ▼ (if no ecosystem)                           │
│  5. "semver"                           ← built-in       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## CalVer Formats

When using `versioning_scheme = "calver"`, the `calver_format` controls
the version layout:

| Format | Example | Use Case |
|--------|---------|----------|
| `YYYY.MM.MICRO` | `2026.02.3` | Monthly releases (default) |
| `YYYY.MM.DD` | `2026.02.15` | Daily releases |
| `YYYY.MICRO` | `2026.42` | Yearly releases with sequential count |

## Codelab: Setting Up a Mixed Workspace

**Scenario:** You have a monorepo with Python libraries (PyPI) and a
JavaScript SDK (npm) in the same workspace.

### Step 1: Configure the workspace

```toml
# releasekit.toml
forge = "github"
repo_owner = "myorg"
repo_name = "myproject"

[workspace.mono]
ecosystem = "python"
root = "."

[workspace.mono.groups]
py-libs = ["myproject-*"]
js-sdk  = ["myproject-js-sdk"]

# JS packages use semver instead of pep440
[workspace.mono.packages.js-sdk]
versioning_scheme = "semver"
dist_tag = "latest"
```

### Step 2: Verify with `plan`

```bash
releasekit plan
```

```
┌──────────────────────┬────────┬─────────┬──────────┬────────┐
│ Package              │ Bump   │ Current │ Next     │ Scheme │
├──────────────────────┼────────┼─────────┼──────────┼────────┤
│ myproject-core       │ minor  │ 1.2.0   │ 1.3.0   │ pep440 │
│ myproject-utils      │ patch  │ 1.2.0   │ 1.2.1   │ pep440 │
│ myproject-js-sdk     │ minor  │ 1.2.0   │ 1.3.0   │ semver │
└──────────────────────┴────────┴─────────┴──────────┴────────┘
```

### Step 3: Pre-release versions look different per scheme

```bash
releasekit plan --prerelease rc
```

```
┌──────────────────────┬──────────────┬──────────────────┐
│ Package              │ Scheme       │ Pre-release      │
├──────────────────────┼──────────────┼──────────────────┤
│ myproject-core       │ pep440       │ 1.3.0rc1         │
│ myproject-js-sdk     │ semver       │ 1.3.0-rc.1       │
└──────────────────────┴──────────────┴──────────────────┘
```

## Next Steps

- [Per-Package Configuration](per-package-config.md) — All per-package override fields
- [Configuration Reference](../reference/config-file.md) — Full `releasekit.toml` schema
- [FAQ](faq.md) — Common versioning questions
