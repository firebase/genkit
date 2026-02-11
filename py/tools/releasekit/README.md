# releasekit

Release orchestration for uv workspaces — publish Python packages in
topological order with dependency-triggered scheduling, ephemeral version
pinning, retry with jitter, crash-safe file restoration, and post-publish
checksum verification.

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
| `check` | Run standalone workspace health checks |
| `bump` | Bump version for one or all packages |
| `init` | Scaffold `[tool.releasekit]` config with auto-detected groups |
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

Scaffolds `[tool.releasekit]` in `pyproject.toml` with auto-detected
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

`releasekit check` runs 10 checks split into two categories:

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

The `CheckBackend` protocol allows adding language-specific checks
for other runtimes (Go, JS) without modifying the core check runner.

### Preflight Checks

`run_preflight` gates the publish pipeline with environment checks:
- Clean git worktree
- Lock file up to date
- No shallow clone
- No dependency cycles
- No stale dist/ directories
- Trusted publisher (OIDC) detection
- Version conflict check against PyPI

## Architecture

```
releasekit
├── Backends (DI / Protocol-based)
│   ├── VCS          git operations (tag, commit, push)
│   ├── PackageManager  uv operations (build, publish, lock)
│   ├── Registry     PyPI queries (poll, checksum verify)
│   └── Forge        GitHub operations (release, PR)
│
├── Core Pipeline
│   ├── workspace.py     discover packages from pyproject.toml
│   ├── graph.py         build & topo-sort dependency graph
│   ├── versions.py      semantic version bumping
│   ├── pin.py           ephemeral dep pinning with crash-safe restore
│   ├── preflight.py     pre-publish safety checks
│   ├── scheduler.py     dependency-triggered queue dispatcher
│   ├── publisher.py     async publish orchestration
│   └── checks.py        standalone workspace health checks
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
┌───────────────────────────────────────────────────────┐
│                     Scheduler                         │
│                                                       │
│  from_graph() ──▶ seed level-0 ──▶ Queue              │
│                                      │                │
│         ┌────────────────────────────┼──────────┐     │
│         │          Semaphore(N)      │          │     │
│         │                            ▼          │     │
│     ┌────────┐ ┌────────┐ ... ┌────────┐       │     │
│     │Worker 0│ │Worker 1│     │Worker N│       │     │
│     └───┬────┘ └───┬────┘     └───┬────┘       │     │
│         │          │              │             │     │
│         └──────────┴──────┬───────┘             │     │
│                           │                     │     │
│                     publish_fn(name)             │     │
│                           │                     │     │
│                    ┌──────┴──────┐              │     │
│                    │  mark_done  │              │     │
│                    └──────┬──────┘              │     │
│                           │                     │     │
│              decrement dependents' counters      │     │
│              enqueue newly-ready packages        │     │
│                           │                     │     │
│                    ┌──────┴──────┐              │     │
│                    │    Queue    │◀─────────────┘     │
│                    └─────────────┘                    │
└───────────────────────────────────────────────────────┘
```

## Why This Tool Exists

The genkit Python SDK is a uv workspace with 60+ packages that have
inter-dependencies. Publishing them to PyPI requires dependency-ordered
builds with ephemeral version pinning — and no existing tool does this.

See [roadmap.md](roadmap.md) for the full design rationale and
implementation plan.

## License

Apache 2.0 — see [LICENSE](../../LICENSE) for details.
