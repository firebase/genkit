---
title: Configuration File Reference
description: Schema reference for releasekit.toml.
---

# Configuration File Reference

`releasekit.toml` is a flat TOML file at the monorepo root. No nesting
under `[tool.*]` — it works for any ecosystem.

## Schema

```toml
# ── Tagging ──────────────────────────────────────────────
tag_format      = "{name}-v{version}"   # Per-package tag
umbrella_tag    = "v{version}"          # Umbrella tag

# ── Publishing ───────────────────────────────────────────
publish_from    = "local"               # "local" | "ci"

# ── Exclusions ───────────────────────────────────────────
exclude         = []                    # Exclude from everything
exclude_bump    = []                    # Exclude from version bumps
exclude_publish = []                    # Exclude from publishing

# ── Features ─────────────────────────────────────────────
changelog       = true                  # Generate changelogs
prerelease_mode = "rollup"              # "rollup" | "separate"
synchronize     = false                 # Lockstep versioning
smoke_test      = true                  # Post-publish smoke test
http_pool_size  = 10                    # HTTP connection pool

# ── Groups ───────────────────────────────────────────────
[groups]
core    = ["genkit"]
plugins = ["genkit-plugin-*"]
```

## Key Types

| Key | Type | Allowed Values |
|-----|------|---------------|
| `tag_format` | `string` | Any string with `{name}` and `{version}` placeholders |
| `umbrella_tag` | `string` | Any string with `{version}` placeholder |
| `publish_from` | `string` | `"local"`, `"ci"` |
| `exclude` | `list[string]` | Glob patterns or `"group:<name>"` refs |
| `exclude_bump` | `list[string]` | Glob patterns or `"group:<name>"` refs |
| `exclude_publish` | `list[string]` | Glob patterns or `"group:<name>"` refs |
| `changelog` | `bool` | `true`, `false` |
| `prerelease_mode` | `string` | `"rollup"`, `"separate"` |
| `synchronize` | `bool` | `true`, `false` |
| `smoke_test` | `bool` | `true`, `false` |
| `http_pool_size` | `int` | Positive integer |
| `groups` | `table` | `{name: list[string]}` |

## Group Patterns

Groups support:

- **Glob patterns**: `"genkit-plugin-*"` matches `genkit-plugin-foo`
- **Group references**: `"group:plugins"` expands to the patterns in the `plugins` group
- **Nesting**: Groups can reference other groups

```toml
[groups]
google    = ["genkit-plugin-google-*", "genkit-plugin-vertex-*"]
community = ["genkit-plugin-ollama", "genkit-plugin-anthropic"]
all       = ["group:google", "group:community"]
```
