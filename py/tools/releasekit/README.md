# releasekit

Release orchestration for uv workspaces — publish Python packages in
topological order with dependency-triggered scheduling, ephemeral version
pinning, retry with jitter, crash-safe file restoration, and post-publish
checksum verification.

## Why This Tool Exists

The Genkit Python SDK is a uv workspace with 60+ packages that have
inter-dependencies. Publishing them to PyPI requires dependency-ordered
builds with ephemeral version pinning — and no existing tool does this.

`uv publish` is a **single-package** command. It publishes one wheel or
sdist to PyPI. It does not understand workspaces, dependency graphs, or
multi-package release orchestration. releasekit fills that gap:

| Feature | `uv publish` | `releasekit` |
|---------|:--:|:--:|
| Publish a single package | ✅ | ✅ (calls `uv publish` internally) |
| Dependency graph ordering | ❌ | ✅ topological sort |
| Multi-package workspace publish | ❌ | ✅ all packages in order |
| Version bump computation | ❌ | ✅ git-based semver |
| Transitive dependency propagation | ❌ | ✅ patch bump dependents |
| Concurrency within topo levels | ❌ | ✅ parallel within a level |
| Pre/post-publish checks | ❌ | ✅ preflight + smoke test |
| Retry with backoff | ❌ | ✅ configurable |
| Exclude lists / groups | ❌ | ✅ `exclude`, `exclude_publish`, `exclude_bump` |
| Git tagging | ❌ | ✅ per-package + umbrella |
| Changelog generation | ❌ | ✅ from conventional commits |
| Release manifest | ❌ | ✅ JSON record of what shipped |
| Crash-safe resume | ❌ | ✅ state file + `--resume` |
| SIGUSR1/SIGUSR2 pause/resume | ❌ | ✅ live scheduler control |

`uv publish` is the low-level primitive. releasekit is the orchestrator
that calls it per-package at the right time in the right order.

See [roadmap.md](roadmap.md) for the full design rationale and
implementation plan.

## Getting Started

```bash
# 1. Install (or run directly with uvx)
uv tool install releasekit

# 2. Initialize config in your workspace root
releasekit init

# 3. Preview what would happen
releasekit plan

# 4. Publish all changed packages
releasekit publish

# 5. Enable shell completions (bash, zsh, or fish)
eval "$(releasekit completion bash)"
```

Or run without installing:

```bash
uvx releasekit discover
uvx releasekit graph --format table
uvx releasekit check
```

## Commands

| Command | Description |
|---------|-------------|
| `discover` | List all workspace packages with versions and metadata |
| `graph` | Print the dependency graph (8 output formats) |
| `plan` | Preview version bumps and publish order (dry run) |
| `publish` | Build and publish packages to PyPI in dependency order |
| `prepare` | Bump versions, generate changelogs, open a Release PR |
| `release` | Tag a merged Release PR and create a GitHub Release |
| `check` | Run standalone workspace health checks |
| `bump` | Bump version for one or all packages |
| `init` | Scaffold `releasekit.toml` config with auto-detected groups |
| `rollback` | Delete a git tag (local + remote) and its GitHub release |
| `explain` | Look up any error code (e.g. `releasekit explain RK-GRAPH-CYCLE-DETECTED`) |
| `version` | Show the releasekit version |
| `completion` | Generate shell completion scripts (bash/zsh/fish) |

## Features

### Graph Formatters

`releasekit graph --format <fmt>` supports 8 output formats:

| Format | Output | Use case |
|--------|--------|----------|
| `ascii` | Box-drawing art | Terminal viewing |
| `csv` | RFC 4180 + UTF-8 BOM | Excel, Google Sheets, data pipelines |
| `d2` | D2 diagram DSL | `d2 render` |
| `dot` | Graphviz DOT | `dot -Tpng` / `dot -Tsvg` |
| `json` | Structured JSON | Scripting, CI, jq |
| `levels` | Simple text (default) | Quick inspection |
| `mermaid` | Mermaid flowchart | GitHub READMEs, docs |
| `table` | Markdown table | READMEs, docs, PRs |

```bash
# Render as Mermaid for a README
releasekit graph --format mermaid > deps.mmd

# Export as CSV for a spreadsheet
releasekit graph --format csv > deps.csv

# Render as Graphviz SVG
releasekit graph --format dot | dot -Tsvg -o deps.svg

# Show as a Markdown table
releasekit graph --format table
```

### Publish Pipeline

Each package goes through:

```
pin → build → checksum → publish → poll → verify_checksum → smoke_test → restore
```

Packages are dispatched via a **dependency-triggered queue** — each
package starts as soon as all its dependencies complete (no level-based
lockstep). Workers pull from the queue as fast as they can.

Granular control:

