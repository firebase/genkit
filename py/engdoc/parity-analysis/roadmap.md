# Parity Analysis & Roadmap

> [!NOTE]
> This document tracks the feature parity of Genkit Python plugins against the
> Genkit Node.js reference implementation. Use this to identify gaps and plan work.

---

## Current Status (Updated 2026-02-06)

> [!IMPORTANT]
> **Overall Parity: ~99% Complete** - Nearly all milestones done!
>
> Legacy formatting and type checking issues fixed throughout the repo.
> Remaining work is focused on resolving specific model quirks (e.g. DeepSeek R1 reasoning).

| Plugin | API Conformance | Missing Features | Security Issues | Test Coverage | Priority |
|--------|-----------------|------------------|-----------------|---------------|----------|
| google-genai | ✅ Verified | Minor | None | Good | - |
| anthropic | ✅ Mostly Conformant (PR #4482) | Citations | None | ✅ Good | Low |
| amazon-bedrock | ✅ Verified | Guardrails | None | Good | Low |
| ollama | ✅ Verified | Vision via chat API | None | Fair | Low |
| mistral | ✅ Mostly Conformant (PR #4481) | Agents API, Codestral FIM | None | ✅ Good | Low |
| xai | ⚠️ Gaps | Agent Tools API (server/client-side) | None | Fair | Medium |
| deepseek | ✅ Mostly Conformant (PR #4480) | Multi-round reasoning | None | ✅ Good | Low |
| cloudflare-workers-ai | ✅ Verified | Async Batch API | None | Good | Low |
| huggingface | ⚠️ Gaps | Inference Endpoints, TGI | None | Fair | Medium |
| azure | ⚠️ Gaps | Azure AI Studio | None | Fair | Medium |

### Priority Actions

| Priority | Task | Plugin | Effort | Description |
|----------|------|--------|--------|-------------|
| ~~P0~~ | ~~Fix `reasoning_content` extraction~~ | ~~deepseek~~ | ~~M~~ | ✅ Done (PR #4480) - Extracted via `MessageAdapter` in compat-oai, emits `ReasoningPart` |
| ~~P0~~ | ~~Add parameter validation warnings~~ | ~~deepseek~~ | ~~S~~ | ✅ Done (PR #4480) - `_warn_reasoning_params()` logs warnings for ignored params |
| ~~P1~~ | ~~Add cache control support~~ | ~~anthropic~~ | ~~M~~ | ✅ Done (PR #4482) - `cache_control` with TTL for cost savings |
| ~~P1~~ | ~~Add PDF/Document support~~ | ~~anthropic~~ | ~~M~~ | ✅ Done (PR #4482) - `DocumentBlockParam` for common use case |
| ~~P1~~ | ~~Add embeddings support~~ | ~~mistral~~ | ~~S~~ | ✅ Done (PR #4481) - `mistral-embed` model |
| **P2** | Add Agent Tools API | xai | M | Server/client-side tool calling (Jan 2026) |
| **P2** | Add Agents API | mistral | L | Mistral Agents endpoint |
| **P2** | Add Inference Endpoints | huggingface | M | Dedicated endpoints for production |
| **P3** | Add Guardrails | amazon-bedrock | M | Bedrock Guardrails integration |
| **P3** | Add Azure AI Studio | azure | L | New unified API |

### Detailed Gap Analysis

#### 1. google-genai (Gemini/Vertex AI)

**Status**: ✅ Mostly Conformant

**Verified Features**:
- Text generation (streaming/non-streaming) ✓
- Embeddings ✓
- Image generation (Imagen) ✓
- Video generation (Veo) ✓
- Function/tool calling ✓
- Context caching ✓
- Safety settings ✓
- Evaluators (Vertex AI) ✓
- Rerankers (Vertex AI Discovery Engine) ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Grounding with Google Search | Not implemented for Gemini API | Medium - useful for RAG | Medium |
| Code execution tool | Built-in code execution not exposed | Low | Low |
| Audio generation (Lyria) | Partial - helpers only, no full model | Low | Low |

---

#### 2. anthropic (Claude)

**Status**: ✅ Mostly Conformant (PR #4482)

**Verified Features**:
- Messages API ✓
- Tool/function calling ✓
- Streaming ✓
- Vision (images) ✓
- Thinking mode (extended thinking) ✓
- ✅ Cache control (ephemeral) ✓ (PR #4482)
- ✅ PDF/Document support (`DocumentBlockParam`) ✓ (PR #4482)
- ✅ URL image source ✓ (PR #4482)

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| ~~Cache control (ephemeral)~~ | ~~`cache_control` with TTL not supported~~ | ~~High~~ | ✅ Done (PR #4482) |
| ~~PDF/Document support~~ | ~~`DocumentBlockParam` not implemented~~ | ~~High~~ | ✅ Done (PR #4482) |
| Citations | Citation extraction not supported | Medium | P2 |
| Web search tool | Server-side `web_search` tool not supported | Medium | P2 |
| Batch API | Message batches not supported | Low - async processing | P3 |

---

#### 3. amazon-bedrock

**Status**: ✅ Mostly Conformant

**Verified Features**:
- Converse API ✓
- ConverseStream API ✓
- Tool calling ✓
- Multi-provider support (Claude, Nova, Llama, etc.) ✓
- Inference profiles for cross-region ✓
- Embeddings ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Guardrails | Bedrock Guardrails not integrated | Medium - content filtering | P3 |
| Knowledge bases | RAG via Bedrock KB not supported | Medium | P3 |
| Model invocation logging | CloudWatch logging config | Low | P4 |

---

#### 4. ollama

**Status**: ✅ Conformant

**Verified Features**:
- Chat API (/api/chat) ✓
- Generate API (/api/generate) ✓
- Embeddings API (/api/embeddings) ✓
- Tool calling ✓
- Streaming ✓
- Model discovery ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Vision in chat | Images via chat API need testing | Low - works via generate | P4 |
| Pull models | Model download/management | Low - user manages | P4 |

---

#### 5. mistral

**Status**: ✅ Mostly Conformant (PR #4481)

**Verified Features**:
- Chat completions ✓
- Streaming ✓
- Tool/function calling ✓
- JSON mode ✓
- Vision models (Pixtral) ✓
- ✅ Embeddings (`mistral-embed`) ✓ (PR #4481)

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| ~~Embeddings~~ | ~~`mistral-embed` model not supported~~ | ~~Medium~~ | ✅ Done (PR #4481) |
| Agents API | Mistral Agents endpoint not supported | High - agentic workflows | P2 |
| FIM (Fill-in-Middle) | Codestral FIM for code completion | Medium - code use cases | P2 |
| Built-in tools | websearch, code_interpreter, image_generation | Medium | P3 |

---

#### 6. xai (Grok)

**Status**: ⚠️ Has Gaps

**Verified Features**:
- Chat completions ✓
- Streaming ✓
- Tool/function calling ✓
- Vision (grok-2-vision) ✓
- Reasoning effort parameter ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Agent Tools API | Server-side and client-side tool calling (Jan 2026) | High - new feature | P2 |
| Web search options | Built-in web search configuration | Medium | P3 |
| New models | grok-4-1-fast-reasoning, grok-4-1-fast-non-reasoning | Medium | P2 |

---

#### 7. deepseek

**Status**: ✅ Mostly Conformant (PR #4480)

**Verified Features**:
- Chat completions (OpenAI-compatible) ✓
- Streaming ✓
- Uses compat-oai for implementation ✓
- `reasoning_content` extraction for R1/reasoner models ✓ (PR #4480)
- Parameter validation warnings for R1 (temp, top_p, tools) ✓ (PR #4480)
- Chat vs. reasoning model capability split ✓ (PR #4480)
- `is_reasoning_model()` helper ✓ (PR #4480)

**Implementation Details (PR #4480)**:
- **compat-oai layer**: `MessageAdapter` wraps raw Pydantic `ChatCompletionMessage` for safe `reasoning_content` access (Pydantic raises `AttributeError` for unknown fields). `MessageConverter.to_genkit()` emits `ReasoningPart` before `TextPart` (matching JS order).
- **Streaming**: `MessageAdapter(delta).reasoning_content` in `_generate_stream()` replaces unsafe `getattr()` pattern.
- **deepseek plugin**: `_warn_reasoning_params()` logs warnings when `temperature`, `top_p`, or `tools` are passed to R1 models. Model capabilities split into chat (`tools=True`) vs. reasoning (`tools=False`).

**Remaining Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| ~~`reasoning_content`~~ | ~~CoT output not extracted/exposed~~ | ~~**Critical**~~ | ✅ Done (PR #4480) |
| ~~Parameter validation~~ | ~~R1 ignores temp/top_p but no warning~~ | ~~High~~ | ✅ Done (PR #4480) |
| ~~Multi-round reasoning~~ | ~~Must strip reasoning_content from context~~ | ~~High~~ | ✅ Done — `ReasoningPart` skipped in `MessageConverter.to_openai()` |
| Tool calling in R1 | Not supported in reasoner mode | Medium - documented limitation | P2 |

---

#### 8. cloudflare-workers-ai (Cloudflare Workers AI)

**Status**: ✅ Mostly Conformant

**Verified Features**:
- Text generation ✓
- Streaming (SSE) ✓
- Tool calling (via CF specific implementation) ✓
- Embeddings ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Async Batch API | Not implemented | Low | Low |
| Function calling standardization | Uses custom impl instead of OpenAI compat | Medium | Low |

---

#### 9. huggingface

**Status**: ⚠️ Has Gaps

**Verified Features**:
- Text generation (inference API) ✓
- Streaming ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Inference Endpoints | Dedicated endpoints not supported | Medium - production use | P2 |
| TGI Integration | Text Generation Inference specific features | Medium | P3 |
| Chat templating | Better reliance on tokenizer chat templates | Low | P3 |

---

#### 10. azure (Azure OpenAI)

**Status**: ⚠️ Has Gaps

**Verified Features**:
- Chat completions ✓
- Streaming ✓
- Tool calling ✓

**Gaps**:
| Gap | Description | Impact | Priority |
|-----|-------------|--------|----------|
| Azure AI Studio | New unified API not supported | Medium | P3 |
| Entra ID Auth | Managed identity support | Medium - enterprise | P2 |
| On Your Data | Azure Search integration | Medium | P3 |
