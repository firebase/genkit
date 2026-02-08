# Dataflow

## Request lifecycle

Every request — whether REST or gRPC — follows the same path through
the Genkit runtime.

```mermaid
sequenceDiagram
    participant Client
    participant Middleware as Middleware Stack
    participant Handler as Route / RPC Handler
    participant Flow as Genkit Flow
    participant Validate as Pydantic Validation
    participant LLM as Gemini API

    Client->>Middleware: HTTP POST / gRPC call
    Middleware->>Middleware: Request ID, rate limit, security headers
    Middleware->>Handler: Forward request
    Handler->>Validate: Parse + validate input
    Validate-->>Handler: Pydantic model
    Handler->>Flow: await flow(input)
    Flow->>LLM: ai.generate(model, prompt)
    LLM-->>Flow: Response / structured JSON
    Flow-->>Handler: Output model
    Handler-->>Client: JSON / Protobuf response
```

### ASCII variant

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

## Streaming dataflow

The sample supports two streaming patterns — handler-level streaming
with `ai.generate_stream()` and flow-level streaming with `flow.stream()`.

### REST SSE streaming

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant Genkit
    participant Gemini

    Client->>Handler: POST /tell-joke/stream
    Handler->>Genkit: ai.generate_stream()
    Genkit->>Gemini: Streaming request

    loop For each chunk
        Gemini-->>Genkit: chunk.text
        Genkit-->>Handler: yield chunk
        Handler-->>Client: data: {"chunk": "..."}
    end

    Gemini-->>Genkit: Final response
    Genkit-->>Handler: complete
    Handler-->>Client: data: {"done": true, "joke": "..."}
```

### Flow-level streaming (tell-story)

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant Flow as tell_story flow
    participant Ctx as ctx.send_chunk()

    Client->>Handler: POST /tell-story/stream
    Handler->>Flow: tell_story.stream(input)

    loop For each paragraph
        Flow->>Ctx: ctx.send_chunk(text)
        Ctx-->>Handler: yield chunk
        Handler-->>Client: data: {"chunk": "..."}
    end

    Flow-->>Handler: final result
    Handler-->>Client: data: {"done": true, "story": "..."}
```

### gRPC server streaming

```mermaid
sequenceDiagram
    participant Client
    participant Servicer as GenkitServiceServicer
    participant Flow as tell_story flow

    Client->>Servicer: TellStory(StoryRequest)
    Servicer->>Flow: tell_story.stream(input)

    loop For each chunk
        Flow-->>Servicer: chunk text
        Servicer-->>Client: StoryChunk{text}
    end

    Servicer->>Servicer: await future
    Note over Client,Servicer: Stream ends
```

### ASCII variant

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

## Telemetry dataflow

```mermaid
graph LR
    REQ["Request"] --> OTEL_MW["ASGI Middleware<br/>Creates root span"]
    OTEL_MW --> FLOW_SPAN["Genkit Flow<br/>Child span"]
    FLOW_SPAN --> SUB_SPAN["ai.run() / ai.generate()<br/>Child spans"]
    SUB_SPAN --> EXPORTER["OTLP Exporter<br/>(HTTP or gRPC)"]
    EXPORTER --> BACKEND["Jaeger / Cloud Trace<br/>X-Ray / App Insights"]

    subgraph AUTO_DETECT["Auto-detection (app_init.py)"]
        K_SVC{"K_SERVICE?"} -->|yes| GCP["GCP Cloud Trace"]
        AWS{"AWS_EXEC?"} -->|yes| XRAY["AWS X-Ray"]
        AZ{"CONTAINER_APP?"} -->|yes| INSIGHTS["Azure App Insights"]
        OTLP_EP{"OTLP_ENDPOINT?"} -->|yes| GENERIC["Generic OTLP"]
    end
```

### ASCII variant

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

## Circuit breaker state machine

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open : failures >= threshold
    Open --> HalfOpen : recovery_timeout elapsed
    HalfOpen --> Closed : probe succeeds
    HalfOpen --> Open : probe fails
```

```
CLOSED ──[failures >= threshold]──► OPEN
  ▲                                   │
  │                              [recovery_timeout]
  │                                   │
  └───[probe succeeds]─── HALF_OPEN ◄─┘
```
