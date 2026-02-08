# Genkit Endpoints Sample (REST + gRPC)

A kitchen-sink sample that shows **all the ways** to expose Genkit AI flows
as network endpoints:

- **REST** via ASGI frameworks —
  [FastAPI](https://fastapi.tiangolo.com/),
  [Litestar](https://docs.litestar.dev/), or
  [Quart](https://quart.palletsprojects.com/)
- **gRPC** via [grpcio](https://grpc.io/docs/languages/python/) with
  server reflection (compatible with
  [grpcui](https://github.com/fullstorydev/grpcui) and
  [grpcurl](https://github.com/fullstorydev/grpcurl))

Both servers run in parallel: REST on `:8080`, gRPC on `:50051`.

**This sample is designed to be self-contained and copyable as a template
for your own Genkit projects.**

## Genkit Features Demonstrated

| Feature | API | Where |
|---------|-----|-------|
| **Flows** | `@ai.flow()` | `tell_joke`, `translate_text`, `describe_image`, etc. |
| **Tools** | `@ai.tool()` | `get_current_time` — model-callable function |
| **Structured output** | `Output(schema=...)` | `/translate`, `/generate-character`, `/generate-code` |
| **Streaming (REST)** | `ai.generate_stream()` | `/tell-joke/stream` via SSE |
| **Streaming (flow)** | `flow.stream()` | `/tell-story/stream` via SSE |
| **Streaming (gRPC)** | server-side streaming | `TellStory` RPC → `stream StoryChunk` |
| **Multimodal input** | `Message` + `MediaPart` | `/describe-image` — image URL → text |
| **System prompts** | `system=` parameter | `/chat` — pirate captain persona |
| **Dotprompt** | `ai.prompt()` | `/review-code` — .prompt file with template + schema |
| **Traced steps** | `ai.run()` | `sanitize-input` sub-span inside `translate_text` |
| **ASGI server** | `--server` CLI | uvicorn (default), granian (Rust), or hypercorn |
| **Framework choice** | `--framework` CLI | FastAPI (default), Litestar, or Quart |
| **gRPC server** | `grpc.aio` | All flows exposed as gRPC RPCs with reflection |

## Architecture

### System overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        python -m src                                │
│                                                                     │
│  ┌─────────────┐   ┌───────────────────────────────────────────┐   │
│  │  CLI + Config│──▶│           main.py  (entry point)          │   │
│  │  config.py   │   │                                           │   │
│  └─────────────┘   │   _create_app()         _serve_both()     │   │
│                     │        │                   │    │          │   │
│                     └────────┼───────────────────┼────┼──────────┘   │
│                              ▼                   ▼    ▼              │
│  ┌──────────── REST (ASGI) ──────────┐  ┌──── gRPC ────────────┐   │
│  │                                   │  │                       │   │
│  │  --framework selects one:         │  │  grpc_server.py       │   │
│  │  ┌───────────┐ ┌──────────┐       │  │  GenkitServiceServicer│   │
│  │  │  FastAPI   │ │ Litestar │       │  │  grpc.aio.server()   │   │
│  │  │  (default) │ │          │       │  │                       │   │
│  │  └─────┬─────┘ └────┬─────┘       │  │  Reflection enabled  │   │
│  │        │    ┌────────┘             │  │  (grpcui / grpcurl)  │   │
│  │        │    │  ┌──────────┐        │  │                       │   │
│  │        │    │  │  Quart   │        │  └───────────┬───────────┘   │
│  │        │    │  └────┬─────┘        │              │               │
│  │        └────┴───────┘              │              │               │
│  │              │                     │              │               │
│  │  --server selects one:            │              │               │
│  │  granian (Rust) │ uvicorn │ hypercorn │           │               │
│  │  :8080                            │              │  :50051        │
│  └───────────────┬───────────────────┘              │               │
│                  │                                   │               │
│                  ▼                                   ▼               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Genkit flows  (flows.py)                  │   │
│  │                                                               │   │
│  │  tell_joke  translate_text  describe_image  generate_character│   │
│  │  pirate_chat  tell_story  generate_code  review_code          │   │
│  │                                                               │   │
│  │  Shared: @ai.flow() + @ai.tool() + Pydantic schemas          │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────┼───────────────────────────────────┐   │
│  │           Genkit runtime (ai = Genkit(...))                   │   │
│  │  app_init.py — singleton, plugin loading, telemetry detect   │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
               ┌──────────────────────────┐
               │      Gemini API          │
               │  (Google AI / Vertex AI) │
               └──────────────────────────┘
```

### Request dataflow

```
  Client                 Server                         External
  ──────                 ──────                         ────────

  HTTP POST              ┌───────────────┐
  /tell-joke ──────────▶ │  FastAPI /     │
  Content-Type:          │  Litestar /    │
  application/json       │  Quart         │
                         │  (route handler)│
                         └───────┬────────┘
                                 │
  grpcurl TellJoke       ┌───────┴────────┐
  -plaintext ──────────▶ │  gRPC servicer │
  localhost:50051        │  (grpc_server) │
                         └───────┬────────┘
                                 │
                                 ▼
                         ┌───────────────┐      ┌─────────────────┐
                         │  Genkit Flow  │─────▶│  Pydantic       │
                         │  (flows.py)   │      │  validate input │
                         └───────┬───────┘      └─────────────────┘
                                 │
                      ┌──────────┼──────────┐
                      ▼          ▼          ▼
               ┌──────────┐ ┌────────┐ ┌────────┐
               │ai.generate│ │ai.run()│ │@ai.tool│
               │  (model)  │ │(traced │ │get_    │
               │           │ │ step)  │ │current_│
               │           │ │        │ │time    │
               └─────┬─────┘ └────────┘ └────────┘
                     │
                     ▼
              ┌──────────────┐
              │  Gemini API  │
              │  (generate)  │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐      ┌──────────────────┐
              │  Structured  │─────▶│  Pydantic model  │
              │  JSON output │      │  (response_model) │
              └──────┬───────┘      └──────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  JSON / SSE  │ ←── REST response
              │  Protobuf    │ ←── gRPC response
              └──────────────┘
```

### Streaming dataflow (SSE and gRPC)

```
  REST streaming (/tell-joke/stream, /tell-story/stream):

    Client                   Handler                     Genkit
    ──────                   ───────                     ──────
    POST /tell-joke/stream
    ─────────────────────▶  ai.generate_stream()  ────▶  Gemini
                                                          │
                            ◀──── chunk.text ◀────────────┘
    ◀── data: {"chunk":...}                               │
                            ◀──── chunk.text ◀────────────┘
    ◀── data: {"chunk":...}                               │
    ...                     ...                           ...
                            ◀──── final response ◀────────┘
    ◀── data: {"done":true}


  REST streaming (/tell-story/stream) — flow-level streaming:

    Client                   Handler                     Flow
    ──────                   ───────                     ────
    POST /tell-story/stream
    ─────────────────────▶  tell_story.stream()  ────▶  ctx.send_chunk()
                                                          │
                            ◀──── chunk ◀─────────────────┘
    ◀── data: {"chunk":...}                               │
    ...                     ...                           ...
                            ◀──── final ◀─────────────────┘
    ◀── data: {"done":true}


  gRPC server streaming (TellStory):

    Client                   Servicer                    Flow
    ──────                   ────────                    ────
    TellStory(StoryRequest)
    ─────────────────────▶  tell_story.stream()  ────▶  ctx.send_chunk()
                                                          │
                            ◀──── chunk ◀─────────────────┘
    ◀── StoryChunk{text}                                  │
                            ◀──── chunk ◀─────────────────┘
    ◀── StoryChunk{text}                                  │
    ...                     ...                           ...
    ◀── (stream ends)       await future
```

### Telemetry dataflow

```
  Request
    │
    ▼
  ┌──────────────────┐    ┌──────────────────────────────────────┐
  │  ASGI middleware  │    │  Telemetry auto-detection            │
  │  (OpenTelemetry)  │    │  (app_init.py at import time)        │
  │                   │    │                                      │
  │  Creates root     │    │  K_SERVICE?  ──▶ GCP Cloud Trace     │
  │  span for each    │    │  AWS_EXEC?   ──▶ AWS X-Ray           │
  │  HTTP request     │    │  CONTAINER?  ──▶ Azure App Insights  │
  └────────┬──────────┘    │  OTLP_EP?   ──▶ Generic OTLP        │
           │               │  (none)     ──▶ No export            │
           ▼               └──────────────────────────────────────┘
  ┌──────────────────┐
  │  Genkit flow     │──▶ child span: "tell_joke"
  │                   │──▶ child span: "sanitize-input" (ai.run)
  │                   │──▶ child span: "ai.generate" (model call)
  └────────┬──────────┘
           │
           ▼
  ┌──────────────────┐
  │  OTLP exporter   │──▶  Jaeger / Cloud Trace / X-Ray / etc.
  │  (HTTP or gRPC)  │
  └──────────────────┘
```

Both REST and gRPC endpoints call the **same** Genkit flows, so traces,
metrics, and the DevUI work identically regardless of protocol.

## Module Structure

```
src/
├── __init__.py          — Package marker
├── __main__.py          — python -m src entry point
├── app_init.py          — Genkit singleton, plugin loading, platform telemetry
├── asgi.py              — ASGI app factory for gunicorn (multi-worker production)
├── cache.py             — TTL + LRU response cache for idempotent flows
├── circuit_breaker.py   — Circuit breaker for LLM API failure protection
├── config.py            — Settings (pydantic-settings), env files, CLI args
├── connection.py        — Connection pool / keep-alive tuning for outbound HTTP
├── flows.py             — @ai.flow() and @ai.tool() definitions
├── log_config.py        — Structured logging (Rich + structlog, JSON mode)
├── main.py              — CLI entry point: parse args → create app → start servers
├── rate_limit.py        — Token-bucket rate limiting (ASGI + gRPC)
├── resilience.py        — Shared singletons for cache + circuit breaker
├── schemas.py           — Pydantic input/output models (shared by all adapters)
├── security.py          — Security headers, body size, request ID middleware
├── sentry_init.py       — Optional Sentry error tracking
├── server.py            — ASGI server helpers (granian / uvicorn / hypercorn)
├── telemetry.py         — OpenTelemetry OTLP setup + framework instrumentation
├── frameworks/
│   ├── __init__.py      — Framework adapter package
│   ├── fastapi_app.py   — FastAPI create_app(ai) factory + routes
│   ├── litestar_app.py  — Litestar create_app(ai) factory + routes
│   └── quart_app.py     — Quart create_app(ai) factory + routes
├── generated/           — Protobuf + gRPC stubs (auto-generated)
│   ├── genkit_sample_pb2.py
│   └── genkit_sample_pb2_grpc.py
└── grpc_server.py       — GenkitServiceServicer + serve_grpc()
gunicorn.conf.py         — Gunicorn config for multi-worker production deployments
protos/
└── genkit_sample.proto  — gRPC service definition (genkit.sample.v1)
prompts/
└── code_review.prompt   — Dotprompt template for /review-code
```

## Endpoints

All three REST frameworks expose **identical routes** — only the internal
plumbing differs (see [Framework Comparison](#framework-comparison) below).
The gRPC service mirrors the REST routes 1:1.

### Endpoint map (REST + gRPC side by side)

| Genkit Flow | REST Endpoint | gRPC RPC | Input Schema | Output Schema | Genkit Feature |
|-------------|---------------|----------|--------------|---------------|----------------|
| `tell_joke` | `POST /tell-joke` | `TellJoke` (unary) | `JokeInput{name, username}` | `JokeResponse{joke, username}` | Basic flow |
| *(handler)* | `POST /tell-joke/stream` | — | `JokeInput{name}` | SSE `{chunk}...{done, joke}` | `ai.generate_stream()` |
| `tell_story` | `POST /tell-story/stream` | `TellStory` (server stream) | `StoryInput{topic}` | SSE `{chunk}...{done, story}` / `stream StoryChunk` | `flow.stream()` + `ctx.send_chunk()` |
| `translate_text` | `POST /translate` | `TranslateText` (unary) | `TranslateInput{text, target_language}` | `TranslationResult{original_text, translated_text, target_language, confidence}` | Structured output + tool use + traced step |
| `describe_image` | `POST /describe-image` | `DescribeImage` (unary) | `ImageInput{image_url}` | `ImageResponse{description, image_url}` | Multimodal (text + image) |
| `generate_character` | `POST /generate-character` | `GenerateCharacter` (unary) | `CharacterInput{name}` | `RpgCharacter{name, back_story, abilities, skills}` | Structured output (nested) |
| `pirate_chat` | `POST /chat` | `PirateChat` (unary) | `ChatInput{question}` | `ChatResponse{answer, persona}` | System prompt |
| `generate_code` | `POST /generate-code` | `GenerateCode` (unary) | `CodeInput{description, language}` | `CodeOutput{code, language, explanation, filename}` | Structured output |
| `review_code` | `POST /review-code` | `ReviewCode` (unary) | `CodeReviewInput{code, language}` | `CodeReviewResponse{review}` (JSON) | Dotprompt (.prompt file) |
| *(built-in)* | `GET /health` | `Health` (unary) | — | `{status: "ok"}` | Health check |
| *(built-in)* | `GET /docs` | *(reflection)* | — | Swagger UI / OpenAPI schema | API docs |

### REST endpoints (`:8080`)

All three frameworks serve on the same port with the same routes. The
`--framework` flag selects which adapter is used at startup.

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/tell-joke` | Generate a joke | `{"name": "Mittens", "username": null}` | `{"joke": "...", "username": null}` |
| `POST` | `/tell-joke/stream` | SSE streaming joke | `{"name": "Python"}` | `data: {"chunk": "Why"}\ndata: {"chunk": " did"}...\ndata: {"done": true, "joke": "..."}` |
| `POST` | `/tell-story/stream` | SSE streaming story (flow-level) | `{"topic": "a robot learning to paint"}` | `data: {"chunk": "Once upon"}...\ndata: {"done": true, "story": "..."}` |
| `POST` | `/translate` | Structured translation + tool use | `{"text": "Hello", "target_language": "Japanese"}` | `{"original_text": "Hello", "translated_text": "...", "target_language": "Japanese", "confidence": "high"}` |
| `POST` | `/describe-image` | Multimodal image description | `{"image_url": "https://..."}` | `{"description": "...", "image_url": "https://..."}` |
| `POST` | `/generate-character` | Structured RPG character | `{"name": "Luna"}` | `{"name": "Luna", "backStory": "...", "abilities": [...], "skills": {"strength": 80, ...}}` |
| `POST` | `/generate-code` | Code generation (structured) | `{"description": "reverse a linked list", "language": "python"}` | `{"code": "...", "language": "python", "explanation": "...", "filename": "reverse.py"}` |
| `POST` | `/review-code` | Code review via Dotprompt | `{"code": "def add(a, b):...", "language": "python"}` | `{"summary": "...", "issues": [...], ...}` |
| `POST` | `/chat` | Pirate captain persona | `{"question": "Best programming language?"}` | `{"answer": "Arrr! ...", "persona": "pirate captain"}` |
| `GET`  | `/health` | Health check | — | `{"status": "ok"}` |
| `GET`  | `/docs` | API documentation | — | Swagger UI (FastAPI), Schema explorer (Litestar), N/A (Quart) |

**Framework-specific differences:**

| Aspect | FastAPI | Litestar | Quart |
|--------|---------|----------|-------|
| **Request body** | Pydantic model auto-parsed | Pydantic model auto-parsed | Manual `request.get_json()` + model init |
| **Response** | Return Pydantic model directly | Return Pydantic model directly | Return `model.model_dump()` dict |
| **SSE streaming** | `StreamingResponse(gen())` | `Stream(iterator=gen())` | `Response(gen(), content_type=...)` |
| **Auth header** | `Header(default=None)` param | Via `data.username` field | `request.headers.get(...)` |
| **API docs** | `/docs` (Swagger UI) + `/redoc` | `/schema` (built-in explorer) | None (Flask-style) |
| **Source file** | `src/frameworks/fastapi_app.py` | `src/frameworks/litestar_app.py` | `src/frameworks/quart_app.py` |

### gRPC endpoints (`:50051`)

The gRPC service is defined in `protos/genkit_sample.proto` under package
`genkit.sample.v1`. Every RPC delegates to the same Genkit flow used by
REST, so traces are identical regardless of protocol.

| RPC | Type | Request | Response | Genkit Flow |
|-----|------|---------|----------|-------------|
| `Health` | Unary | `HealthRequest{}` | `HealthResponse{status}` | *(direct)* |
| `TellJoke` | Unary | `JokeRequest{name, username}` | `JokeResponse{joke, username}` | `tell_joke` |
| `TranslateText` | Unary | `TranslateRequest{text, target_language}` | `TranslationResponse{original_text, translated_text, target_language, confidence}` | `translate_text` |
| `DescribeImage` | Unary | `ImageRequest{image_url}` | `ImageResponse{description, image_url}` | `describe_image` |
| `GenerateCharacter` | Unary | `CharacterRequest{name}` | `RpgCharacter{name, back_story, abilities[], skills{strength, charisma, endurance}}` | `generate_character` |
| `PirateChat` | Unary | `ChatRequest{question}` | `ChatResponse{answer, persona}` | `pirate_chat` |
| `TellStory` | **Server streaming** | `StoryRequest{topic}` | `stream StoryChunk{text}` | `tell_story` (via `flow.stream()`) |
| `GenerateCode` | Unary | `CodeRequest{description, language}` | `CodeResponse{code, language, explanation, filename}` | `generate_code` |
| `ReviewCode` | Unary | `CodeReviewRequest{code, language}` | `CodeReviewResponse{review}` (JSON string) | `review_code` |

gRPC **reflection** is enabled, so `grpcui` and `grpcurl` can discover
all methods without needing the `.proto` file.

**How gRPC maps to REST:**

```
  gRPC                          REST                        Genkit Flow
  ────                          ────                        ───────────
  TellJoke(JokeRequest)    ←→   POST /tell-joke             tell_joke()
  TellStory(StoryRequest)  ←→   POST /tell-story/stream     tell_story()
  TranslateText(...)       ←→   POST /translate              translate_text()
  DescribeImage(...)       ←→   POST /describe-image         describe_image()
  GenerateCharacter(...)   ←→   POST /generate-character     generate_character()
  PirateChat(...)          ←→   POST /chat                   pirate_chat()
  GenerateCode(...)        ←→   POST /generate-code          generate_code()
  ReviewCode(...)          ←→   POST /review-code            review_code()
  Health(HealthRequest)    ←→   GET  /health                 (direct)
```

## Setup

### Prerequisites

The `./setup.sh` script auto-detects your OS and installs all tools:

```bash
./setup.sh           # Install everything
./setup.sh --check   # Just check what's installed
```

| Tool | macOS | Debian / Ubuntu | Fedora |
|------|-------|-----------------|--------|
| **uv** | curl installer | curl installer | curl installer |
| **just** | `brew install just` | `apt install just` (24.04+) or official installer | `dnf install just` (39+) or official installer |
| **podman** (or docker) | `brew install podman` | `apt install podman` | `dnf install podman` |
| **genkit CLI** | `npm install -g genkit-cli` | `npm install -g genkit-cli` | `npm install -g genkit-cli` |
| **grpcurl** | `brew install grpcurl` | `go install .../grpcurl@latest` or prebuilt binary | `go install .../grpcurl@latest` or prebuilt binary |
| **grpcui** | `brew install grpcui` | `go install .../grpcui@latest` | `go install .../grpcui@latest` |
| **shellcheck** | `brew install shellcheck` | `apt install shellcheck` | `dnf install ShellCheck` |

### Get a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key

```bash
export GEMINI_API_KEY=<your-api-key>
```

### Per-Environment Secrets (optional)

For local dev / staging / prod separation, use
[dotenvx](https://dotenvx.com/) or a `.env` file:

```bash
# .local.env (git-ignored, local development)
GEMINI_API_KEY=AIza...

# .staging.env
GEMINI_API_KEY=AIza_staging_key...

# .production.env
GEMINI_API_KEY=AIza_prod_key...
```

```bash
# Load a specific environment
dotenvx run -f .staging.env -- ./run.sh
```

For deployed environments, use the platform's native secrets instead
(see [Secrets Management](#secrets-management) below).

## Run Locally (Dev Mode)

```bash
./run.sh                            # FastAPI + uvicorn + gRPC (default)
./run.sh --framework litestar       # Litestar + uvicorn + gRPC
./run.sh --framework quart          # Quart + uvicorn + gRPC
./run.sh --server uvicorn           # FastAPI + uvicorn + gRPC
./run.sh --server hypercorn         # FastAPI + hypercorn + gRPC
./run.sh --no-grpc                  # REST only, no gRPC server
./run.sh --grpc-port 50052          # Custom gRPC port
```

This starts:
- **REST API** (via uvicorn) on `http://localhost:8080` — your ASGI server
- **gRPC server** on `localhost:50051` — reflection enabled for grpcui/grpcurl
- **Genkit DevUI** on `http://localhost:4000` — flow debugging
- **Swagger UI** auto-opens in your browser at `http://localhost:8080/docs`

### CLI Options

```
python -m src [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--framework {fastapi,litestar,quart}` | `fastapi` | ASGI framework to use |
| `--server {granian,uvicorn,hypercorn}` | `uvicorn` | ASGI server to use |
| `--env ENV` | *(none)* | Load `.<ENV>.env` on top of `.env` (e.g. `--env staging`) |
| `--port PORT` | `$PORT` or `8080` | REST API port |
| `--grpc-port PORT` | `$GRPC_PORT` or `50051` | gRPC server port |
| `--no-grpc` | *(off)* | Disable the gRPC server (REST only) |
| `--no-telemetry` | *(off)* | Disable all telemetry export |
| `--otel-endpoint URL` | *(none)* | OpenTelemetry collector endpoint |
| `--otel-protocol` | `http/protobuf` | OTLP export protocol |
| `--otel-service-name` | `genkit-endpoints-hello` | Service name in traces |

**Configuration priority** (highest wins):

1. CLI arguments (`--port`, `--server`, `--framework`)
2. Environment variables (`export GEMINI_API_KEY=...`)
3. `.<env>.env` file (via `--env`)
4. `.env` file (shared defaults)
5. Settings defaults

**Examples:**

```bash
# Default: FastAPI + uvicorn on port 8080, load .env
python -m src

# Litestar with staging config (.env + .staging.env)
python -m src --framework litestar --env staging

# Production with uvicorn on custom port
python -m src --env production --server uvicorn --port 9090
```

### Server Comparison

| Server | Language | Event Loop | HTTP/2 | WebSocket | Best For |
|--------|----------|-----------|--------|-----------|----------|
| **uvicorn** (default) | Python | uvloop (libuv) | ❌ | ✅ | Ecosystem compatibility — most popular |
| **granian** | Rust | tokio (built-in) | ✅ | ✅ | Production throughput — fastest in benchmarks |
| **hypercorn** | Python | anyio (asyncio/trio) | ✅ | ✅ | Quart users, HTTP/2 — same author as Quart |
| **daphne** *(not included)* | Python | Twisted | ✅ | ✅ | Django Channels only |

### Framework Comparison

| Feature | **FastAPI** (default) | **Litestar** | **Quart** |
|---------|----------------------|-------------|-----------|
| **API style** | Decorator + type hints | Decorator + type hints | Flask-style decorators |
| **Auto API docs** | ✅ Swagger UI + ReDoc | ✅ Built-in schema UI | ❌ Manual (Flask-like) |
| **Pydantic models** | ✅ Native (v1 + v2) | ✅ Native (v2 + attrs + msgspec) | ⚠️ Manual `.model_dump()` |
| **SSE streaming** | ✅ `StreamingResponse` | ✅ `Stream` | ✅ `Response` generator |
| **Dependency injection** | ✅ `Depends()` | ✅ Built-in DI container | ❌ Manual / Flask extensions |
| **Middleware** | ✅ Starlette-based | ✅ Own middleware stack | ✅ Flask-style `before_request` |
| **OpenTelemetry** | ✅ `opentelemetry-instrumentation-fastapi` | ✅ Built-in `litestar.contrib.opentelemetry` | ✅ Generic ASGI middleware |
| **WebSocket** | ✅ Native | ✅ Native | ✅ Native |
| **Ecosystem** | ⭐⭐⭐⭐⭐ Largest | ⭐⭐⭐ Growing | ⭐⭐⭐ Flask ecosystem |
| **Best for** | New async projects | Performance-critical APIs | **Migrating from Flask** |
| **Django** *(not included)* | — | — | — |

> **Why not Django?** Django supports ASGI since 3.0+, but it's a full-stack
> framework (ORM, admin, settings module, etc.) with a fundamentally different
> project structure. Django users should integrate Genkit into their existing
> Django project rather than starting from this template.

## Production Mode

In production, set `GENKIT_ENV` to anything other than `dev` (or leave it
unset — it defaults to production). This disables the Genkit DevUI
reflection server entirely:

```bash
# Production: only the ASGI app runs, no DevUI on :4000
GENKIT_ENV=prod python -m src

# In containers/Cloud Run/etc., GENKIT_ENV is not set → production by default
python -m src
```

| Mode | `GENKIT_ENV` | Servers |
|------|-------------|----------|
| Development | `dev` | REST `:8080` + gRPC `:50051` + DevUI `:4000` |
| Production | unset / any other value | REST `:8080` + gRPC `:50051` |

## Test the API

### Non-streaming joke

```bash
# Default name ("Mittens")
curl -X POST http://localhost:8080/tell-joke \
  -H "Content-Type: application/json" \
  -d '{}'

# Custom name
curl -X POST http://localhost:8080/tell-joke \
  -H "Content-Type: application/json" \
  -d '{"name": "Banana"}'

# With authorization context
curl -X POST http://localhost:8080/tell-joke \
  -H "Content-Type: application/json" \
  -H "Authorization: Alice" \
  -d '{"name": "Waffles"}'
```

### Streaming joke (SSE)

> **Important:** The `-N` flag disables curl's output buffering. Without it,
> curl will buffer the entire response and dump it all at once, making it
> look like streaming isn't working.

```bash
curl -N -X POST http://localhost:8080/tell-joke/stream \
  -H "Content-Type: application/json" \
  -d '{"name": "Python"}'
```

You should see tokens arrive one-by-one:
```
data: {"chunk": "Why"}
data: {"chunk": " did"}
data: {"chunk": " Python"}
...
data: {"done": true, "joke": "Why did Python..."}
```

### Streaming story via `flow.stream()` (SSE)

This endpoint demonstrates the *idiomatic* Genkit approach: the flow itself
calls `ctx.send_chunk()`, and the HTTP handler uses `flow.stream()` to
consume chunks. Compare with the joke stream above, which uses
`ai.generate_stream()` directly in the handler.

```bash
curl -N -X POST http://localhost:8080/tell-story/stream \
  -H "Content-Type: application/json" \
  -d '{"topic": "a robot learning to paint"}'
```

### Structured translation (with tool use)

```bash
curl -X POST http://localhost:8080/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?", "target_language": "Japanese"}'
```

Returns structured JSON:
```json
{
  "original_text": "Hello, how are you?",
  "translated_text": "こんにちは、お元気ですか？",
  "target_language": "Japanese",
  "confidence": "high"
}
```

### Describe an image (multimodal)

```bash
curl -X POST http://localhost:8080/describe-image \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"}'
```

### Generate an RPG character (structured output)

```bash
curl -X POST http://localhost:8080/generate-character \
  -H "Content-Type: application/json" \
  -d '{"name": "Luna"}'
```

### Chat with a pirate captain (system prompt)

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the best programming language?"}'
```

### Generate code

```bash
curl -X POST http://localhost:8080/generate-code \
  -H "Content-Type: application/json" \
  -d '{"description": "a function that reverses a linked list", "language": "python"}'
```

### Review code (Dotprompt)

This endpoint uses a `.prompt` file for the template, model config, and output
schema — no prompt engineering in Python code:

```bash
curl -X POST http://localhost:8080/review-code \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a, b):\n    return a + b", "language": "python"}'
```

### Health check

```bash
curl http://localhost:8080/health
```

### Run REST tests

With the server running, exercise all REST endpoints at once:

```bash
./test_endpoints.sh
```

Test against a deployed instance:

```bash
BASE_URL=https://my-app.run.app ./test_endpoints.sh
```

### Test gRPC endpoints

Install `grpcurl` and `grpcui`:

```bash
# macOS
brew install grpcurl grpcui

# Linux (via Go)
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
go install github.com/fullstorydev/grpcui/cmd/grpcui@latest

# Or run setup.sh to auto-install everything
./setup.sh
```

**Interactive web UI** (like Swagger UI, but for gRPC):

```bash
grpcui -plaintext localhost:50051
```

**CLI testing** with `grpcurl`:

```bash
# List services
grpcurl -plaintext localhost:50051 list

# Describe the service
grpcurl -plaintext localhost:50051 describe genkit.sample.v1.GenkitService

# Call a unary RPC
grpcurl -plaintext -d '{"name": "Waffles"}' \
  localhost:50051 genkit.sample.v1.GenkitService/TellJoke

# Server-streaming RPC
grpcurl -plaintext -d '{"topic": "a robot learning to paint"}' \
  localhost:50051 genkit.sample.v1.GenkitService/TellStory
```

**Run all gRPC tests** (automated):

```bash
./test_grpc_endpoints.sh
```

**Run both REST + gRPC tests:**

```bash
just test-all
```

## Deploy

Each platform has a ready-to-use deployment script. All require
`GEMINI_API_KEY` to be set in your environment.

A [`justfile`](https://github.com/casey/just) is included for convenience.
Run `just` to see all available commands:

```
just                        # Show all commands
just dev                    # Start app + Jaeger (uses podman or docker)
just dev-litestar           # Same, with Litestar framework
just dev-quart              # Same, with Quart framework
just stop                   # Stop everything (app, gRPC, DevUI, Jaeger)
just test                   # Run pytest (unit + telemetry)
just test-endpoints         # REST integration tests
just test-grpc-endpoints    # gRPC integration tests
just test-all               # Both REST + gRPC tests
just proto                  # Regenerate gRPC stubs from .proto
just grpcui                 # Open grpcui web UI
just grpc-list              # List gRPC services via reflection
just deploy-cloudrun        # Deploy to Cloud Run
just deploy-appengine       # Deploy to App Engine
just deploy-firebase        # Deploy via Firebase Hosting + Cloud Run
just deploy-flyio           # Deploy to Fly.io
just deploy-aws             # Deploy to AWS App Runner
just deploy-azure           # Deploy to Azure Container Apps
just lint                   # Shellcheck all scripts
just fmt                    # Format Python code
just clean                  # Remove build artifacts
```

### Container (podman or docker)

The `Containerfile` uses a **distroless** runtime image
(`gcr.io/distroless/python3-debian13:nonroot`) for a minimal, secure
production image — no shell, no package manager, runs as non-root
(Python 3.13, Debian 13 trixie).

All scripts and `just` targets auto-detect which container runtime is
available, preferring **podman** and falling back to **docker**.

```bash
# Build the image (auto-detects podman or docker via `just`)
just build

# Or directly — replace `podman` with `docker` if that's what you have:
podman build -f Containerfile -t genkit-endpoints .

# Run locally (expose both REST and gRPC ports)
just run-container

# Or directly:
podman run -p 8080:8080 -p 50051:50051 -e GEMINI_API_KEY=$GEMINI_API_KEY genkit-endpoints

# Push to a registry (e.g. Google Artifact Registry)
podman tag genkit-endpoints us-docker.pkg.dev/PROJECT/REPO/genkit-endpoints
podman push us-docker.pkg.dev/PROJECT/REPO/genkit-endpoints
```

### Google Cloud Run

Cloud Run is the **recommended** deployment target. It supports containers,
auto-scales to zero, and sets `PORT` automatically.

```bash
./deploy_cloudrun.sh                          # Interactive project
./deploy_cloudrun.sh --project=my-project     # Explicit project
./deploy_cloudrun.sh --region=europe-west1    # Non-default region
```

Or manually:

```bash
gcloud run deploy genkit-endpoints \
  --source . \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --allow-unauthenticated
```

### Google App Engine (Flex)

Uses the `app.yaml` in this directory:

```bash
./deploy_appengine.sh                        # Interactive project
./deploy_appengine.sh --project=my-project   # Explicit project
```

### Firebase Hosting + Cloud Run

Deploys to Cloud Run, then sets up Firebase Hosting to proxy all traffic
to the Cloud Run service. This is the recommended workaround since
`firebase-functions-python` does not yet support `onCallGenkit`.

```bash
./deploy_firebase_hosting.sh --project=my-project
./deploy_firebase_hosting.sh --project=my-project --region=europe-west1
```

> **Note:** Firebase Cloud Functions for Python (via `firebase-functions`)
> does not yet have a Genkit integration equivalent to the JS SDK's
> `onCallGenkit`. The Python SDK is Flask-based (sync) with no async
> roadmap yet ([issue #135](https://github.com/firebase/firebase-functions-python/issues/135)).

### Fly.io

Fly.io provides global edge deployment with auto-scaling:

```bash
./deploy_flyio.sh                          # Default app name + region
./deploy_flyio.sh --app=my-genkit-app      # Custom app name
./deploy_flyio.sh --region=lhr             # Deploy to London
```

The script generates a `fly.toml` on first run and sets `GEMINI_API_KEY`
as a Fly.io secret (not stored in config files).

### AWS App Runner

App Runner deploys containers directly from Amazon ECR with auto-scaling:

```bash
./deploy_aws.sh                              # Interactive setup
./deploy_aws.sh --region=us-east-1           # Explicit region
./deploy_aws.sh --service=my-genkit-app      # Custom service name
```

The script auto-detects and installs the AWS CLI, creates an ECR repository,
builds and pushes the container, and creates or updates the App Runner service.

### Azure Container Apps

Container Apps provide serverless containers on Azure with scale-to-zero:

```bash
./deploy_azure.sh                                  # Interactive setup
./deploy_azure.sh --resource-group=my-rg            # Explicit resource group
./deploy_azure.sh --location=westeurope             # Non-default location
./deploy_azure.sh --app=my-genkit-app               # Custom app name
```

The script auto-detects and installs the Azure CLI, creates a resource group
and ACR, builds the container via ACR Build, and creates or updates the
Container App.

### Secrets Management

Each platform has its own way to provide `GEMINI_API_KEY` securely:

| Platform | Quick start | Production recommendation |
|----------|------------|-----------------------------|
| **Local dev** | `export GEMINI_API_KEY=...` | Use [dotenvx](https://dotenvx.com/) with `.local.env` |
| **Container** | `podman run -e GEMINI_API_KEY=... ` | Mount from vault / CI secret |
| **Cloud Run** | `--set-env-vars GEMINI_API_KEY=...` | [Secret Manager](https://cloud.google.com/run/docs/configuring/services/secrets) |
| **App Engine Flex** | `env_variables` in `app.yaml` | [Secret Manager](https://cloud.google.com/appengine/docs/flexible/reference/app-yaml#secrets) |
| **Firebase + Cloud Run** | Same as Cloud Run | Same as Cloud Run |
| **Fly.io** | `flyctl secrets set GEMINI_API_KEY=...` | Fly.io secrets (already encrypted) |
| **AWS App Runner** | `--set-env-vars GEMINI_API_KEY=...` | [Systems Manager Parameter Store](https://docs.aws.amazon.com/apprunner/latest/dg/manage-configure.html) |
| **Azure Container Apps** | `--env-vars GEMINI_API_KEY=...` | [Key Vault](https://learn.microsoft.com/azure/container-apps/manage-secrets) |

**Cloud Run with Secret Manager** (recommended for production):

```bash
# 1. Create the secret
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# 2. Deploy with the secret mounted as an env var
gcloud run deploy genkit-endpoints \
  --source . \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --allow-unauthenticated
```

> **Tip:** The deploy scripts use plaintext env vars for quick demos.
> For production, always use your platform's native secrets manager.

### GitHub Actions CI/CD

Pre-built GitHub Actions workflows are included in `.github/workflows/`.
All are **disabled by default** (manual `workflow_dispatch` trigger only).

| Workflow | File | What it does |
|----------|------|-------------|
| **CI** | `ci.yml` | Lint, type-check (ty + pyrefly + pyright), test (Python 3.10-3.13), security scan |
| **Cloud Run** | `deploy-cloudrun.yml` | Build from source, deploy to Cloud Run via Workload Identity Federation |
| **App Engine** | `deploy-appengine.yml` | Deploy to App Engine Flex via Workload Identity Federation |
| **Firebase Hosting** | `deploy-firebase.yml` | Deploy to Cloud Run + Firebase Hosting proxy |
| **AWS App Runner** | `deploy-aws.yml` | Build container, push to ECR, deploy to App Runner via OIDC |
| **Azure Container Apps** | `deploy-azure.yml` | Build container, push to ACR, deploy to Container Apps via OIDC |
| **Fly.io** | `deploy-flyio.yml` | Deploy container to Fly.io via deploy token |

**To enable CI on push/PR**, uncomment the `push` / `pull_request` triggers
in `ci.yml`. For deploy workflows, use the GitHub UI "Run workflow" button
or wire them to run on release tags.

**Required secrets per platform:**

| Platform | Secrets |
|----------|---------|
| CI | (none) |
| Cloud Run / App Engine / Firebase | `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SERVICE_ACCOUNT`, `GCP_WORKLOAD_IDENTITY`, `GEMINI_API_KEY` |
| AWS | `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ECR_REPOSITORY`, `GEMINI_API_KEY` |
| Azure | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_ACR_NAME`, `AZURE_RESOURCE_GROUP`, `GEMINI_API_KEY` |
| Fly.io | `FLY_API_TOKEN`, `GEMINI_API_KEY` |

> All deploy workflows use **OIDC / Workload Identity Federation** (no
> long-lived credentials). See each workflow file's header comments for
> detailed setup instructions.

## Telemetry

The app auto-detects the cloud platform at startup and enables the
appropriate telemetry plugin. All three frameworks (FastAPI, Litestar,
Quart) are instrumented via OpenTelemetry:

| Cloud | Detection env var | Plugin | Data sent to |
|-------|------------------|--------|--------------||
| **GCP** (Cloud Run, GCE, GKE) | `K_SERVICE`, `GOOGLE_CLOUD_PROJECT` | `genkit-plugin-google-cloud` | Cloud Trace + Monitoring |
| **AWS** (App Runner, ECS) | `AWS_EXECUTION_ENV`, `ECS_CONTAINER_METADATA_URI` | `genkit-plugin-amazon-bedrock` | AWS X-Ray |
| **Azure** (Container Apps, App Service) | `CONTAINER_APP_NAME`, `WEBSITE_SITE_NAME` | `genkit-plugin-microsoft-foundry` | Application Insights |
| **Generic OTLP** | `OTEL_EXPORTER_OTLP_ENDPOINT` | `genkit-plugin-observability` | Any OTLP collector |
| **Local dev** | (none of the above) | (none) | Nothing |

### Installing Telemetry Plugins

```bash
# GCP telemetry
pip install "web-endpoints-hello[gcp]"

# AWS telemetry
pip install "web-endpoints-hello[aws]"

# Azure telemetry
pip install "web-endpoints-hello[azure]"

# Generic OTLP (Honeycomb, Datadog, Jaeger, etc.)
pip install "web-endpoints-hello[observability]"
```

### Local Tracing with Jaeger

`just dev` **automatically starts Jaeger** for local trace visualization.
The Jaeger script uses **podman** if available, falling back to **docker**.
If neither is installed, podman will be installed via Homebrew (macOS) or
your system package manager (Linux). The podman machine is initialized
and started automatically on macOS.

```bash
just dev                    # installs podman → starts Jaeger → starts app
```

After startup:
- **App** → `http://localhost:8080`
- **Jaeger UI** → `http://localhost:16686` (traces appear here)
- **Genkit DevUI** → `http://localhost:4000`

**Stop everything** (app, DevUI, Jaeger):
```bash
just stop
```

If you want to run **without tracing**, use `./run.sh` directly:
```bash
./run.sh                    # app only, no Jaeger
```

**Manual Jaeger management:**
```bash
just jaeger-start     # Start Jaeger container
just jaeger-stop      # Stop Jaeger container
just jaeger-status    # Show Jaeger ports and status
just jaeger-open      # Open Jaeger UI in browser
just jaeger-logs      # Tail Jaeger container logs
```

### Disabling Telemetry

Telemetry can be disabled entirely via either:

```bash
# Environment variable
export GENKIT_TELEMETRY_DISABLED=1
python -m src

# CLI flag
python -m src --no-telemetry

# Via run.sh
./run.sh --no-telemetry
```

## Using as a Template

This sample is designed to be self-contained. To use it as a starting point:

```bash
cp -r web-endpoints-hello my-project
cd my-project
```

### Eject from the monorepo (automated)

The included `scripts/eject.sh` handles all the isolation steps automatically:

```bash
# Auto-detect genkit version from monorepo and apply all changes:
./scripts/eject.sh

# Pin to a specific version and rename the project:
./scripts/eject.sh --version 0.5.0 --name my-project

# Preview what would change without modifying files:
./scripts/eject.sh --dry-run
```

The script performs these steps:

1. **Pins genkit dependencies** — adds `>=X.Y.Z` to all `genkit*` entries in
   `pyproject.toml` (inside the monorepo they resolve via `[tool.uv.sources]`
   in the parent workspace; outside they must come from PyPI)
2. **Updates CI workflows** — changes `working-directory` from the monorepo
   path (`py/samples/web-endpoints-hello`) to `.` in all `.github/workflows/*.yml`
3. **Renames the project** (optional, via `--name`) — updates the `name` field
   in `pyproject.toml`
4. **Regenerates the lockfile** — deletes the stale workspace `uv.lock` and
   runs `uv lock` to produce a standalone one

### Customize and run

```bash
# Update pyproject.toml with your project name
# Update the Genkit flows in src/flows.py
# Update schemas in src/schemas.py
# Update routes in src/frameworks/fastapi_app.py or litestar_app.py
# Update protos/genkit_sample.proto and regenerate stubs:
#   ./scripts/generate_proto.sh

# Install dependencies and run
uv sync
./run.sh
```

All dependencies are declared in `pyproject.toml` — no external imports
from the genkit repo are required.

### Additional notes

| Item | Detail |
|------|--------|
| **`run.sh` watches `../../packages` and `../../plugins`** | No action needed — the script guards with `[[ -d ... ]]` and skips missing dirs |
| **`just lint` optional tools** | Some tools (`addlicense`, `shellcheck`) are optional and skipped with a warning if not installed. Install them for full parity: `go install github.com/google/addlicense@latest`, `brew install shellcheck` |
| **Dev tools (`pysentry-rs`, `liccheck`, `ty`, etc.)** | Run `uv sync --extra dev` after copying — these are in `[project.optional-dependencies].dev` |
| **`liccheck` authorized packages** | Review `[tool.liccheck.authorized_packages]` in `pyproject.toml` — transitive deps may differ with newer versions |

## Performance & Resilience

Production LLM services face unique challenges: expensive API calls,
unpredictable latency, and bursty traffic. This sample includes four
production-hardening features that address common deployment issues.

### Response cache (`src/cache.py`)

An in-memory TTL + LRU cache for idempotent flows (translate, describe-image,
generate-character, generate-code, review-code). Identical inputs return
cached results without making another LLM API call.

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| `cache_enabled` | `CACHE_ENABLED` | `true` | Enable/disable caching |
| `cache_ttl` | `CACHE_TTL` | `300` | Time-to-live in seconds |
| `cache_max_size` | `CACHE_MAX_SIZE` | `1024` | Maximum cached entries (LRU eviction) |

Non-idempotent flows (tell-joke, pirate-chat) and streaming flows
(tell-story) are not cached.

### Circuit breaker (`src/circuit_breaker.py`)

Protects against cascading failures when the LLM API is degraded. After
`CB_FAILURE_THRESHOLD` consecutive failures, the circuit opens and
subsequent calls fail immediately with 503 instead of blocking workers.

```
CLOSED ──[failures >= threshold]──► OPEN
  ▲                                   │
  │                              [recovery_timeout]
  │                                   │
  └───[probe succeeds]─── HALF_OPEN ◄─┘
```

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| `cb_enabled` | `CB_ENABLED` | `true` | Enable/disable circuit breaker |
| `cb_failure_threshold` | `CB_FAILURE_THRESHOLD` | `5` | Failures before opening |
| `cb_recovery_timeout` | `CB_RECOVERY_TIMEOUT` | `30` | Seconds before half-open probe |

### Connection tuning (`src/connection.py`)

Configures keep-alive timeouts and connection pool sizes for outbound
HTTP clients (LLM API calls) and inbound ASGI servers.

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| `llm_timeout` | `LLM_TIMEOUT` | `120000` | LLM API timeout (ms) |
| `keep_alive_timeout` | `KEEP_ALIVE_TIMEOUT` | `75` | Server keep-alive (s) — must exceed LB idle timeout |
| — | `HTTPX_POOL_MAX` | `100` | Max outbound connections |
| — | `HTTPX_POOL_MAX_KEEPALIVE` | `20` | Max idle keep-alive connections |

The server keep-alive (75s) is set above the typical load balancer idle
timeout (60s for Cloud Run, ALB, Azure Front Door) to prevent sporadic
502 errors.

### Multi-worker production (`gunicorn.conf.py`)

For multi-core production deployments, use gunicorn with UvicornWorker:

```bash
# Multi-worker REST server (use `just prod` as shortcut)
gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'

# Override worker count
WEB_CONCURRENCY=4 gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'
```

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Workers | `WEB_CONCURRENCY` | `(CPU * 2) + 1` | Worker processes (capped at 12) |
| Timeout | `WORKER_TIMEOUT` | `120` | Kill hung workers after N seconds |
| Keep-alive | `KEEP_ALIVE` | `75` | Server keep-alive timeout |
| Max requests | `MAX_REQUESTS` | `10000` | Recycle workers to prevent memory leaks |

For local development, continue using `python -m src` (or `just dev`) which
runs a single-process server with the gRPC server and Genkit DevUI.

## Security & Hardening

This sample follows a **secure-by-default** philosophy: every default is
chosen so that a fresh deployment with zero configuration is locked down.
Development convenience (Swagger UI, open CORS, colored logs, gRPC
reflection) requires explicit opt-in via `--debug` or `DEBUG=true`.

All security features work identically across FastAPI, Litestar, Quart,
and the gRPC server. See [`docs/production/security.md`](docs/production/security.md)
for the full engineering reference.

### Secure-by-default design

| Principle | Implementation |
|-----------|---------------|
| **Locked down on deploy** | All defaults are restrictive; dev convenience is opt-in |
| **Debug mode is explicit** | `--debug` / `DEBUG=true` enables Swagger UI, gRPC reflection, relaxed CSP, open CORS |
| **Defense in depth** | Multiple independent layers (CSP, CORS, rate limit, body size, input validation, trusted hosts) |
| **Framework-agnostic** | All middleware is pure ASGI — works with any framework |

### Debug mode

A single flag controls all development-only features:

| Feature | `debug=false` (production) | `debug=true` (development) |
|---------|---------------------------|---------------------------|
| Swagger UI (`/docs`, `/redoc`) | Disabled | Enabled |
| OpenAPI schema (`/openapi.json`) | Disabled | Enabled |
| gRPC reflection | Disabled | Enabled |
| Content-Security-Policy | `default-src none` (strict) | Allows CDN resources for Swagger UI |
| CORS (when unconfigured) | Same-origin only | Wildcard (`*`) |
| Log format (when unconfigured) | `json` (structured) | `console` (colored) |
| Trusted hosts warning | Logs a warning | Suppressed |

Activate: `--debug` CLI flag, `DEBUG=true` env var, or via `run.sh`
(which passes `--debug` automatically).

### ASGI middleware stack

Security middleware is applied as pure ASGI wrappers in
`apply_security_middleware()`. The request-flow order is:

```
AccessLog → GZip → CORS → TrustedHost → Timeout → MaxBodySize
  → ExceptionHandler → SecurityHeaders → RequestId → App
```

### Security headers (OWASP)

`SecurityHeadersMiddleware` uses the [`secure`](https://secure.readthedocs.io/)
library to inject OWASP-recommended headers on every HTTP response:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src none` | Block all resource loading (API-only server) |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Block clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Restrict browser APIs |
| `Cross-Origin-Opener-Policy` | `same-origin` | Isolate browsing context |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS only (conditional on HTTPS) |

> `X-XSS-Protection` is intentionally omitted — the browser XSS auditor
> it controlled has been removed from all modern browsers, and setting it
> can introduce XSS in older browsers (OWASP recommendation since 2023).

### CORS

| Scenario | `CORS_ALLOWED_ORIGINS` | Behavior |
|----------|----------------------|----------|
| Production (default) | `""` (empty) | Same-origin only — cross-origin requests are denied |
| Production (explicit) | `"https://app.example.com"` | Only listed origins are allowed |
| Development (`debug=true`) | `""` (empty) | Falls back to `*` (wildcard) |

Allowed methods: `GET`, `POST`, `OPTIONS`. Allowed headers:
`Content-Type`, `Authorization`, `X-Request-ID`. Credentials: disabled.

### Rate limiting

Token-bucket rate limiting applied per client IP at both layers:

| Protocol | Component | Over-limit response |
|----------|-----------|-------------------|
| REST | `RateLimitMiddleware` | `429 Too Many Requests` + `Retry-After` header |
| gRPC | `GrpcRateLimitInterceptor` | `RESOURCE_EXHAUSTED` |

Health endpoints (`/health`, `/healthz`, `/ready`, `/readyz`) are exempt.

```bash
RATE_LIMIT_DEFAULT=100/minute   # Override: 100 requests per minute per IP
```

### Request body size limit

`MaxBodySizeMiddleware` rejects requests whose `Content-Length` exceeds
`MAX_BODY_SIZE` (default: 1 MB) with `413 Payload Too Large`. The gRPC
server applies the same limit via `grpc.max_receive_message_length`.

### Request ID / correlation

`RequestIdMiddleware` assigns a unique `X-Request-ID` to every HTTP
request. If the client sends one, it is reused; otherwise a UUID4 is
generated. The ID is:

1. Bound to structlog context — every log line includes `request_id`
2. Echoed in the `X-Request-ID` response header for client-side correlation
3. Stored in `scope["state"]["request_id"]` for framework access

### Trusted host validation

When `TRUSTED_HOSTS` is set, Starlette's `TrustedHostMiddleware` rejects
requests with spoofed `Host` headers (returns 400). If unset, a warning
is logged at startup in production mode.

```bash
TRUSTED_HOSTS=api.example.com,localhost
```

### Input validation (Pydantic constraints)

All input models in `src/schemas.py` include `Field` constraints that
reject malformed input before it reaches any flow:

| Constraint | Example | Models |
|-----------|---------|--------|
| `max_length` | Name ≤ 200, text ≤ 10,000, code ≤ 50,000 | All string inputs |
| `min_length` | Text ≥ 1 (no empty strings) | `text`, `code`, `description`, `question` |
| `ge` / `le` | 0 ≤ skill ≤ 100 | `Skills.strength`, `.charisma`, `.endurance` |
| `pattern` | `^[a-zA-Z#+]+$` | `CodeInput.language` (prevent injection) |

### Circuit breaker

Async-safe circuit breaker for LLM API calls. Prevents cascading failures
by failing fast when the upstream API is degraded.

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Enabled | `CB_ENABLED` | `true` | Enable/disable circuit breaker |
| Failure threshold | `CB_FAILURE_THRESHOLD` | `5` | Consecutive failures to open |
| Recovery timeout | `CB_RECOVERY_TIMEOUT` | `30.0` | Seconds before half-open probe |

Uses `time.monotonic()` for NTP-immune timing.

### Response cache (stampede protection)

In-memory TTL + LRU cache for idempotent flows with per-key request
coalescing to prevent cache stampedes (thundering herd).

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Enabled | `CACHE_ENABLED` | `true` | Enable/disable caching |
| TTL | `CACHE_TTL` | `300` | Time-to-live in seconds |
| Max entries | `CACHE_MAX_SIZE` | `1024` | LRU eviction after this count |

Uses SHA-256 hashed cache keys and `asyncio.Lock` per key for coalescing.

### Connection tuning

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| Keep-alive | `KEEP_ALIVE_TIMEOUT` | `75` | Above typical 60s LB idle timeout |
| LLM timeout | `LLM_TIMEOUT` | `120000` | 2-minute timeout for LLM API calls |
| Pool max | `HTTPX_POOL_MAX` | `100` | Max outbound connections |
| Pool keepalive | `HTTPX_POOL_MAX_KEEPALIVE` | `20` | Max idle connections |

### Graceful shutdown

SIGTERM is handled with a configurable grace period (default: 10s,
matching Cloud Run). In-flight REST requests and gRPC RPCs are drained
before the process exits.

### gRPC interceptors

The gRPC server applies interceptors in this order:

1. **GrpcLoggingInterceptor** — logs every RPC with method, duration, status
2. **GrpcRateLimitInterceptor** — token-bucket per peer (same as REST)
3. **Max message size** — `grpc.max_receive_message_length` = 1 MB
4. **Reflection** — debug-only (exposes API schema; disabled in production)

### Structured logging

| Mode | `LOG_FORMAT` | Description |
|------|-------------|-------------|
| Production (default) | `json` | Structured, machine-parseable, no ANSI codes |
| Development | `console` | Colored, human-friendly (set in `local.env`) |

All log entries include `request_id` from `RequestIdMiddleware`.

### Sentry error tracking (optional)

Set `SENTRY_DSN` to enable. PII is stripped (`send_default_pii=False`).
The SDK auto-detects the active framework (FastAPI, Litestar, Quart) and
enables the matching integration plus gRPC.

### Platform telemetry auto-detection

Automatically detects cloud platform and enables tracing:

| Platform | Detection signal | Plugin |
|----------|-----------------|--------|
| GCP (Cloud Run) | `K_SERVICE` | `genkit-plugin-google-cloud` |
| GCP (GCE/GKE) | `GCE_METADATA_HOST` | `genkit-plugin-google-cloud` |
| AWS (ECS/App Runner) | `AWS_EXECUTION_ENV` | `genkit-plugin-amazon-bedrock` |
| Azure (Container Apps) | `CONTAINER_APP_NAME` | `genkit-plugin-microsoft-foundry` |
| Generic OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | `genkit-plugin-observability` |

> `GOOGLE_CLOUD_PROJECT` alone does not trigger GCP telemetry (it's
> commonly set on dev machines for gcloud CLI). Set `GENKIT_TELEMETRY_GCP=1`
> to force it.

### Dependency auditing

```bash
just audit      # pip-audit — known CVEs from PyPA advisory database
just security   # pysentry-rs + pip-audit + liccheck
just licenses   # License compliance against allowlist
just lint       # Includes all of the above
```

Allowlist: Apache-2.0, MIT, BSD-3-Clause, BSD-2-Clause, PSF-2.0, ISC,
Python-2.0, MPL-2.0.

### Distroless container

The `Containerfile` uses `gcr.io/distroless/python3-debian13:nonroot`:

- No shell, no package manager, no `setuid` binaries
- Runs as uid 65534 (nonroot)
- ~50 MB base image (vs ~150 MB for `python:3.13-slim`)

### Production hardening checklist

| Item | How | Default |
|------|-----|---------|
| Debug mode | `DEBUG=false` (default) | Off — Swagger UI, reflection, relaxed CSP all disabled |
| TLS termination | Load balancer / reverse proxy | Not included (use Cloud Run, nginx, etc.) |
| Trusted hosts | `TRUSTED_HOSTS=api.example.com` | Disabled (warns at startup) |
| CORS lockdown | `CORS_ALLOWED_ORIGINS=https://app.example.com` | Same-origin only |
| Rate limit tuning | `RATE_LIMIT_DEFAULT=100/minute` | `60/minute` |
| Body size | `MAX_BODY_SIZE=524288` | 1 MB |
| Log format | `LOG_FORMAT=json` (default) | JSON (structured) |
| Secrets | Use a secrets manager, never `.env` in production | `.env` files |
| Sentry | `SENTRY_DSN=...` | Disabled |
| Container | `Containerfile` with distroless + nonroot | Included |

### Security environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable dev-only features (Swagger, reflection, relaxed CSP) | `false` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `""` (same-origin) |
| `TRUSTED_HOSTS` | Comma-separated allowed Host headers | `""` (disabled, warns) |
| `RATE_LIMIT_DEFAULT` | Rate limit in `<count>/<period>` format | `60/minute` |
| `MAX_BODY_SIZE` | Max request body in bytes | `1048576` (1 MB) |
| `LOG_FORMAT` | `json` (production) or `console` (dev) | `json` |
| `SENTRY_DSN` | Sentry Data Source Name | `""` (disabled) |
| `SENTRY_TRACES_SAMPLE_RATE` | Fraction of transactions to sample | `0.1` |
| `SENTRY_ENVIRONMENT` | Sentry environment tag | (auto from `--env`) |
| `GENKIT_TELEMETRY_DISABLED` | Disable all platform telemetry | `""` (enabled) |

## How It Works

1. **Define tools** — `@ai.tool()` registers `get_current_time` so the model
   can call it during generation. Tools are the primary way to give models
   access to real-world data.

2. **Define flows** — `@ai.flow()` registers flows with the Genkit runtime
   (visible in DevUI, traced, replayable).

3. **Structured output** — `Output(schema=TranslationResult)` tells Gemini to
   return JSON matching the Pydantic model. No manual parsing needed.

4. **Traced steps** — `ai.run('sanitize-input', ...)` creates a sub-span
   visible in the DevUI trace viewer, making complex flows auditable.

5. **Multimodal input** — `Message` with `MediaPart` sends both text and
   images to Gemini in a single request (see `/describe-image`).

6. **System prompts** — `system=` sets the model's persona before generation
   (see `/chat` with the pirate captain).

7. **Streaming with anti-buffering** — `ai.generate_stream()` returns an
   async iterator + future. Each chunk is forwarded as an SSE event.
   Three response headers prevent buffering:

   | Header | Why |
   |--------|-----|
   | `Cache-Control: no-cache` | Prevents browser/CDN caching |
   | `Connection: keep-alive` | Keeps the HTTP connection open for SSE |
   | `X-Accel-Buffering: no` | Disables nginx proxy buffering |

8. **Framework selection** — `--framework` selects FastAPI or Litestar.
   Both frameworks use the same Genkit flows and schemas — only the HTTP
   adapter layer differs. This is done via a `create_app(ai)` factory
   pattern in `src/frameworks/`.

9. **ASGI server selection** — `--server` selects uvicorn (default),
   granian (Rust), or hypercorn. All serve any ASGI application.

10. **Cloud-ready** — The app reads `PORT` from the environment (default
    8080), making it compatible with Cloud Run, App Engine, and any
    container-based platform.

11. **gRPC server** — A parallel `grpc.aio` server exposes the same flows
    as gRPC RPCs (defined in `protos/genkit_sample.proto`). Each RPC
    method in `src/grpc_server.py` converts the protobuf request to
    a Pydantic model, calls the flow, and converts the result back.
    Server-side streaming (`TellStory`) yields `StoryChunk` messages
    as the flow streams chunks via `ctx.send_chunk()`.

12. **gRPC reflection** — The server registers with the gRPC reflection
    service, so tools like `grpcui` (web UI) and `grpcurl` (CLI) can
    discover and test all RPCs without needing the `.proto` file.

The key insight is that Genkit flows are just async functions — you can
`await` them from any framework, whether ASGI or gRPC. The framework
adapter pattern (`src/frameworks/`) and `src/grpc_server.py` are thin
wrappers around the same flow functions in `src/flows.py`.
