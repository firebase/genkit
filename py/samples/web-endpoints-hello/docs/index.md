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

!!! tip "Template-ready"
    This sample is designed to be self-contained and copyable as a template
    for your own Genkit projects. See [Using as a Template](guides/template.md).

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

## Quick Start

```bash
./setup.sh              # Install tools + dependencies
export GEMINI_API_KEY=<your-key>
./run.sh                # Start REST + gRPC servers
```

Then open:

- **Swagger UI** → [http://localhost:8080/docs](http://localhost:8080/docs)
- **gRPC UI** → `just grpcui`
- **Genkit DevUI** → [http://localhost:4000](http://localhost:4000)

## Project Layout

```
web-endpoints-hello/
├── src/                    # Application source code
│   ├── flows.py            # Genkit AI flows (@ai.flow, @ai.tool)
│   ├── schemas.py          # Pydantic input/output models
│   ├── frameworks/         # REST adapters (FastAPI, Litestar, Quart)
│   ├── grpc_server.py      # gRPC service implementation
│   └── ...                 # Config, security, telemetry, etc.
├── tests/                  # Unit and integration tests
├── protos/                 # gRPC .proto definitions
├── docs/                   # This documentation (MkDocs)
├── .github/workflows/      # CI/CD pipelines
├── justfile                # Task runner commands
├── Containerfile           # Distroless container build
└── deploy_*.sh             # Platform deployment scripts
```