```bash
releasekit publish --dry-run             # Preview mode
releasekit publish --version-only        # Bump versions, skip build/publish
releasekit publish --no-tag --no-push    # Publish without tagging/pushing
releasekit publish --no-release          # Skip GitHub release creation
releasekit publish --max-retries 3       # Retry failed publishes
releasekit publish --concurrency 10      # Max parallel per level
```

On failure, the scheduler retries with exponential backoff + full jitter.
Failed packages block their dependents (fail-fast for the dependency chain).

### Workspace Initialization

```bash
releasekit init              # Auto-detect groups, write config
releasekit init --dry-run    # Preview generated config
releasekit init --force      # Overwrite existing config
```

Scaffolds `releasekit.toml` in the workspace root with auto-detected
package groups (plugins, samples, core). Also adds `.releasekit-state/`
to `.gitignore`.

### Rollback

```bash
releasekit rollback genkit-v0.5.0            # Delete tag + GitHub release
releasekit rollback genkit-v0.5.0 --dry-run  # Preview what would be deleted
```

### Rust-Style Diagnostics

All errors and warnings use Rust-compiler-style formatting:

```
error[RK-GRAPH-CYCLE-DETECTED]: Circular dependency detected in the workspace dependency graph.
  |
  = hint: Run 'releasekit check-cycles' to identify the cycle.
```

Every error code can be looked up:

```bash
releasekit explain RK-PREFLIGHT-DIRTY-WORKTREE
```

### Shell Completions

```bash
# Bash — add to ~/.bashrc
eval "$(releasekit completion bash)"

# Zsh — add to ~/.zshrc
eval "$(releasekit completion zsh)"

# Fish — save to completions dir
releasekit completion fish > ~/.config/fish/completions/releasekit.fish
```

### Health Checks

`releasekit check` runs 19 checks split into two categories:

**Universal checks** (always run):
- `cycles` — circular dependency chains
- `self_deps` — package depends on itself
- `orphan_deps` — internal dep not in workspace
- `missing_license` — no LICENSE file
- `missing_readme` — no README.md
- `stale_artifacts` — leftover .bak or dist/ files

**Language-specific checks** (via `CheckBackend` protocol):
- `type_markers` — py.typed PEP 561 marker
- `version_consistency` — plugin version matches core
- `naming_convention` — directory matches package name
- `metadata_completeness` — pyproject.toml required fields
- `python_version` — consistent `requires-python` across packages
- `python_classifiers` — Python version classifiers (3.10–3.14)
- `dependency_resolution` — `uv pip check` passes
- `namespace_init` — no `__init__.py` in namespace directories
- `readme_field` — publishable packages declare `readme` in `[project]`
- `changelog_url` — publishable packages have `Changelog` in `[project.urls]`
- `publish_classifier_consistency` — `exclude_publish` agrees with `Private :: Do Not Upload`
- `ungrouped_packages` — all packages appear in at least one `[groups]` pattern
- `lockfile_staleness` — `uv.lock` is in sync with `pyproject.toml`

The `CheckBackend` protocol allows adding language-specific checks
for other runtimes (Go, JS) without modifying the core check runner.

### Preflight Checks

`run_preflight` gates the publish pipeline with environment checks.
Checks are split into **universal** (always run) and **ecosystem-specific**
(gated by `ecosystem` parameter):

**Universal checks:**
- Clean git worktree
- Lock file up to date
- No shallow clone
- No dependency cycles
- No stale dist/ directories
- Trusted publisher (OIDC) detection
- Version conflict check against the registry

**Python-specific checks** (`ecosystem='python'`):
- `metadata_validation` — pyproject.toml has description, license, authors
- `pip_audit` — vulnerability scan (advisory, opt-in via `run_audit=True`)

The `ecosystem` parameter enables forward-compatible extensibility: future
ecosystems (Node/npm, Rust/cargo, Go) can add their own checks (e.g.
`npm audit`, `cargo audit`, `govulncheck`) without modifying universal logic.

### Resume / State

Every publish run persists state to `.releasekit-state.json` after each
package completes. On crash or failure:

```bash
# Resume from where we left off
releasekit publish --resume

# Force restart from scratch
releasekit publish --fresh
```

The state file tracks:
- Per-package status (`pending`, `building`, `published`, `failed`)
- Git SHA at start (refuses to resume if HEAD changed)
- Checksums of published artifacts

### SIGUSR1/SIGUSR2 Controls

During a live publish, you can pause and resume the scheduler:

```bash
kill -USR1 <pid>   # Pause: finish current packages, stop starting new ones
kill -USR2 <pid>   # Resume: continue processing the queue
```

## Configuration

releasekit reads configuration from a standalone `releasekit.toml` file
in the workspace root. Use `releasekit init` to scaffold one:

