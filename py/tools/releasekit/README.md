# releasekit

Release orchestration for uv workspaces — publish Python packages in
topological order with dependency-triggered scheduling, ephemeral version
pinning, retry with jitter, crash-safe file restoration, and post-publish
checksum verification.

## Quick Start

```bash
# Preview what would happen
uvx releasekit plan

# Publish all changed packages
uvx releasekit publish

# Discover workspace packages
uvx releasekit discover

# Show dependency graph
uvx releasekit graph

# Run workspace health checks
uvx releasekit check
```

## Commands

| Command | Description |
|---------|-------------|
| `discover` | List all workspace packages with versions and metadata |
| `graph` | Print the dependency graph in topological order |
| `plan` | Preview version bumps and publish order (dry run) |
| `publish` | Build and publish packages to PyPI in dependency order |
| `check` | Run standalone workspace health checks |
| `bump` | Bump version for one or all packages |

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
├── Extensibility
│   ├── CheckBackend     protocol for language-specific checks
│   ├── PythonCheckBackend  py.typed, version sync, naming, metadata
│   └── (future: GoCheckBackend, JsCheckBackend, plugins)
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

### Publish Pipeline

Packages are dispatched via a dependency-triggered queue — each package
starts as soon as all its dependencies complete (no level-based lockstep).

#### Why Dependency-Triggered?

**Before (lock-step per level):**

```
Level 0:  [A] [B] [C]     ← wait for ALL to finish
              ↓
Level 1:  [D] [E]          ← wait for ALL to finish
              ↓
Level 2:  [F]              ← no parallelism across levels
```

D and E are blocked until A, B, *and* C all finish — even though D
only depends on A.  A single slow package in level 0 delays the entire
pipeline.

**After (dependency-triggered queue):**

```
Queue: ┌─A─┐ ┌─B─┐ ┌─C─┐
       └─┬─┘ └───┘ └───┘
         │ A done → D ready
       ┌─▼─┐
       │ D │                 ← starts as soon as A finishes
       └─┬─┘
         │ D done + B done → E ready
       ┌─▼─┐
       │ E │
       └─┬─┘
         │ E done → F ready
       ┌─▼─┐
       │ F │
       └───┘
```

Each package starts the moment its dependencies are done.  Workers pull
from the queue as fast as they can — no artificial synchronisation
barriers between levels.

### Publish Pipeline

Each package goes through:

```
pin → build → checksum → publish → poll → verify_checksum → smoke_test → restore
```

On failure, the scheduler retries with exponential backoff + full jitter
(configurable `--max-retries`, `--retry-base-delay`). Failed packages block
their dependents (fail-fast for the dependency chain).

1. **Pin** — temporarily rewrite internal deps to exact versions
2. **Build** — `uv build --no-sources` into temp directory
3. **Checksum** — compute SHA-256 of .tar.gz and .whl
4. **Publish** — `uv publish` with `--check-url` for idempotency
5. **Poll** — wait for PyPI to index the new version
6. **Verify checksum** — download SHA-256 from PyPI JSON API,
   compare against local build (supply chain integrity)
7. **Smoke test** — `uv pip install` in isolated venv
8. **Restore** — revert pinned pyproject.toml to original

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

## Why This Tool Exists

The genkit Python SDK is a uv workspace with 60+ packages that have
inter-dependencies. Publishing them to PyPI requires dependency-ordered
builds with ephemeral version pinning — and no existing tool does this.

See [roadmap.md](roadmap.md) for the full design rationale and
implementation plan.

## License

Apache 2.0 — see [LICENSE](../../LICENSE) for details.
