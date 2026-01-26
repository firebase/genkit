# Model Spec Compliance Analysis

This document cross-checks Python model plugin implementations against the Genkit Model Action Specification ([model-spec.md](/docs/model-spec.md)).

---

## Executive Summary

| Area | Types Defined | Plugin Implementation | Gap Level |
|------|--------------|----------------------|-----------|
| Core Types | ✅ Complete | ⚠️ Partial use | Medium |
| Metadata | ✅ Complete | ⚠️ Missing fields | Medium |
| Docs Context | ✅ Type exists | ❌ Not implemented | High |
| Latency Tracking | ✅ Type exists | ❌ Not tracked | Medium |
| Partial Tool Streaming | ✅ Type exists | ❌ Not implemented | Low |

---

## 1. Type Compliance (Python Core Types)

### 1.1 GenerateRequest ✅

| Field | Spec | Python Type | Status |
|-------|------|-------------|--------|
| `messages` | Required | ✅ `list[Message]` | Complete |
| `config` | Any | ✅ `Any \| None` | Complete |
| `tools` | ToolDefinition[] | ✅ `list[ToolDefinition] \| None` | Complete |
| `toolChoice` | enum | ✅ `ToolChoice \| None` | Complete |
| `output` | OutputConfig | ✅ `OutputConfig \| None` | Complete |
| `docs` | DocumentData[] | ✅ `list[DocumentData] \| None` | Complete |

### 1.2 GenerateResponse ✅

| Field | Spec | Python Type | Status |
|-------|------|-------------|--------|
| `message` | Message | ✅ `Message \| None` | Complete |
| `finishReason` | enum | ✅ `FinishReason \| None` | Complete |
| `finishMessage` | string | ✅ `str \| None` | Complete |
| `usage` | GenerationUsage | ✅ `GenerationUsage \| None` | Complete |
| `latencyMs` | number | ✅ `float \| None` | Complete |
| `custom` | any | ✅ `Any \| None` | Complete |
| `request` | GenerateRequest | ✅ `GenerateRequest \| None` | Complete |

### 1.3 GenerateResponseChunk ✅

| Field | Spec | Python Type | Status |
|-------|------|-------------|--------|
| `role` | Role | ✅ `Role \| None` | Complete |
| `index` | number | ✅ `float \| None` | Complete |
| `content` | Part[] | ✅ `list[Part]` | Complete |
| `aggregated` | boolean | ✅ `bool \| None` | Complete |
| `custom` | any | ✅ `Any \| None` | Complete |

### 1.4 Part Types ✅

| Part Type | Spec | Python Type | Status |
|-----------|------|-------------|--------|
| TextPart | ✅ | ✅ `TextPart` | Complete |
| MediaPart | ✅ | ✅ `MediaPart` | Complete |
| ToolRequestPart | ✅ | ✅ `ToolRequestPart` | Complete |
| ToolResponsePart | ✅ | ✅ `ToolResponsePart` | Complete |
| CustomPart | ✅ | ✅ `CustomPart` | Complete |
| ReasoningPart | ✅ | ✅ `ReasoningPart` | Complete |
| DataPart | Reserved | ✅ `DataPart` | Complete |

### 1.5 ToolRequest (Partial Streaming) ✅

| Field | Spec | Python Type | Status |
|-------|------|-------------|--------|
| `partial` | boolean | ✅ `bool \| None` | Complete |

---

## 2. Model Action Metadata Gaps

> [!WARNING]
> Plugin implementations don't fully populate action metadata per spec.

### 2.1 Spec Requirements

```json
{
  "model": {
    "label": "Human-readable name",
    "versions": ["version1", "version2"],
    "supports": {
      "multiturn": true,
      "media": true,
      "tools": true,
      "systemRole": true,
      "output": ["json", "text"],
      "contentType": ["application/json"],
      "context": false,
      "constrained": "no-tools",
      "toolChoice": true,
      "longRunning": false
    },
    "stage": "stable",
    "customOptions": { /* JSON Schema */ }
  }
}
```

### 2.2 Gap Analysis

| Field | Google GenAI | Anthropic | Ollama |
|-------|-------------|-----------|--------|
| `label` | ✅ | ⚠️ Missing | ⚠️ Missing |
| `versions` | ⚠️ Some models | ✅ | ❌ |
| `multiturn` | ✅ | ✅ | ✅ |
| `media` | ✅ | ✅ | ✅ |
| `tools` | ✅ | ✅ | ✅ |
| `systemRole` | ✅ | ✅ | ✅ |
| `output` | ⚠️ Some | ❌ Missing | ❌ Missing |
| `contentType` | ❌ Missing | ❌ Missing | ❌ Missing |
| `context` | ❌ Missing | ❌ Missing | ❌ Missing |
| `constrained` | ✅ | ❌ Missing | ⚠️ Hardcoded |
| `toolChoice` | ✅ | ❌ Missing | ⚠️ Missing |
| `longRunning` | ❌ Missing | ❌ Missing | ❌ Missing |
| `stage` | ✅ | ❌ Missing | ❌ Missing |
| `customOptions` | ❌ Not exposed | ❌ | ❌ |