```toml
# releasekit.toml
changelog    = true
smoke_test   = true
tag_format   = "{name}-v{version}"
umbrella_tag = "v{version}"

exclude_publish = ["group:samples"]

[groups]
core = ["genkit"]
samples = ["*-hello", "*-demo", "web-*"]
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `tag_format` | `{name}/v{version}` | Git tag template |
| `umbrella_tag` | `v{version}` | Umbrella tag for the release |
| `synchronize` | `false` | Lockstep versioning (all packages same version) |
| `concurrency` | `5` | Max parallel publish workers |
| `smoke_test` | `true` | Run `python -c 'import ...'` after publish |
| `verify_checksums` | `true` | Verify SHA-256 against registry |
| `exclude` | `[]` | Glob patterns to exclude from discovery entirely |
| `exclude_publish` | `[]` | Glob patterns to skip during publish (still discovered + bumped) |
| `exclude_bump` | `[]` | Glob patterns to skip during version bumps (still discovered + checked) |
| `poll_timeout` | `300.0` | Seconds to wait for package availability |
| `max_retries` | `0` | Retry count per package on transient failure |

### Exclusion Hierarchy

The three exclude levels control how much of the pipeline a package participates in:

| Level | Discovered | Checked | Version-bumped | Published |
|-------|:--:|:--:|:--:|:--:|
| *(normal)* | ✅ | ✅ | ✅ | ✅ |
| `exclude_publish` | ✅ | ✅ | ✅ | ❌ |
| `exclude_bump` | ✅ | ✅ | ❌ | ❌ |
| `exclude` | ❌ | ❌ | ❌ | ❌ |

### Group References

All exclude lists support `group:<name>` references that expand to the
patterns defined in `[groups]`. Groups can reference other groups
recursively — cycles are detected and reported as errors.

```toml
[groups]
core = ["genkit"]
google_plugins = ["genkit-plugin-firebase", "genkit-plugin-google-*"]
community_plugins = ["genkit-plugin-anthropic", "genkit-plugin-ollama"]
all_plugins = ["group:google_plugins", "group:community_plugins"]
samples = ["*-hello", "*-demo", "web-*"]

exclude_publish = [
  "group:samples",              # entire group
  "genkit-plugin-amazon-bedrock", # specific package
]
```

## Architecture

```
releasekit
├── Backends (DI / Protocol-based)
│   ├── VCS              git / hg operations (tag, commit, push)
│   │   ├── git.py         GitCLIBackend (default)
│   │   └── mercurial.py   MercurialCLIBackend
│   ├── PackageManager   build, publish, lock
│   │   ├── uv.py          UvBackend (default)
│   │   └── pnpm.py        PnpmBackend
│   ├── Workspace        package discovery
│   │   ├── uv.py          UvWorkspaceBackend (default)
│   │   └── pnpm.py        PnpmWorkspaceBackend
│   ├── Registry         package registry queries
│   │   ├── pypi.py        PyPIBackend (default)
│   │   └── npm.py         NpmRegistry
│   └── Forge            release / PR management
│       ├── github.py      GitHubCLIBackend (default)
│       ├── github_api.py  GitHubAPIBackend (REST, for CI)
│       ├── gitlab.py      GitLabCLIBackend
│       └── bitbucket.py   BitbucketAPIBackend
│
├── Core Pipeline
│   ├── workspace.py     discover packages from pyproject.toml
│   ├── graph.py         build & topo-sort dependency graph
│   ├── versioning.py    conventional commits parsing + semver bumps
│   ├── versions.py      version data structures (ReleaseManifest, PackageVersion)
│   ├── bump.py          rewrite version in pyproject.toml
│   ├── pin.py           ephemeral dep pinning with crash-safe restore
│   ├── changelog.py     changelog generation from commits
│   ├── preflight.py     pre-publish safety checks
│   ├── checks.py        standalone workspace health checks
│   ├── scheduler.py     dependency-triggered queue dispatcher
│   ├── publisher.py     async publish orchestration
│   ├── prepare.py       release preparation (bump + changelog + PR)
│   ├── release.py       release tagging (tag merge commit + create Release)
│   ├── plan.py          execution plan preview
│   ├── state.py         crash-safe publish state persistence
│   ├── lock.py          lockfile management
│   ├── net.py           async HTTP utilities
│   ├── tags.py          git tag utilities
│   ├── release_notes.py release notes generation
│   ├── commitback.py    commit-back version bumps
│   ├── detection.py     multi-ecosystem auto-detection
│   └── groups.py        release group filtering
│
├── Formatters
│   ├── ascii_art.py     box-drawing terminal art
│   ├── csv_fmt.py       RFC 4180 CSV with UTF-8 BOM
│   ├── d2.py            D2 diagram DSL
│   ├── dot.py           Graphviz DOT
│   ├── json_fmt.py      structured JSON
│   ├── levels.py        simple text listing (default)
│   ├── mermaid.py       Mermaid flowchart
│   ├── table.py         Markdown table
│   └── registry.py      format dispatcher
│
├── UX
│   ├── errors.py        error catalog + Rust-style render_error/render_warning
│   ├── logging.py       structured logging setup
│   ├── config.py        TOML config loading + validation
│   ├── init.py          workspace config scaffolding
│   └── cli.py           argparse + rich-argparse + shell completion
│
├── Observer
│   └── observer.py      PublishStage, SchedulerState, PublishObserver
│
└── UI
    ├── RichProgressUI   live progress table (TTY) + sliding window
    ├── LogProgressUI    structured logs (CI)
    ├── NullProgressUI   no-op (tests)
    └── Controls         p=pause r=resume q=cancel a=all w=window f=filter
