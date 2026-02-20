# REST Endpoints

All three REST frameworks expose identical routes — only the internal
plumbing differs. The `--framework` flag selects which adapter is used
at startup.

## Endpoint map (REST + gRPC)

| Genkit Flow | REST Endpoint | gRPC RPC | Input | Output | Feature |
|-------------|---------------|----------|-------|--------|---------|
| `tell_joke` | `POST /tell-joke` | `TellJoke` (unary) | `JokeInput` | `JokeResponse` | Basic flow |
| *(handler)* | `POST /tell-joke/stream` | — | `JokeInput` | SSE chunks | `ai.generate_stream()` |
| `tell_story` | `POST /tell-story/stream` | `TellStory` (stream) | `StoryInput` | SSE / `StoryChunk` | `flow.stream()` |
| `translate_text` | `POST /translate` | `TranslateText` (unary) | `TranslateInput` | `TranslationResult` | Structured output + tool |
| `describe_image` | `POST /describe-image` | `DescribeImage` (unary) | `ImageInput` | `ImageResponse` | Multimodal |
| `generate_character` | `POST /generate-character` | `GenerateCharacter` (unary) | `CharacterInput` | `RpgCharacter` | Structured (nested) |
| `pirate_chat` | `POST /chat` | `PirateChat` (unary) | `ChatInput` | `ChatResponse` | System prompt |
| `generate_code` | `POST /generate-code` | `GenerateCode` (unary) | `CodeInput` | `CodeOutput` | Structured output |
| `review_code` | `POST /review-code` | `ReviewCode` (unary) | `CodeReviewInput` | `CodeReviewResponse` | Dotprompt |
| *(built-in)* | `GET /health` | `Health` (unary) | — | `{status: "ok"}` | Health check |
| *(built-in)* | `GET /docs` | *(reflection)* | — | Swagger UI | API docs |

## REST routes (`:8080`)

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/tell-joke` | Generate a joke | `{"name": "Mittens"}` | `{"joke": "..."}` |
| `POST` | `/tell-joke/stream` | SSE streaming joke | `{"name": "Python"}` | `data: {"chunk": "..."}` |
| `POST` | `/tell-story/stream` | SSE streaming story | `{"topic": "a robot"}` | `data: {"chunk": "..."}` |
| `POST` | `/translate` | Structured translation | `{"text": "Hello", "target_language": "Japanese"}` | `{"translated_text": "..."}` |
| `POST` | `/describe-image` | Multimodal description | `{"image_url": "https://..."}` | `{"description": "..."}` |
| `POST` | `/generate-character` | RPG character | `{"name": "Luna"}` | `{"name": "Luna", "abilities": [...]}` |
| `POST` | `/generate-code` | Code generation | `{"description": "reverse list", "language": "python"}` | `{"code": "..."}` |
| `POST` | `/review-code` | Code review | `{"code": "def add(a,b):...", "language": "python"}` | `{"summary": "..."}` |
| `POST` | `/chat` | Pirate chat | `{"question": "Best language?"}` | `{"answer": "Arrr!..."}` |
| `GET` | `/health` | Health check | — | `{"status": "ok"}` |
| `GET` | `/docs` | API documentation | — | Swagger UI |

## Framework-specific differences

| Aspect | FastAPI | Litestar | Quart |
|--------|---------|----------|-------|
| Request body | Pydantic auto-parsed | Pydantic auto-parsed | Manual `request.get_json()` |
| Response | Return Pydantic model | Return Pydantic model | Return `.model_dump()` dict |
| SSE streaming | `StreamingResponse` | `Stream` | `Response` generator |
| Auth header | `Header(default=None)` | Via `data.username` | `request.headers.get()` |
| API docs | `/docs` (Swagger) + `/redoc` | `/schema` (explorer) | None |
| Source | `fastapi_app.py` | `litestar_app.py` | `quart_app.py` |

## How gRPC maps to REST

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
