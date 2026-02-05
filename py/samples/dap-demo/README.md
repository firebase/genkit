# Dynamic Action Provider (DAP) Demo

This sample demonstrates how to use **Dynamic Action Providers (DAPs)** to
dynamically provide tools at runtime, enabling integration with external
systems like MCP servers, plugin registries, or other dynamic tool sources.

## What is a Dynamic Action Provider (DAP)?

A DAP is a factory that creates actions (tools, flows, etc.) at runtime rather
than at startup. This is useful for:

- **MCP Integration**: Connect to Model Context Protocol servers
- **Plugin Systems**: Load tools from external plugin registries
- **Multi-tenant Systems**: Provide tenant-specific tools dynamically
- **Feature Flags**: Enable/disable tools based on runtime configuration

## Key Concepts

| Concept | Description |
|---------|-------------|
| **DAP** | A "tool factory" that creates tools on-demand at runtime |
| **Dynamic Tool** | A tool created via `ai.dynamic_tool()` - not registered globally |
| **Cache** | DAP results are cached to avoid recreating tools on every request |
| **TTL** | Time-To-Live - how long cached tools remain valid before refresh |
| **Invalidation** | Manually clear the cache to force fresh tool creation |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DAP Flow                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Genkit     │     │     DAP      │     │   External   │                │
│  │   generate() │ ──► │    Cache     │ ──► │   System     │                │
│  └──────────────┘     └──────────────┘     │ (API, DB)    │                │
│         │                    │              └──────────────┘                │
│         ▼                    ▼                     │                        │
│  ┌──────────────┐     ┌──────────────┐             │                        │
│  │   Model      │ ◄── │   Dynamic    │ ◄───────────┘                        │
│  │   Response   │     │   Tools      │                                      │
│  └──────────────┘     └──────────────┘                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features Demonstrated

1. **Multiple DAPs**: Weather tools and Finance tools from separate providers
2. **Caching Strategies**: Different TTL values for different tool sources
3. **Cache Invalidation**: Manually refresh tools when needed
4. **Multi-source Composition**: Combine tools from multiple DAPs in one query

## Prerequisites

- Python 3.10+
- Google AI API key (`GEMINI_API_KEY`)

## Running the Sample

### Using the Sample Runner (Recommended)

```bash
# From the py/ directory
./bin/run_sample dap-demo
```

### Manual Execution

```bash
# Navigate to sample directory
cd py/samples/dap-demo

# Install dependencies
uv sync

# Run with Genkit DevUI
./run.sh

# Or run with genkit start directly
uv run genkit start -- python src/main.py
```

## Testing in the DevUI

1. **Start the sample** using `./run.sh` or the sample runner
2. **Open the DevUI** at http://localhost:4000
3. **Navigate to Flows** in the left sidebar
4. **Select a flow** (e.g., `weather_assistant`)
5. **Click Run** - default input values are pre-filled
6. **View the result** in the response panel

### Testing Each Flow

| Flow | Default Input | Expected Output |
|------|---------------|-----------------|
| `weather_assistant` | `{"city": "Tokyo"}` | Weather information for Tokyo |
| `finance_assistant` | `{"query": "What's the current price of AAPL stock?"}` | List of available finance tools |
| `multi_assistant` | `{"query": "..."}` | List of all tools from both DAPs |
| `refresh_tools_demo` | `{"source": "all"}` | Cache invalidation confirmation |
| `list_dap_tools` | `{"source": "all"}` | List of all available tool names |

## Available Flows

### weather_assistant

Get weather information for a city using the dynamically-provided weather tool.

**Input**: `WeatherInput` with `city` field (default: "Tokyo")

### finance_assistant

Answer finance questions using dynamically-provided finance tools.

**Input**: `FinanceInput` with `query` field (default: "What's the current price of AAPL stock?")

### multi_assistant

Multi-source assistant that combines tools from both Weather and Finance DAPs.

**Input**: `MultiInput` with `query` field

### refresh_tools_demo

Invalidate DAP cache to force fresh tool fetching.

**Input**: `RefreshInput` with `source` field ("weather", "finance", or "all")

### list_dap_tools

List all tools provided by a specific DAP or all DAPs.

**Input**: `ListToolsInput` with `source` field ("weather", "finance", or "all")

## DAP Configuration Examples

### Weather Tools DAP (Short Cache)

```python
weather_dap = ai.define_dynamic_action_provider(
    config=DapConfig(
        name='weather-tools',
        description='Provides weather-related tools',
        cache_config=DapCacheConfig(ttl_millis=5000),  # 5 second cache
    ),
    fn=weather_tools_provider,
)
```

### Finance Tools DAP (Long Cache)

```python
finance_dap = ai.define_dynamic_action_provider(
    config=DapConfig(
        name='finance-tools',
        description='Provides finance and market tools',
        cache_config=DapCacheConfig(ttl_millis=60000),  # 60 second cache
    ),
    fn=finance_tools_provider,
)
```

## Use Cases

1. **MCP Integration**: Use DAPs to connect to MCP servers and expose their
   tools to Genkit. See the `genkit-plugin-mcp` package for a complete
   implementation.

2. **Plugin Marketplace**: Load tools from an external registry based on
   user preferences or subscription level.

3. **Multi-tenant SaaS**: Provide different tools to different tenants based
   on their configuration or tier.

4. **A/B Testing**: Enable different tool sets for different users to test
   effectiveness.

## Related Resources

- [Genkit Python SDK Documentation](https://firebase.google.com/docs/genkit/python)
- [MCP Plugin](../../plugins/mcp/) - Full MCP integration using DAP
- [JS DAP Implementation](../../../../js/core/src/dynamic-action-provider.ts)
