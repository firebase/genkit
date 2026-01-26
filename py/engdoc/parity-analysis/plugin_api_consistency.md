# Plugin API Consistency Report

This document analyzes model provider API consistency across JS and Python Genkit plugins, comparing initialization parameters, config schemas, and feature support.

---

## Executive Summary

| Plugin | JS Config Schema | Python Config Schema | Gap Level |
|--------|-----------------|---------------------|-----------|
| Google GenAI | Full Zod Schema (25+ fields) | Pydantic (inherits from SDK) | **Medium** |
| Anthropic | AnthropicConfigSchema (10+ fields) | GenerationCommonConfig only | **Critical** |
| Ollama | OllamaConfigSchema (6 fields) | GenerationCommonConfig | **Medium** |

---

## 1. Google GenAI / Vertex AI Plugin

### 1.1 Plugin Initialization Options

| Parameter | JS | Python | Notes |
|-----------|-----|--------|-------|
| `apiKey` | ✅ | ✅ | Both support |
| `apiVersion` | ✅ | ❌ | Python missing |
| `baseUrl` | ✅ | ❌ | Python missing |
| `customHeaders` | ✅ | ❌ (internal only) | Python injects headers internally |
| `legacyResponseSchema` | ✅ | ❌ | Python missing |
| `experimental_debugTraces` | ✅ | ❌ | Python missing |
| `credentials` | ✅ | ✅ | Both support |
| `project` | ✅ | ✅ | VertexAI only |
| `location` | ✅ | ✅ | VertexAI only |
| `debug_config` | ❌ | ✅ | Python has SDK debug |
| `http_options` | ❌ | ✅ | Python SDK-specific |

### 1.2 GeminiConfigSchema Comparison

**JS (Zod Schema):**
```typescript
GeminiConfigSchema = GenerationCommonConfigSchema.extend({
  apiKey: z.string().optional(),           // Override plugin apiKey
  baseUrl: z.string().optional(),          // Override baseUrl
  apiVersion: z.string().optional(),       // Override apiVersion
  safetySettings: z.array(...),            // Safety filters
  codeExecution: z.boolean().optional(),   // Enable code execution
  contextCache: z.boolean().optional(),    // Enable context caching
  functionCallingConfig: z.object({...}),  // Tool control
  responseModalities: z.array(...),        // TEXT/IMAGE/AUDIO
  googleSearchRetrieval: z.boolean(),      // Grounding with Google Search
  fileSearch: z.object({...}),             // File search stores
  urlContext: z.boolean(),                 // URL context grounding
  temperature: z.number().min(0).max(2),   // With descriptions
  topP: z.number().min(0).max(1),
  thinkingConfig: z.object({
    includeThoughts: z.boolean(),
    thinkingBudget: z.number().min(0).max(24576),
    thinkingLevel: z.enum(['MINIMAL', 'LOW', 'MEDIUM', 'HIGH']),
  }),
});
```

**Python (Pydantic Model):**
```python
class GeminiConfigSchema(genai_types.GenerateContentConfig):
    code_execution: bool | None = None
    response_modalities: list[str] | None = None
    thinking_config: dict[str, Any] | None = None
    file_search: dict[str, Any] | None = None
    url_context: dict[str, Any] | None = None
    api_version: str | None = None
```

### 1.3 Config Schema Gaps

| Field | JS | Python | Priority |
|-------|-----|--------|----------|
| `safetySettings` | ✅ Typed array | Inherits from SDK | P1 |
| `contextCache` | ✅ boolean | ❌ Missing | P1 |
| `functionCallingConfig` | ✅ Typed object | Inherits from SDK | P2 |
| `googleSearchRetrieval` | ✅ boolean/object | Inherits from SDK | P2 |
| Per-field descriptions | ✅ All fields | ❌ None | P2 |
| Type validation bounds | ✅ min/max | ❌ None | P2 |

### 1.4 API Surface Gap

> [!WARNING]
> Python plugin does not expose `googleAI.model()` or `vertexAI.model()` convenience methods for creating model references with typed configs.

**JS Pattern:**
```typescript
const model = googleAI.model('gemini-2.5-flash', { 
  temperature: 0.8,
  thinkingConfig: { includeThoughts: true }
});
```

**Python Pattern:**
```python
# No equivalent - must use string reference
response = await ai.generate(
    model='googleai/gemini-2.5-flash',
    config={'temperature': 0.8}  # Untyped dict
)
```

---

## 2. Anthropic Plugin

### 2.1 Plugin Initialization Options

| Parameter | JS | Python | Notes |
|-----------|-----|--------|-------|
| `apiKey` | ✅ | ✅ | Both support |
| `apiVersion` | ✅ ('stable'/'beta') | ❌ | Python missing |
| `models` | ❌ | ✅ | Python-specific |
| `**anthropic_params` | ❌ | ✅ | Python passes to SDK |

### 2.2 Config Schema Comparison

> [!CAUTION]
> **Critical Gap**: Python Anthropic uses only `GenerationCommonConfig`, missing all Claude-specific features.

**JS AnthropicConfigSchema:**
```typescript
AnthropicConfigSchema = GenerationCommonConfigSchema.extend({
  tool_choice: z.union([
    z.object({ type: z.literal('auto') }),
    z.object({ type: z.literal('any') }),
    z.object({ type: z.literal('tool'), name: z.string() }),
  ]),
  metadata: z.object({ user_id: z.string() }).optional(),
  apiVersion: z.enum(['stable', 'beta']).optional(),
  thinking: z.object({
    enabled: z.boolean().optional(),
    budgetTokens: z.number().min(1024).optional(),
  }).optional(),
});
```

