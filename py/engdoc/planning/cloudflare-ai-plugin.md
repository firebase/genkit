# Cloudflare Workers AI Plugin Implementation Plan

**Status:** Ready for Implementation  
**Feasibility:** ✅ HIGH  
**Estimated Effort:** Medium (2-3 weeks)  
**Dependencies:** `httpx`, `pydantic`

## Overview

The `cloudflare-ai` plugin provides access to Cloudflare Workers AI, enabling Genkit
applications to use 50+ open-source AI models running at the edge across 200+ data centers.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 CLOUDFLARE WORKERS AI PLUGIN ARCHITECTURE               │
│                                                                         │
│    Key Concepts (ELI5):                                                 │
│    ┌─────────────────────┬────────────────────────────────────────────┐ │
│    │ Workers AI          │ Cloudflare's AI at the edge. Models run    │ │
│    │                     │ close to users (200+ data centers).        │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Account ID          │ Your Cloudflare account identifier.        │ │
│    │                     │ Found in dashboard URL or API settings.    │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ API Token           │ Auth token with Workers AI permissions.    │ │
│    │                     │ Create at dash.cloudflare.com/profile/api  │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ @cf/ Models         │ Model names start with @cf/ prefix.        │ │
│    │                     │ @cf/meta/llama-3.1-8b-instruct             │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Edge Computing      │ Processing close to users. Lower latency   │ │
│    │                     │ than centralized cloud data centers.       │ │
│    └─────────────────────┴────────────────────────────────────────────┘ │
│                                                                         │
│    Data Flow:                                                           │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│    │  Genkit App     │────▶│  CF Workers AI  │────▶│  Edge Location  │  │
│    │  (Your Code)    │     │  REST API       │     │  (Nearest DC)   │  │
│    └─────────────────┘     └─────────────────┘     └─────────────────┘  │
│           │                                               │             │
│           │         ┌─────────────────────────────────────┘             │
│           │         │                                                   │
│           │         ▼                                                   │
│           │    ┌─────────────────┐                                      │
│           │    │  AI Models      │                                      │
│           │    │  • Llama 3/4    │                                      │
│           │    │  • Mistral      │                                      │
│           │    │  • Flux (Image) │                                      │
│           │    │  • Whisper      │                                      │
│           │    └─────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## API Details

### Authentication

```python
# Environment variables
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token
```

### Base URL Pattern

```
https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}
```

### Request Format

```python
# Text Generation
{
    "messages": [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello!"}
    ],
    "stream": true,  # Optional: Enable SSE streaming
    "max_tokens": 256,
    "temperature": 0.6
}

# Image Generation
{
    "prompt": "A sunset over mountains",
    "num_steps": 20,
    "guidance": 7.5
}

# Embeddings
{
    "text": ["Hello world", "Goodbye world"]
}
```

### Response Format

```python
# Non-streaming
{
    "result": {
        "response": "Hello! How can I help you today?"
    },
    "success": true,
    "errors": [],
    "messages": []
}

# Streaming (SSE)
data: {"response": "Hello"}
data: {"response": "!"}
data: {"response": " How"}
data: [DONE]
```

## Model Support Matrix

| Model | Type | Streaming | Tools | Status |
|-------|------|-----------|-------|--------|
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Text | ✅ | ✅ | Priority |
| `@cf/meta/llama-3.1-8b-instruct-fast` | Text | ✅ | ✅ | Priority |
| `@cf/meta/llama-4-scout-17b-16e-instruct` | Multimodal | ✅ | ✅ | Priority |
| `@cf/mistral/mistral-7b-instruct-v0.2` | Text | ✅ | ❌ | Phase 1 |
| `@cf/qwen/qwen1.5-14b-chat-awq` | Text | ✅ | ❌ | Phase 2 |
| `@cf/black-forest-labs/flux-2-klein-9b` | Image | ❌ | ❌ | Phase 2 |
| `@cf/stabilityai/stable-diffusion-xl-base-1.0` | Image | ❌ | ❌ | Phase 2 |
| `@cf/openai/whisper` | Speech→Text | ❌ | ❌ | Phase 3 |
| `@cf/baai/bge-base-en-v1.5` | Embedding | ❌ | ❌ | Phase 1 |
| `@cf/baai/bge-large-en-v1.5` | Embedding | ❌ | ❌ | Phase 1 |

## Model Configuration Parameters

### Text Generation (Llama/Mistral)

```python
class CloudflareLlamaConfig(BaseModel):
    """Configuration for Llama models on Workers AI."""
    
    # Core parameters
    temperature: float | None = Field(default=0.6, ge=0.0, le=5.0)
    max_tokens: int | None = Field(default=256, ge=1, le=4096)
    top_p: float | None = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int | None = Field(default=40, ge=1, le=100)
    
    # Repetition control
    repetition_penalty: float | None = Field(default=1.0, ge=0.0, le=2.0)
    presence_penalty: float | None = None  # Llama 3.1+
    frequency_penalty: float | None = None  # Llama 3.1+
    
    # Output control
    seed: int | None = None  # For reproducibility
    raw: bool | None = None  # Return raw tokens
```

### Image Generation (Flux/Stable Diffusion)

```python
class CloudflareImageConfig(BaseModel):
    """Configuration for image generation models."""
    
    num_steps: int | None = Field(default=20, ge=1, le=50)
    guidance: float | None = Field(default=7.5, ge=0.0, le=20.0)
    strength: float | None = Field(default=1.0, ge=0.0, le=1.0)  # For img2img
    width: int | None = Field(default=1024)
    height: int | None = Field(default=1024)
    seed: int | None = None
```