```

### Scheduler Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                          Scheduler                                │
│                                                                   │
│  from_graph() ──▶ seed level-0 ──▶ Queue                          │
│                                      │                            │
│         ┌────────────────────────────┼──────────┐                 │
│         │          Semaphore(N)      │          │                 │
│         │                            ▼          │                 │
│     ┌────────┐ ┌────────┐ ... ┌────────┐       │                 │
│     │Worker 0│ │Worker 1│     │Worker N│       │                 │
│     └───┬────┘ └───┬────┘     └───┬────┘       │                 │
│         │          │              │             │                 │
│         └──────────┴──────┬───────┘             │                 │
│                           │                     │                 │
│                     publish_fn(name)             │                 │
│                           │                     │                 │
│                    ┌──────┴──────┐              │                 │
│                    │  mark_done  │              │                 │
│                    └──────┬──────┘              │                 │
│                           │                     │                 │
│              decrement dependents' counters      │                 │
│              enqueue newly-ready packages        │                 │
│                           │                     │                 │
│                    ┌──────┴──────┐              │                 │
│                    │    Queue    │◀─────────────┘                 │
│                    └─────────────┘                                │
└───────────────────────────────────────────────────────────────────┘
```

### Backend Protocols

All I/O goes through protocol-defined backends. This enables:
- **Testing** with in-memory fakes (no subprocess calls)
- **Future ecosystems** by implementing new backends (e.g. `CargoBackend`)
- **CI/local parity** — same code path, different backends

```python
# Protocols defined in:
#   releasekit.backends.vcs         VCS
#   releasekit.backends.pm          PackageManager
#   releasekit.backends.workspace   Workspace
#   releasekit.backends.registry    Registry
#   releasekit.backends.forge       Forge

# Concrete implementations:
#   VCS:            GitCLIBackend, MercurialCLIBackend
#   PackageManager: UvBackend, PnpmBackend
#   Workspace:      UvWorkspaceBackend, PnpmWorkspaceBackend
#   Registry:       PyPIBackend, NpmRegistry
#   Forge:          GitHubCLIBackend, GitHubAPIBackend, GitLabCLIBackend, BitbucketAPIBackend
```

### Ecosystem Abstraction

Some operations are currently Python-specific but follow a pattern that
enables multi-ecosystem support:

| Module | Current State | Abstraction Path |
|--------|--------------|------------------|
| `bump.py` | Rewrites `pyproject.toml` | → `Workspace.rewrite_version()` |
| `pin.py` | Rewrites deps in `pyproject.toml` | → `Workspace.rewrite_dependency_version()` |
| `config.py` | Reads `releasekit.toml` | ✅ Already standalone (ecosystem-agnostic) |
| `checks.py` | `PythonCheckBackend` | ✅ Already protocol-based |
| `preflight.py` | `pip-audit`, metadata | ✅ Gated by `ecosystem=` param |

## Testing

```bash
# Run all tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=releasekit --cov-report=term-missing

# Specific module
uv run pytest tests/rk_publisher_test.py -v
```

### Testing Strategy

- All backends are injected via **dependency injection** — tests use
  in-memory fakes that satisfy the protocol contracts.
- No subprocess calls, no network I/O, no file system side effects
  (except `tmp_path`).
- Standard library assertions (`if/else` + `raise AssertionError`)
  following the want/got pattern.
- Complex comparisons use `dataclasses.asdict` for readable diffs.

## Security

- **No credentials in code** — PyPI tokens come from environment
  (`UV_PUBLISH_TOKEN`) or trusted publishing (OIDC).
- **Checksum verification** — SHA-256 checksums are computed locally
  and verified against the registry after publish.
- **Ephemeral pinning** — dependency rewrites use crash-safe
  backup/restore with `.bak` files.
- **State file integrity** — resume refuses if HEAD SHA differs.

## License

Apache 2.0 — see [LICENSE](../../LICENSE) for details.

