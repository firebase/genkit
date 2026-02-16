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
versioning_scheme = "semver"             # "semver" | "pep440" | "calver" (auto from ecosystem)
calver_format   = "YYYY.MM.MICRO"       # CalVer format (when versioning_scheme = "calver")
major_on_zero     = false               # Allow 0.x → 1.0.0 on breaking
max_commits     = 0                     # Max commits to scan (0 = unlimited)
bootstrap_sha   = ""                    # Starting SHA for mid-stream adoption

# ── Supply Chain Security ────────────────────────────────────
slsa_provenance = false                 # Generate SLSA Provenance v1 in-toto statement
sign_provenance = false                 # Sign provenance with Sigstore (implies slsa_provenance)

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

# ── Per-Package Overrides ──────────────────────────────────
# Override any per-package field for a specific package or group.
[workspace.py.packages."my-js-lib"]
versioning_scheme = "semver"
dist_tag          = "next"

[workspace.py.packages."my-py-lib"]
versioning_scheme = "pep440"
registry_url      = "https://test.pypi.org"
major_on_zero     = true

# ── Announcements ──────────────────────────────────────────
[workspace.py.announcements]
slack_webhook   = "$SLACK_WEBHOOK_URL"
discord_webhook = "$DISCORD_WEBHOOK_URL"
irc_webhook     = "$IRC_BRIDGE_URL"
template        = "Released ${version}: ${packages}"

[workspace.py.announcements.overrides.plugins]
slack_webhook = "$SLACK_PLUGINS_WEBHOOK"
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
| `versioning_scheme` | `string` | `"semver"`, `"pep440"`, `"calver"` (auto-detected from ecosystem) |
| `calver_format` | `string` | CalVer format string (e.g. `"YYYY.MM.MICRO"`) |
| `groups` | `table` | `{name: list[string]}` |
| `packages` | `table` | Per-package config overrides (see below) |
| `core_package` | `string` | Package name for version checks |
| `plugin_prefix` | `string` | Expected prefix for plugin names |
| `namespace_dirs` | `list[string]` | Dirs requiring PEP 420 checks |
| `library_dirs` | `list[string]` | Parent dirs needing `py.typed` |
| `plugin_dirs` | `list[string]` | Parent dirs with naming conventions |

## Default Versioning Schemes

When `versioning_scheme` is not explicitly set, releasekit applies the
appropriate default based on the workspace ecosystem:

| Ecosystem | Default Scheme | Registry | Specification |
|-----------|---------------|----------|---------------|
| `python` | `pep440` | PyPI | [PEP 440](https://peps.python.org/pep-0440/) — `1.0.0a1`, `1.0.0rc1` |
| `js` | `semver` | npm | [Semantic Versioning 2.0.0](https://semver.org/) — `1.0.0-rc.1` |
| `go` | `semver` | Go proxy | [Go module versioning](https://go.dev/ref/mod#versions) |
| `rust` | `semver` | crates.io | [Cargo SemVer](https://doc.rust-lang.org/cargo/reference/semver.html) |
| `dart` | `semver` | pub.dev | [Dart versioning](https://dart.dev/tools/pub/versioning) |
| `java` | `semver` | Maven Central | [Maven versioning](https://maven.apache.org/pom.html#Version) |
| `jvm` | `semver` | Maven Central | Same as Java |
| `kotlin` | `semver` | Maven Central | Same as Java |
| `clojure` | `semver` | Clojars | [Leiningen versioning](https://codeberg.org/leiningen/leiningen) |
| `bazel` | `semver` | BCR | [Bazel Central Registry](https://registry.bazel.build/) |

Python is the only ecosystem that uses PEP 440 by default because PyPI
**requires** PEP 440 compliance. All other registries use or recommend
Semantic Versioning 2.0.0.

You can always override the default per-workspace or per-package:

```toml
# Force semver for a Python workspace
[workspace.py]
ecosystem = "python"
versioning_scheme = "semver"  # override pep440 default

# Or override per-package within a workspace
[workspace.mono.packages."my-py-lib"]
versioning_scheme = "pep440"
```

## Per-Package Configuration

Within a workspace, individual packages can override workspace-level
settings via `[workspace.<label>.packages.<name>]` sections. This is
useful for mixed-ecosystem workspaces or packages with special needs.

### Supported Per-Package Keys

| Key | Type | Description |
|-----|------|-------------|
| `versioning_scheme` | `string` | `"semver"`, `"pep440"`, or `"calver"` |
| `calver_format` | `string` | CalVer format string |
| `prerelease_label` | `string` | Default pre-release label (`"alpha"`, `"beta"`, `"rc"`, `"dev"`) |
| `changelog` | `bool` | Generate CHANGELOG.md entries |
| `changelog_template` | `string` | Path to Jinja2 changelog template |
| `smoke_test` | `bool` | Run install smoke test after publish |
| `major_on_zero` | `bool` | Allow `0.x → 1.0.0` on breaking changes |
| `extra_files` | `list[string]` | Extra files with version strings to bump |
| `dist_tag` | `string` | npm dist-tag (JS only) |
| `registry_url` | `string` | Custom registry URL |
| `provenance` | `bool` | npm provenance attestation (JS only) |

### Resolution Order

1. **Exact package name** — `[workspace.mono.packages."genkit-core"]`
2. **Group membership** — `[workspace.mono.packages.plugins]` (if `genkit-core` matches a pattern in the `plugins` group)
3. **Workspace default** — `[workspace.mono]`

### Example: Mixed Python + JS Workspace

```toml
[workspace.mono]
ecosystem = "python"
root = "."
versioning_scheme = "pep440"  # default for all packages

[workspace.mono.groups]
plugins = ["genkit-plugin-*"]
js-libs = ["my-js-*"]

# JS packages in a Python workspace use semver
[workspace.mono.packages.js-libs]
versioning_scheme = "semver"
dist_tag = "latest"

# One specific package publishes to test PyPI
[workspace.mono.packages."genkit-experimental"]
registry_url = "https://test.pypi.org"
major_on_zero = true
```

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
