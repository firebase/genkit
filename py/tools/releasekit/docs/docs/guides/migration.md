---
title: Migration Guide
description: Migrate to ReleaseKit from release-please, semantic-release, changesets, or lerna.
---

# Migration Guide

Already using another release tool? ReleaseKit can read your existing
configuration and generate `releasekit.toml` automatically.

## ELI5: What Does Migration Do?

```
┌─────────────────────────────────────────────────────────────────┐
│                    Migration Flow                                │
│                                                                 │
│  Your existing config          ReleaseKit config                │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │ .release-please-  │   →    │ releasekit.toml   │              │
│  │ manifest.json     │  migrate│                  │              │
│  │ release-please-   │   →    │ [workspace.py]   │              │
│  │ config.json       │        │ ecosystem = ...   │              │
│  └──────────────────┘         └──────────────────┘              │
│                                                                 │
│  Your git tags and history are preserved.                       │
│  ReleaseKit reads existing tags to compute the next version.    │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Sources

| Source | Config Files | What Gets Migrated |
|--------|-------------|-------------------|
| `release-please` | `.release-please-manifest.json`, `release-please-config.json` | Packages, versions, tag format, changelog sections |
| `semantic-release` | `.releaserc`, `.releaserc.json`, `release.config.js` | Branches, plugins config, tag format |
| `changesets` | `.changeset/config.json` | Packages, changelog, access settings |
| `lerna` | `lerna.json` | Packages, versioning mode, tag format |

## Quick Start

### Step 1: Preview the migration

```bash
releasekit migrate --from release-please --dry-run
```

This shows what `releasekit.toml` would look like without writing
any files.

### Step 2: Run the migration

```bash
releasekit migrate --from release-please
```

### Step 3: Verify

```bash
# Check the generated config
cat releasekit.toml

# Run doctor to validate
releasekit doctor

# Preview what the first release would look like
releasekit plan
```

## Migration from release-please

### Before

```json
// .release-please-manifest.json
{
  "packages/genkit": "0.5.0",
  "plugins/google-genai": "0.5.0"
}
```

```json
// release-please-config.json
{
  "packages": {
    "packages/genkit": {
      "component": "genkit",
      "changelog-sections": [...]
    },
    "plugins/google-genai": {
      "component": "genkit-plugin-google-genai"
    }
  }
}
```

### After

```toml
# releasekit.toml (generated)
forge = "github"
repo_owner = "firebase"
repo_name = "genkit"

[workspace.py]
ecosystem = "python"
root = "py"
tag_format = "{name}-v{version}"
```

### What changes

| Concept | release-please | ReleaseKit |
|---------|---------------|------------|
| Config format | JSON (2 files) | TOML (1 file) |
| Version storage | Manifest JSON | `pyproject.toml` (source of truth) |
| Tag format | `{component}-v{version}` | `{name}-v{version}` (same default) |
| Changelog | Per-package CHANGELOG.md | Per-package CHANGELOG.md (same) |
| PR flow | Release PR → merge → tag | Release PR → merge → tag (same) |

### What stays the same

- **Git tags** — ReleaseKit reads existing tags. No re-tagging needed.
- **Conventional Commits** — Same commit format, same bump rules.
- **CHANGELOG.md** — Same per-package changelogs.
- **Release PR flow** — Same prepare → review → merge → publish pattern.

## Migration from semantic-release

```bash
releasekit migrate --from semantic-release
```

### Key differences

| Concept | semantic-release | ReleaseKit |
|---------|-----------------|------------|
| Scope | Single package | Monorepo-native |
| Config | `.releaserc` + plugins | `releasekit.toml` |
| Plugins | `@semantic-release/*` | Built-in (no plugins needed) |
| Monorepo | Requires `semantic-release-monorepo` | Native support |

## Migration from changesets

```bash
releasekit migrate --from changesets
```

### Key differences

| Concept | changesets | ReleaseKit |
|---------|-----------|------------|
| Version tracking | `.changeset/*.md` files | Conventional Commits (git history) |
| Bump declaration | Manual changeset files | Automatic from commit messages |
| Config | `.changeset/config.json` | `releasekit.toml` |

!!! tip "No more changeset files"
    With ReleaseKit, you don't need to create `.changeset/*.md` files.
    Version bumps are computed automatically from Conventional Commit
    messages (`feat:`, `fix:`, `feat!:`, etc.).

## Migration from lerna

```bash
releasekit migrate --from lerna
```

### Key differences

| Concept | lerna | ReleaseKit |
|---------|-------|------------|
| Versioning | `lerna version` | `releasekit publish` (version + publish) |
| Fixed mode | `"version": "X.Y.Z"` in lerna.json | `synchronize = true` |
| Independent | `"version": "independent"` | Default (each package versioned independently) |

## Post-Migration Checklist

After migrating, verify everything works:

- [ ] `releasekit doctor` passes
- [ ] `releasekit check` passes
- [ ] `releasekit plan` shows expected bumps
- [ ] `releasekit discover` lists all packages
- [ ] `releasekit graph` shows correct dependencies
- [ ] Old tool config files can be removed (keep as backup first)

## Overwriting Existing Config

If `releasekit.toml` already exists:

```bash
# Won't overwrite — shows a message
releasekit migrate --from release-please

# Force overwrite
releasekit migrate --from release-please --force
```

## Next Steps

- [Getting Started](getting-started.md) — Full setup walkthrough
- [Configuration](configuration.md) — Customize the generated config
- [CI/CD Integration](ci-cd.md) — Set up automated releases
