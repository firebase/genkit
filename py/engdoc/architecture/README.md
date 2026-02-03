# Genkit Python SDK Architecture Guide

Welcome to the Genkit Python SDK! This guide will help you understand how the
framework is architected and how all the pieces fit together. Whether you're
fixing bugs, adding features, or just trying to understand the codebase, this
document is your starting point.

## Quick Overview (ELI5)

Think of Genkit as a universal remote control for AI:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         YOUR APP (The TV Viewer)                            │
│                                                                             │
│   "I want to generate text, use tools, retrieve documents..."               │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GENKIT (The Universal Remote)                           │
│                                                                             │
│   Provides ONE consistent way to talk to MANY different AI services         │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
     ┌──────────┐            ┌──────────┐            ┌──────────┐
     │  Gemini  │            │  Claude  │            │  Ollama  │
     │ (Google) │            │(Anthropic│            │ (Local)  │
     └──────────┘            └──────────┘            └──────────┘
```

Just like a universal remote works with any TV brand, Genkit works with any
AI provider. You write your code once, and Genkit handles the differences.

## Key Concepts (ELI5)

```
┌─────────────────────┬────────────────────────────────────────────────────────┐
│ Concept             │ ELI5 Explanation                                       │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Action              │ A "button" on your remote that does ONE thing.         │
│                     │ Press it, something happens. Every feature is an       │
│                     │ action: generate text, embed docs, call tools.         │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Flow                │ YOUR custom action. It's an action YOU define          │
│                     │ to do YOUR specific task.                              │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Registry            │ A "phone book" of all available actions.               │
│                     │ Need a model? Look it up. Need a tool? Look it up.     │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Plugin              │ An "app" you install to add new capabilities.          │
│                     │ Want Gemini? Install the google-genai plugin.          │
│                     │ Want Claude? Install the anthropic plugin.             │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Genkit (class)      │ The "Genkit app" instance. Your main entry point.      │
│                     │ Create one, add plugins, and you're ready to go.       │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Model               │ An AI brain that generates text/images/etc.            │
│                     │ Gemini, Claude, GPT are all models.                    │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Tool                │ A function the AI can call to do things.               │
│                     │ Like "get_weather()" or "search_database()".           │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Embedder            │ Converts text into numbers (vectors) that capture      │
│                     │ meaning. "cat" and "kitten" have similar vectors.      │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Retriever           │ Finds relevant documents from a collection.            │
│                     │ Like a librarian who finds books matching your query.  │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Reranker            │ Re-orders search results by relevance.                 │
│                     │ Like getting a second opinion on which books are best. │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ Middleware          │ Code that runs before/after your request.              │
│                     │ Like a secretary who handles retries and fallbacks.    │
└─────────────────────┴────────────────────────────────────────────────────────┘
```

## The Layered Architecture

Genkit uses an "onion" architecture with distinct layers. Each layer only
talks to the layer directly below it.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 1: USER APPLICATION                                                 │
│   ─────────────────────────                                                 │
│   Your code that uses Genkit                                                │
│                                                                             │
│   from genkit import Genkit                                                 │
│   ai = Genkit(plugins=[...])                                                │
│   response = await ai.generate(prompt="Hello!")                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 2: AI VENEER (genkit/ai/)                                           │
│   ───────────────────────────────                                           │
│   The user-friendly API layer. This is what you import and use.             │
│                                                                             │
│   • Genkit class - Main entry point                                         │
│   • generate(), generate_stream() - Text generation                         │
│   • embed(), retrieve(), rerank() - RAG operations                          │
│   • tool(), flow() - Decorators for defining actions                        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 3: AI BLOCKS (genkit/blocks/)                                       │
│   ────────────────────────────────────                                      │
│   Building blocks for AI capabilities. Higher-level abstractions.           │
│                                                                             │
│   • model.py - Model abstraction and utilities                              │
│   • embedding.py - Embedding operations                                     │
│   • retriever.py - Document retrieval                                       │
│   • reranker.py - Document reranking                                        │
│   • tools.py - Tool definitions and context                                 │
│   • middleware.py - retry(), fallback(), augment_with_context()             │
│   • prompt.py - Prompt templates and dotprompt                              │
│   • generate.py - Generation orchestration                                  │
│   • session/ - Chat sessions and state management                           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 4: CORE (genkit/core/)                                              │
│   ────────────────────────────                                              │
│   The foundation. Actions, registry, tracing, and error handling.           │
│                                                                             │
│   • action/ - The fundamental unit of work                                  │
│   • registry.py - Central action storage and lookup                         │
│   • plugin.py - Plugin base class                                           │
│   • tracing.py - OpenTelemetry integration                                  │
│   • error.py - GenkitError and status codes                                 │
│   • typing.py - Auto-generated Pydantic types (DO NOT EDIT!)                │
│   • reflection.py - Dev UI communication                                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 5: PLUGINS (genkit/plugins/*)                                       │
│   ────────────────────────────────────                                      │
│   Provider-specific implementations                                         │
│                                                                             │
│   • google-genai/ - Google AI (Gemini) and Vertex AI                        │
│   • ollama/ - Local models via Ollama                                       │
│   • anthropic/ - Claude models                                              │
│   • openai/ - GPT models                                                    │
│   • ... more plugins                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## How Data Flows Through Genkit

Let's trace what happens when you call `ai.generate()`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW                                        │
│                                                                             │
│   1. YOUR CODE                                                              │
│      response = await ai.generate(                                          │
│          model='googleai/gemini-2.0-flash',                                 │
│          prompt='Hello!',                                                   │
│          use=[retry(max_retries=3)],                                        │
│      )                                                                      │
│           │                                                                 │
│           ▼                                                                 │
│   2. GENKIT VENEER (ai/_base_async.py)                                      │
│      • Validates parameters                                                 │
│      • Resolves model reference to Action                                   │
│      • Applies middleware (retry, fallback, etc.)                           │
│           │                                                                 │
│           ▼                                                                 │
│   3. BLOCKS LAYER (blocks/generate.py)                                      │
│      • Builds GenerateRequest                                               │
│      • Handles output format (JSON, text, etc.)                             │
│      • Manages tool execution loop                                          │
│           │                                                                 │
│           ▼                                                                 │
│   4. REGISTRY LOOKUP (core/registry.py)                                     │
│      • Finds the model action by name                                       │
│      • Returns the Action callable                                          │
│           │                                                                 │
│           ▼                                                                 │
│   5. PLUGIN MODEL (plugins/google-genai/models/gemini.py)                   │
│      • Converts GenerateRequest → Provider API format                       │
│      • Makes HTTP call to provider API                                      │
│      • Converts response → GenerateResponse                                 │
│           │                                                                 │
│           ▼                                                                 │
│   6. TRACING (core/tracing.py)                                              │
│      • Records spans for observability                                      │
│      • Logs input/output for debugging                                      │
│           │                                                                 │
│           ▼                                                                 │
│   7. YOUR CODE                                                              │
│      print(response.text)  # "Hello! How can I help you?"                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The Action System (The Heart of Genkit)

**Everything in Genkit is an Action.** This is the most important concept
to understand. An Action is simply:

1. A function with typed input and output
2. That's registered by name
3. That can be called locally or remotely (via HTTP)
4. That's automatically traced and observable

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WHAT IS AN ACTION?                                │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         ACTION                                        │  │
│   │                                                                       │  │
│   │   Name: "googleai/gemini-2.0-flash"                                   │  │
│   │   Kind: MODEL                                                         │  │
│   │                                                                       │  │
│   │   ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐    │  │
│   │   │   Input     │────▶│    Function     │────▶│    Output       │    │  │
│   │   │ (Pydantic)  │     │  (async def)    │     │  (Pydantic)     │    │  │
│   │   │             │     │                 │     │                 │    │  │
│   │   │ Generate    │     │ Call Gemini API │     │ Generate        │    │  │
│   │   │ Request     │     │ Convert formats │     │ Response        │    │  │
│   │   └─────────────┘     └─────────────────┘     └─────────────────┘    │  │
│   │                                                                       │  │
│   │   Metadata:                                                           │  │
│   │   • input_schema: JSON Schema for validation                         │  │
│   │   • output_schema: JSON Schema for validation                        │  │
│   │   • description: "Gemini 2.0 Flash model"                            │  │
│   │                                                                       │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   Different KINDS of actions:                                               │
│                                                                             │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│   │   MODEL    │ │  EMBEDDER  │ │ RETRIEVER  │ │   TOOL     │              │
│   │            │ │            │ │            │ │            │              │
│   │ Generates  │ │ Creates    │ │ Finds      │ │ Does       │              │
│   │ content    │ │ embeddings │ │ documents  │ │ something  │              │
│   └────────────┘ └────────────┘ └────────────┘ └────────────┘              │
│                                                                             │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│   │  RERANKER  │ │  INDEXER   │ │ EVALUATOR  │ │   FLOW     │              │
│   │            │ │            │ │            │ │            │              │
│   │ Reorders   │ │ Indexes    │ │ Scores     │ │ YOUR       │              │
│   │ results    │ │ content    │ │ outputs    │ │ action     │              │
│   └────────────┘ └────────────┘ └────────────┘ └────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The Registry (The Phone Book)

The Registry is where all Actions live. When you need to use a model,
tool, or any other capability, Genkit looks it up in the Registry.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REGISTRY                                       │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │   Action Name                        │   Action Object               │  │
│   ├──────────────────────────────────────┼───────────────────────────────┤  │
│   │   /model/googleai/gemini-2.0-flash   │   GeminiModel(...)            │  │
│   │   /model/anthropic/claude-sonnet-4   │   ClaudeModel(...)            │  │
│   │   /model/ollama/llama3.3             │   OllamaModel(...)            │  │
│   │   /embedder/googleai/text-embed-004  │   GeminiEmbedder(...)         │  │
│   │   /tool/get_weather                  │   GetWeatherTool(...)         │  │
│   │   /flow/my_custom_flow               │   MyFlowAction(...)           │  │
│   │   /reranker/vertexai/semantic-ranker │   VertexReranker(...)         │  │
│   └──────────────────────────────────────┴───────────────────────────────┘  │
│                                                                             │
│   HOW IT'S USED:                                                            │
│                                                                             │
│   # Plugins register their actions at startup                               │
│   registry.register("/model/googleai/gemini-2.0-flash", gemini_action)      │
│                                                                             │
│   # Genkit looks up actions when you use them                               │
│   action = await registry.lookup_action("/model/googleai/gemini-2.0-flash") │
│   response = await action(request)                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The Plugin System

Plugins are how Genkit supports different AI providers. Each plugin:

1. Registers its models/embedders/tools with the Registry
2. Handles provider-specific API calls
3. Converts between Genkit's types and the provider's types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PLUGIN ARCHITECTURE                                 │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    google-genai Plugin                            │    │
│   │                                                                   │    │
│   │   __init__.py                                                     │    │
│   │   ├── GoogleAI (class)  - Google AI Studio plugin                │    │
│   │   ├── VertexAI (class)  - Vertex AI plugin                       │    │
│   │   └── Exports: models, embedders, config types                   │    │
│   │                                                                   │    │
│   │   models/                                                         │    │
│   │   ├── gemini.py        - Gemini model implementation             │    │
│   │   ├── embedder.py      - Embedding model implementation          │    │
│   │   ├── imagen.py        - Image generation (Imagen)               │    │
│   │   └── model_info.py    - Model registry and capabilities         │    │
│   │                                                                   │    │
│   │   rerankers/                                                      │    │
│   │   └── reranker.py      - Vertex AI semantic ranker               │    │
│   │                                                                   │    │
│   │   evaluators/                                                     │    │
│   │   └── evaluation.py    - Vertex AI evaluation metrics            │    │
│   │                                                                   │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   PLUGIN LIFECYCLE:                                                         │
│                                                                             │
│   1. CREATE: ai = Genkit(plugins=[GoogleAI(api_key="...")])                 │
│                    │                                                        │
│                    ▼                                                        │
│   2. INIT:   Plugin.init(registry)                                          │
│              • Register known models/embedders                              │
│              • Set up API client                                            │
│                    │                                                        │
│                    ▼                                                        │
│   3. RESOLVE: Plugin.resolve(kind, name)                                    │
│               • Called when an unknown action is requested                  │
│               • Create and return the Action on-demand                      │
│                    │                                                        │
│                    ▼                                                        │
│   4. USE:    await ai.generate(model="googleai/gemini-2.0-flash", ...)      │
│              • Registry looks up the action                                 │
│              • Action calls the plugin's model implementation               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

Here's a map of the codebase:

```
py/
├── packages/genkit/                 # Core framework
│   └── src/genkit/
│       ├── __init__.py              # Main exports (Genkit, retry, fallback, etc.)
│       │
│       ├── ai/                      # User-facing API (Veneer)
│       │   ├── __init__.py          # Exports for genkit.ai
│       │   ├── _base_async.py       # Async Genkit class implementation
│       │   ├── _registry.py         # GenkitRegistry wrapper
│       │   ├── _runtime.py          # Runtime configuration
│       │   └── _server.py           # Dev server management
│       │
│       ├── blocks/                  # AI building blocks
│       │   ├── document.py          # Document class for RAG
│       │   ├── embedding.py         # Embedding operations
│       │   ├── generate.py          # Generation orchestration
│       │   ├── middleware.py        # retry(), fallback(), augment_with_context()
│       │   ├── model.py             # Model abstraction
│       │   ├── prompt.py            # Prompt templates
│       │   ├── reranker.py          # Reranking abstraction
│       │   ├── retriever.py         # Retrieval abstraction
│       │   ├── tools.py             # Tool context and interrupts
│       │   ├── session/             # Chat session management
│       │   └── formats/             # Output format handlers (JSON, text, etc.)
│       │
│       ├── core/                    # Foundation
│       │   ├── action/              # Action system
│       │   │   ├── _action.py       # Action class implementation
│       │   │   └── types.py         # ActionKind enum
│       │   ├── registry.py          # Central action registry
│       │   ├── plugin.py            # Plugin base class
│       │   ├── error.py             # GenkitError and status codes
│       │   ├── typing.py            # ⚠️ AUTO-GENERATED - DO NOT EDIT!
│       │   ├── tracing.py           # OpenTelemetry integration
│       │   ├── reflection.py        # Dev UI API
│       │   └── trace/               # Trace exporters
│       │
│       └── web/                     # Web server components
│           └── manager/             # Dev server management
│
├── plugins/                         # Provider plugins
│   ├── google-genai/                # Google AI / Vertex AI
│   ├── ollama/                      # Ollama (local models)
│   ├── anthropic/                   # Anthropic (Claude)
│   ├── openai/                      # OpenAI (GPT)
│   └── ...
│
├── samples/                         # Example applications
│   ├── rag/                         # RAG demo
│   ├── tool-calling/                # Tool calling demo
│   └── ...
│
└── engdoc/                          # Engineering documentation (you are here!)
```

## Common Patterns

### Pattern 1: Defining a Flow (User Action)

```python
from genkit import Genkit
from pydantic import BaseModel

ai = Genkit(plugins=[...])

class SummarizeInput(BaseModel):
    text: str
    max_length: int = 100

class SummarizeOutput(BaseModel):
    summary: str
    word_count: int

@ai.flow()
async def summarize(input: SummarizeInput) -> SummarizeOutput:
    """Summarize the given text."""
    response = await ai.generate(
        prompt=f"Summarize in {input.max_length} words: {input.text}"
    )
    words = response.text.split()
    return SummarizeOutput(summary=response.text, word_count=len(words))
```

### Pattern 2: Defining a Tool

```python
@ai.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # Call weather API...
    return f"The weather in {city} is sunny, 72°F"

# Use in generation
response = await ai.generate(
    prompt="What's the weather like in Paris?",
    tools=[get_weather],
)
```

### Pattern 3: Using Middleware

```python
from genkit import Genkit, retry, fallback

ai = Genkit(plugins=[...])

# Retry on transient failures
response = await ai.generate(
    model='googleai/gemini-2.5-pro',
    prompt='Hello!',
    use=[
        retry(max_retries=3, initial_delay_ms=1000),
        fallback(ai.registry, models=['googleai/gemini-2.0-flash']),
    ],
)
```

### Pattern 4: RAG Pipeline

```python
# 1. Retrieve relevant documents
docs = await ai.retrieve(
    retriever='my-retriever',
    query='How does authentication work?',
)

# 2. Rerank for quality (optional)
ranked_docs = await ai.rerank(
    reranker='vertexai/semantic-ranker-default@latest',
    query='How does authentication work?',
    documents=docs,
    options={'top_n': 5},
)

# 3. Generate with context
response = await ai.generate(
    prompt='Explain how authentication works.',
    docs=ranked_docs,  # Documents automatically added to context
)
```

## Tracing and Observability

Every action in Genkit is automatically traced using OpenTelemetry:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRACE EXAMPLE                                     │
│                                                                             │
│   ai.generate("Hello!")                                                     │
│   │                                                                         │
│   └─► SPAN: generate                                                        │
│       │   start: 2024-01-15T10:00:00.000Z                                   │
│       │   input: {"prompt": "Hello!"}                                       │
│       │                                                                     │
│       └─► SPAN: /model/googleai/gemini-2.0-flash                            │
│           │   start: 2024-01-15T10:00:00.050Z                               │
│           │   input: GenerateRequest{...}                                   │
│           │   output: GenerateResponse{...}                                 │
│           │   duration: 850ms                                               │
│           │                                                                 │
│           └─► SPAN: gemini-api-call (external)                              │
│                   duration: 820ms                                           │
│                   tokens_in: 5                                              │
│                   tokens_out: 42                                            │
│                                                                             │
│   Traces are viewable in:                                                   │
│   • Genkit Developer UI (localhost:4000)                                    │
│   • Google Cloud Trace (when deployed)                                      │
│   • Any OpenTelemetry-compatible backend                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The Developer UI

The Developer UI (`genkit start`) provides:

1. **Action Explorer** - Browse and test all registered actions
2. **Trace Viewer** - Inspect execution traces for debugging
3. **Evaluation Runner** - Run test suites against your flows

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPER UI ARCHITECTURE                            │
│                                                                             │
│   ┌─────────────────────┐          ┌─────────────────────┐                 │
│   │   Your Python App   │          │   Genkit Dev UI     │                 │
│   │                     │          │   (localhost:4000)  │                 │
│   │   ai = Genkit(...)  │          │                     │                 │
│   │   @ai.flow()        │          │   Browser-based     │                 │
│   │   def my_flow(...)  │◄────────►│   developer tools   │                 │
│   │                     │          │                     │                 │
│   └─────────────────────┘          └─────────────────────┘                 │
│            │                                  │                             │
│            │ Reflection API                   │                             │
│            │ (localhost:3100)                 │                             │
│            ▼                                  ▼                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     Telemetry Server                                │  │
│   │                     (trace storage)                                 │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Error Handling

Genkit uses gRPC-style status codes for consistent error handling:

```python
from genkit.core.error import GenkitError

# Raising errors
raise GenkitError(
    status='INVALID_ARGUMENT',
    message='Temperature must be between 0 and 2',
)

# Status codes used in retry/fallback:
# UNAVAILABLE - Service temporarily down
# DEADLINE_EXCEEDED - Request timed out
# RESOURCE_EXHAUSTED - Rate limited
# INTERNAL - Server error
# NOT_FOUND - Model/action not found
```

## Next Steps

Now that you understand the architecture:

1. **Read the code**: Start with `genkit/__init__.py` to see what's exported
2. **Run the samples**: `cd py/samples/hello-world && ./run.sh`
3. **Write a test**: Add tests to `py/packages/genkit/tests/`
4. **Ask questions**: Join us on [Discord](https://discord.gg/qXt5zzQKpc)

See also:
- [GEMINI.md](../GEMINI.md) - Development guidelines
- [Glossary](../extending/glossary.md) - Terminology reference
- [API Reference](../extending/api.md) - Detailed API docs