---

## 3. Plugin Implementation Gaps

### 3.1 Docs Context Handling ❌

> [!CAUTION]
> **Critical**: No Python plugin implements `docs` context augmentation.

**Spec Requirement:**
> If `docs` are provided, the model action should incorporate them into the context, typically by augmenting the message history.

**Current State:**
- Types: `GenerateRequest.docs` exists
- Google GenAI: Does not process `docs` field
- Anthropic: Does not process `docs` field
- Ollama: Does not process `docs` field

### 3.2 Latency Tracking ❌

**Spec Requirement:**
> `latencyMs`: Time taken for generation in milliseconds.

**Current State:**
- Types: `GenerateResponse.latency_ms` exists
- Google GenAI: Not populating latency_ms
- Anthropic: Not populating latency_ms
- Ollama: Not populating latency_ms

### 3.3 Request Echo ⚠️

**Spec Requirement:**
> `request`: The request that triggered this response.

**Current State:**
- Types: `GenerateResponse.request` exists
- Plugins: Not consistently populating this field

### 3.4 Partial Tool Streaming ❌

**Spec Requirement:**
> Some models support streaming tool calls with `partial: true`. The final chunk should have `partial: false`.

**Current State:**
- Types: `ToolRequest.partial` exists
- Google GenAI: Not implemented
- Anthropic: Not implemented
- Ollama: Not implemented

### 3.5 Server-Side Tools Configuration ⚠️

**Spec Requirement:**
> Features like Web Search, Code Execution, or URL Context are configured in `config`, not `tools`.

**Current State:**
- Google GenAI: ✅ Supports `url_context`, `file_search` in config
- Anthropic: ❌ Not implemented
- Ollama: ❌ Not applicable

### 3.6 Config Passthrough ⚠️

**Spec Requirement:**
> Pass all remaining unknown keys directly to the underlying model API.

**Current State:**
- Google GenAI: ✅ Inherits from SDK type, passes through
- Anthropic: ⚠️ Only extracts known keys, doesn't pass through
- Ollama: ✅ Passes through via `ollama_api.Options(**config)`

---

## 4. Behavior Compliance

### 4.1 System Message Handling ✅

| Plugin | Extracts System | Separate Field | Status |
|--------|----------------|----------------|--------|
| Google GenAI | ✅ | ✅ `systemInstruction` | Compliant |
| Anthropic | ✅ | ✅ `system` | Compliant |
| Ollama | ✅ | ⚠️ Varies by model | Mostly |

### 4.2 Tool Definition Conversion ✅

| Plugin | Name Sanitization | Schema Convert | Description |
|--------|-------------------|----------------|-------------|
| Google GenAI | ✅ | ✅ | ✅ |
| Anthropic | ✅ | ✅ | ✅ |
| Ollama | ✅ | ✅ | ✅ |

### 4.3 Finish Reason Mapping ✅

| Plugin | Maps Provider Reasons | Standard Enum |
|--------|----------------------|---------------|
| Google GenAI | ✅ | ✅ |
| Anthropic | ✅ | ✅ |
| Ollama | ⚠️ Limited | ✅ |

### 4.4 Structured Output ⚠️

| Plugin | Schema Passed | Constrained Support | Status |
|--------|--------------|---------------------|--------|
| Google GenAI | ✅ | ✅ `no-tools` | Good |
| Anthropic | ⚠️ | ❌ | Limited |
| Ollama | ⚠️ | ⚠️ | Limited |

---

## 5. Priority Recommendations

### P0 - Critical

1. **Implement `docs` context handling** - RAG use case is broken without it
2. **Add latency tracking** - Important for monitoring

### P1 - High

3. **Complete metadata fields** - `contentType`, `context`, `longRunning`
4. **Config passthrough** for Anthropic/Ollama - Future-proofing
5. **customOptions JSON Schema** - DevUI config display

### P2 - Medium

6. **Partial tool streaming** - Advanced feature
7. **Request echo** in response - Debugging support
8. **Stage field** for all plugins - Model lifecycle

### P3 - Low

9. **Versions array** for dynamic models
10. **Output contentType** support

---

## 6. Files Reference

### Spec
- [model-spec.md](/docs/model-spec.md)

### Python Types
- [typing.py](/py/packages/genkit/src/genkit/core/typing.py) - Core types

### Plugin Implementations
- [gemini.py](/py/plugins/google-genai/src/genkit/plugins/google_genai/models/gemini.py)
- [anthropic/models.py](/py/plugins/anthropic/src/genkit/plugins/anthropic/models.py)
- [ollama/models.py](/py/plugins/ollama/src/genkit/plugins/ollama/models.py)