**Python (Uses GenerationCommonConfig only):**
```python
# No Claude-specific config!
# Just: temperature, max_output_tokens, top_p, stop_sequences, top_k
```

### 2.3 Missing Python Features

| Feature | Description | Impact |
|---------|-------------|--------|
| **Thinking Config** | Extended thinking with budget tokens | Users cannot enable Claude thinking |
| **API Version** | Switch between stable/beta APIs | No access to beta features |
| **Tool Choice** | Force specific tool use | Less control over tool calling |
| **Metadata** | User ID tracking | No usage tracking |
| **Citations** | Document citation support | `anthropicDocument()` missing |
| **Cache Control** | `cacheControl()` helper | No prompt caching |

### 2.4 Model Mapping Gap

**JS:**
```typescript
KNOWN_CLAUDE_MODELS = {
  'claude-3-haiku': AnthropicBaseConfigSchema,
  'claude-3-5-haiku': AnthropicBaseConfigSchema,
  'claude-sonnet-4': AnthropicThinkingConfigSchema,  // Separate schema!
  'claude-opus-4': AnthropicThinkingConfigSchema,
  'claude-sonnet-4-5': AnthropicThinkingConfigSchema,
  // ...  
};
```

**Python:**
```python
# All models use same GenerationCommonConfig
# No model-specific config schemas
```

---

## 3. Ollama Plugin

### 3.1 Plugin Initialization Options

| Parameter | JS | Python | Notes |
|-----------|-----|--------|-------|
| `serverAddress` | ✅ | ✅ | Both support |
| `requestHeaders` | ✅ | ✅ | Both support |
| `models` | ✅ | ✅ | Pre-register models |
| `embedders` | ✅ | ✅ | Pre-register embedders |

### 3.2 Config Schema Comparison

**JS OllamaConfigSchema:**
```typescript
OllamaConfigSchema = GenerationCommonConfigSchema.extend({
  temperature: z.number().min(0.0).max(1.0)
    .describe('...defaults value is 0.8'),
  topP: z.number().min(0).max(1.0)
    .describe('...defaults value is 0.9'),
});
```

**Python (Uses GenerationCommonConfig):**
```python
# Untyped config - relies on Ollama SDK defaults
```

### 3.3 Gaps

| Gap | Impact |
|-----|--------|
| No per-field descriptions | Less IDE help |
| No type validation | Invalid values sent to Ollama |

---

## 4. Common API Pattern Gaps

### 4.1 Model Reference Factory

**JS Pattern (All Plugins):**
```typescript
// Type-safe model reference with IDE autocomplete
const model = googleAI.model('gemini-2.5-flash');
const model = anthropic.model('claude-sonnet-4');
const model = ollama.model('llama3');
```

**Python Pattern:**
```python
# Only string-based references - no type safety
model='googleai/gemini-2.5-flash'
model='anthropic/claude-sonnet-4'
model='ollama/llama3'
```

### 4.2 Embedder Reference Factory

**JS Pattern:**
```typescript
const embedder = googleAI.embedder('text-embedding-004');
```

**Python:** ❌ No equivalent

### 4.3 Config Schema in DevUI

| Plugin | JS DevUI | Python DevUI |
|--------|----------|--------------|
| Google GenAI | ✅ Full config | ❌ Empty (commented out) |
| Anthropic | ✅ Full config | ⚠️ Basic only |
| Ollama | ✅ Full config | ⚠️ Basic only |

---

## 5. Priority Recommendations

### P0 - Critical

1. **Add Python `config_schema` to model metadata** - Fix the commented out code
2. **Anthropic ThinkingConfig** - Required for Claude 4.x models

### P1 - High

3. **Anthropic-specific config schema** - tool_choice, metadata, apiVersion
4. **Google GenAI plugin options** - apiVersion, baseUrl, customHeaders
5. **Model reference factories** - `plugin.model()` pattern for Python

### P2 - Medium

6. **Config field descriptions** - Match JS documentation
7. **Type validation** - min/max bounds on numeric fields
8. **Ollama config schema** - Match JS validation

### P3 - Low

9. **Embedder reference factories** - `plugin.embedder()` pattern
10. **Debug trace options** - Match JS tracing options

---

## 6. Files Reference

### JS Plugins
- [googleai/types.ts](/js/plugins/google-genai/src/googleai/types.ts) - Plugin options
- [googleai/gemini.ts](/js/plugins/google-genai/src/googleai/gemini.ts) - Config schema
- [anthropic/types.ts](/js/plugins/anthropic/src/types.ts) - Anthropic config
- [anthropic/models.ts](/js/plugins/anthropic/src/models.ts) - Model definitions
- [ollama/index.ts](/js/plugins/ollama/src/index.ts) - Ollama config

### Python Plugins
- [google_genai/google.py](/py/plugins/google-genai/src/genkit/plugins/google_genai/google.py)
- [google_genai/models/gemini.py](/py/plugins/google-genai/src/genkit/plugins/google_genai/models/gemini.py)
- [anthropic/plugin.py](/py/plugins/anthropic/src/genkit/plugins/anthropic/plugin.py)
- [anthropic/models.py](/py/plugins/anthropic/src/genkit/plugins/anthropic/models.py)
- [ollama/plugin_api.py](/py/plugins/ollama/src/genkit/plugins/ollama/plugin_api.py)