## Directory Structure

```
py/plugins/cloudflare-ai/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/genkit/plugins/cloudflare_ai/
│   ├── __init__.py              # Plugin entry, ELI5 docs, exports
│   ├── typing.py                # All Pydantic config schemas
│   ├── constants.py             # Model names, URLs, defaults
│   ├── models/
│   │   ├── __init__.py
│   │   ├── model.py             # CloudflareModel base implementation
│   │   ├── text.py              # Text generation (Llama, Mistral, Qwen)
│   │   ├── image.py             # Image generation (Flux, SD)
│   │   ├── speech.py            # Speech-to-text (Whisper)
│   │   └── utils.py             # Response parsing, error handling
│   ├── embedders/
│   │   ├── __init__.py
│   │   └── embedder.py          # BGE embeddings implementation
│   └── py.typed
└── tests/
    ├── conftest.py
    ├── cloudflare_model_test.py
    ├── cloudflare_embedder_test.py
    └── integration_test.py
```

## Implementation Phases

### Phase 1: Core Plugin (Week 1)

1. **Plugin skeleton**
   - `CloudflareAI` plugin class
   - Authentication handling (API token, Account ID)
   - HTTP client setup with `httpx`

2. **Text generation models**
   - Llama 3.1/3.3 support
   - Streaming via SSE
   - Tool/function calling

3. **Embeddings**
   - BGE embedder implementation
   - Batch embedding support

### Phase 2: Extended Models (Week 2)

1. **Image generation**
   - Flux models
   - Stable Diffusion XL
   - Base64 image handling

2. **Additional text models**
   - Mistral family
   - Qwen models

3. **Model configuration**
   - Full parameter support per model family
   - DevUI integration

### Phase 3: Advanced Features (Week 3)

1. **Speech models**
   - Whisper integration
   - Audio input handling

2. **Multimodal**
   - Llama 4 Scout vision support
   - Image + text inputs

3. **Sample application**
   - `cloudflare-ai-hello` sample
   - README with setup instructions

## Key Implementation Details

### Plugin Class

```python
class CloudflareAI(Plugin):
    """Cloudflare Workers AI plugin for Genkit.
    
    Provides access to 50+ AI models running at the edge.
    
    Example:
        >>> from genkit.ai import Genkit
        >>> from genkit.plugins.cloudflare_ai import CloudflareAI, cloudflare_model
        >>> 
        >>> ai = Genkit(
        ...     plugins=[CloudflareAI()],
        ...     model=cloudflare_model("@cf/meta/llama-3.1-8b-instruct-fast"),
        ... )
    """
    
    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        models: list[str] | None = None,  # Subset of models to register
    ):
        self.account_id = account_id or os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        self.api_token = api_token or os.environ.get('CLOUDFLARE_API_TOKEN')
        
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID required")
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN required")
```

### Streaming Implementation

```python
async def _generate_stream(
    self, 
    model: str,
    messages: list[dict],
    config: CloudflareLlamaConfig,
) -> AsyncIterator[GenerateResponseChunk]:
    """Generate streaming response using SSE."""
    
    url = f"{BASE_URL.format(account_id=self.account_id)}/{model}"
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json={
                "messages": messages,
                "stream": True,
                **config.model_dump(exclude_none=True),
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    yield GenerateResponseChunk(
                        content=[TextPart(text=chunk.get("response", ""))],
                    )
```

## Testing Strategy

1. **Unit tests** - Mock HTTP responses, test config validation
2. **Integration tests** - Live API calls (requires credentials)
3. **Model-specific tests** - Verify each model family works correctly

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Your Cloudflare account ID |
| `CLOUDFLARE_API_TOKEN` | Yes | API token with Workers AI permissions |

## Sample Application

```python
# py/samples/cloudflare-ai-hello/src/main.py
"""Cloudflare Workers AI hello sample - Edge AI with Genkit."""

from genkit.ai import Genkit
from genkit.plugins.cloudflare_ai import CloudflareAI, cloudflare_model

ai = Genkit(
    plugins=[CloudflareAI()],
    model=cloudflare_model("@cf/meta/llama-3.1-8b-instruct-fast"),
)

@ai.flow()
async def say_hi(name: str) -> str:
    """Say hello using Llama at the edge."""
    response = await ai.generate(prompt=f"Say hi to {name} in a friendly way!")
    return response.text

@ai.flow()
async def generate_image(prompt: str) -> str:
    """Generate an image using Flux."""
    response = await ai.generate(
        model=cloudflare_model("@cf/black-forest-labs/flux-2-klein-9b"),
        prompt=prompt,
    )
    return response.media[0].url  # Base64 data URL
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Rate limiting | Medium | Implement exponential backoff |
| Model availability | Low | Graceful fallback to alternative models |
| SSE parsing edge cases | Medium | Comprehensive error handling |
| Tool calling variations | Medium | Test with multiple model families |

## References

- [Workers AI Documentation](https://developers.cloudflare.com/workers-ai/)
- [Workers AI Models Catalog](https://developers.cloudflare.com/workers-ai/models/)
- [REST API Guide](https://developers.cloudflare.com/workers-ai/get-started/rest-api)
- [Cloudflare API Reference](https://developers.cloudflare.com/api/resources/ai/)
