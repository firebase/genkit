# Plugin Implementation Plans

This directory contains detailed implementation plans for proposed Genkit plugins.

## Summary Table

| Plugin | Type | Feasibility | Effort | Priority | Status |
|--------|------|-------------|--------|----------|--------|
| **azure** | Telemetry | ✅ HIGH | 1 week | High | Ready |
| **observability** | Telemetry | ✅ HIGH | 1 week | High | Ready |
| **cloudflare-ai** | Model | ✅ HIGH | 2-3 weeks | High | Ready |
| **cloudflare** | Telemetry | ⚠️ MEDIUM-HIGH | 1-2 weeks | Medium | Consider |
| **vercel** | Combined | ⚠️ MEDIUM | 1 week | Low | If demanded |

> **Note:** The `observability` plugin provides presets for Sentry, Honeycomb, Datadog,
> Grafana, and Axiom. It complements platform plugins (aws, google-cloud, azure) for
> users who prefer third-party backends.

## Detailed Plans

### Ready for Implementation

1. **[azure-telemetry-plugin.md](./azure-telemetry-plugin.md)** - Azure Application Insights
   - Official Microsoft OTEL distro
   - One-liner setup with `configure_azure_monitor()`
   - Live metrics, application map, log correlation

2. **[observability-plugin.md](./observability-plugin.md)** - Third-Party Backends
   - Presets for Sentry, Honeycomb, Datadog, Grafana, Axiom
   - Platform-agnostic OTLP export
   - One function call setup

3. **[cloudflare-ai-plugin.md](./cloudflare-ai-plugin.md)** - Cloudflare Workers AI
   - 50+ models at the edge (Llama, Mistral, Flux, etc.)
   - Streaming, tool calling, embeddings
   - REST API with simple auth

### Consider Building

4. **[cloudflare-telemetry-plugin.md](./cloudflare-telemetry-plugin.md)** - Cloudflare Telemetry
   - No native backend, but exports to Sentry, Honeycomb, Datadog, etc.
   - AI Gateway auto-exports AI traces to third-party backends
   - Recommend: Plugin with presets for common backends

5. **[vercel-plugins.md](./vercel-plugins.md)** - Vercel AI & Telemetry
   - Python DOES work on Vercel (FastAPI, Flask)
   - AI SDK and @vercel/otel are JS-only, but AI Gateway + standard OTEL work
   - Recommend: Build simple helper plugin if user demand exists

## Feasibility Criteria

### ✅ HIGH Feasibility
- Official SDK/library available
- Clear API documentation
- Python support confirmed
- Similar patterns to existing plugins

### ⚠️ MEDIUM Feasibility
- REST API available but no SDK
- Limited Python-specific documentation
- Workarounds required
- May have feature gaps

### ❌ LOW Feasibility
- No Python support
- Platform-specific (JS/Node only)
- Would duplicate existing functionality
- Not worth maintenance overhead

## Implementation Priority

### Phase 1 (Immediate)
1. **azure** - Strong enterprise demand, official OTEL support
2. **observability** - Platform-agnostic, Sentry/Honeycomb/Datadog presets
3. **cloudflare-ai** - Growing edge AI market, good REST API

### Phase 2 (Consider)
4. **cloudflare** (telemetry) - AI Gateway integration, pairs with cloudflare-ai

### Phase 3 (If Demanded)
5. **vercel** - Simple helper plugin if users request it

## Architecture Patterns

All plugins should follow these patterns from existing implementations:

### Model Plugins (like `aws-bedrock`, `msfoundry`)
```
plugins/{name}/
├── src/genkit/plugins/{name}/
│   ├── __init__.py          # ELI5 docs, exports
│   ├── typing.py            # Config schemas per model
│   ├── models/
│   │   ├── model.py         # Base model implementation
│   │   └── {family}.py      # Model-specific configs
│   └── embedders/           # If applicable
└── tests/
```

### Telemetry Plugins (like `aws`, `google-cloud`)
```
plugins/{name}/
├── src/genkit/plugins/{name}/
│   ├── __init__.py          # ELI5 docs, exports
│   ├── telemetry/
│   │   ├── __init__.py
│   │   └── tracing.py       # Manager class
│   └── typing.py            # Config schemas
└── tests/
```

## Documentation Requirements

All plugins must include:

1. **ELI5 Concepts Table** - In module docstring
2. **Data Flow Diagram** - ASCII art showing architecture
3. **README.md** - Setup instructions, examples
4. **Sample Application** - In `samples/{name}-hello/`

See [GEMINI.md](../../GEMINI.md) for full documentation requirements.
