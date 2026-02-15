---
title: Configuration File Reference
description: Schema reference for releasekit.toml.
---

# Configuration File Reference

`releasekit.toml` is a flat TOML file at the monorepo root. No nesting
under `[tool.*]` — it works for any ecosystem.

## Schema

```toml
# ── Global Keys ──────────────────────────────────────────
forge            = "github"             # "github" | "gitlab" | "bitbucket" | "none"
repo_owner       = "firebase"           # GitHub/GitLab org or user
repo_name        = "genkit"             # Repository name
default_branch   = "main"              # Override auto-detected default branch
publish_from     = "local"              # "local" | "ci"
http_pool_size   = 10                   # HTTP connection pool
pr_title_template = "chore(release): v{version}"

# ── Workspace Section ────────────────────────────────────
# Each [workspace.<label>] defines a release unit.
[workspace.py]
ecosystem       = "python"              # "python" | "js" | "go" | "rust" | "jvm" | "dart"
tool            = "uv"                  # Defaults per ecosystem (python→uv, js→pnpm)
root            = "py"                  # Relative path from repo root

# ── Tagging ──────────────────────────────────────────────
tag_format      = "{name}-v{version}"   # Per-package tag
umbrella_tag    = "v{version}"          # Umbrella tag

# ── Exclusions ───────────────────────────────────────────
exclude         = []                    # Exclude from everything
exclude_bump    = []                    # Exclude from version bumps
exclude_publish = []                    # Exclude from publishing

# ── Features ─────────────────────────────────────────────
changelog       = true                  # Generate changelogs
prerelease_mode = "rollup"              # "rollup" | "separate"
synchronize     = false                 # Lockstep versioning
smoke_test      = true                  # Post-publish smoke test
propagate_bumps = true                  # Transitive PATCH bumps to dependents

# ── Versioning ────────────────────────────────────────
major_on_zero     = false               # Allow 0.x → 1.0.0 on breaking
max_commits     = 0                     # Max commits to scan (0 = unlimited)
bootstrap_sha   = ""                    # Starting SHA for mid-stream adoption

# ── JS Publishing (ignored for Python) ───────────────────────
dist_tag        = ""                    # npm dist-tag ("latest", "next")
publish_branch  = ""                    # pnpm --publish-branch
provenance      = false                 # pnpm --provenance

# ── Extra Files ───────────────────────────────────────────
extra_files       = []                  # Additional files to version-bump

# ── Checks ────────────────────────────────────────────────
core_package    = ""                    # Core package for version checks
plugin_prefix   = ""                    # Expected prefix for plugin names
namespace_dirs  = []                    # Dirs requiring PEP 420 checks
library_dirs    = []                    # Parent dirs needing py.typed
plugin_dirs     = []                    # Parent dirs with naming conventions

# ── Groups ─────────────────────────────────────────────────
[workspace.py.groups]
core    = ["genkit"]
plugins = ["genkit-plugin-*"]
```

## Global Key Types

| Key | Type | Allowed Values |
|-----|------|---------------|
| `forge` | `string` | `"github"`, `"gitlab"`, `"bitbucket"`, `"none"` |
| `repo_owner` | `string` | GitHub/GitLab org or user |
| `repo_name` | `string` | Repository name |
| `default_branch` | `string` | Branch name (auto-detected if omitted) |
| `publish_from` | `string` | `"local"`, `"ci"` |
| `http_pool_size` | `int` | Positive integer |
| `pr_title_template` | `string` | Any string with `{version}` placeholder |

## Workspace Key Types

| Key | Type | Allowed Values |
|-----|------|---------------|
| `ecosystem` | `string` | `"python"`, `"js"`, `"go"`, `"rust"`, `"jvm"`, `"dart"` |
| `tool` | `string` | `"uv"`, `"pnpm"`, `"cargo"`, etc. (defaults per ecosystem) |
| `root` | `string` | Relative path from repo root (default `"."`) |
| `tag_format` | `string` | Any string with `{name}` and `{version}` placeholders |
| `umbrella_tag` | `string` | Any string with `{version}` placeholder |
| `exclude` | `list[string]` | Glob patterns or `"group:<name>"` refs |
| `exclude_bump` | `list[string]` | Glob patterns or `"group:<name>"` refs |
| `exclude_publish` | `list[string]` | Glob patterns or `"group:<name>"` refs |
| `changelog` | `bool` | `true`, `false` |
| `prerelease_mode` | `string` | `"rollup"`, `"separate"` |
| `synchronize` | `bool` | `true`, `false` |
| `smoke_test` | `bool` | `true`, `false` |
| `propagate_bumps` | `bool` | `true`, `false` (default `true`) |
| `major_on_zero` | `bool` | `true`, `false` |
| `max_commits` | `int` | Non-negative integer (0 = unlimited) |
| `bootstrap_sha` | `string` | Git SHA or empty string |
| `dist_tag` | `string` | npm dist-tag (e.g. `"latest"`, `"next"`) — JS only |
| `publish_branch` | `string` | Branch name for `pnpm --publish-branch` — JS only |
| `provenance` | `bool` | `true`, `false` — JS only |
| `extra_files` | `list[string]` | File paths or `"path:regex"` pairs |
| `groups` | `table` | `{name: list[string]}` |
| `core_package` | `string` | Package name for version checks |
| `plugin_prefix` | `string` | Expected prefix for plugin names |
| `namespace_dirs` | `list[string]` | Dirs requiring PEP 420 checks |
| `library_dirs` | `list[string]` | Parent dirs needing `py.typed` |
| `plugin_dirs` | `list[string]` | Parent dirs with naming conventions |

## Group Patterns

Groups support:

- **Glob patterns**: `"genkit-plugin-*"` matches `genkit-plugin-foo`
- **Group references**: `"group:plugins"` expands to the patterns in the `plugins` group
- **Nesting**: Groups can reference other groups

```toml
[workspace.py.groups]
google    = ["genkit-plugin-google-*", "genkit-plugin-vertex-*"]
community = ["genkit-plugin-ollama", "genkit-plugin-anthropic"]
all       = ["group:google", "group:community"]
```
