# releasekit

Release orchestration for uv workspaces — publish Python packages in
topological order with ephemeral version pinning, level gating, and
crash-safe file restoration.

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
```

## Why This Tool Exists

The genkit Python SDK is a uv workspace with 21+ packages that have
inter-dependencies. Publishing them to PyPI requires dependency-ordered
builds with ephemeral version pinning — and no existing tool does this.

See [roadmap.md](roadmap.md) for the full design rationale and
implementation plan.

## License

Apache 2.0 — see [LICENSE](../../LICENSE) for details.
