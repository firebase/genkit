# Genkit 1.0 API Review (Python)

The Python surface we intend to ship as 1.0. It describes the state after the open API PRs land (#6697, #6698, #6699, #6709, #6757, #6764–#6770, #6775, #6777, #6314, #6655), not `main` today. Snippets show the intended usage; they're not run in CI.

---

## 1. Public API Surface

```python
from genkit import (
    # The app object; every ai.* call goes through it.
    Genkit,
    # What you send a model.
    Message, Role, Part, Media, Document, ToolChoice,
    # What comes back; Failure is the error on a failed turn.
    ModelResponse, ModelResponseChunk, ModelStreamResponse, StreamResponse, FinishReason, Failure,
    # Results of ai.embed and background models.
    Embedding, Operation,
    # Flows, tools, prompts, and human-in-the-loop.
    Flow, FlowContext, Tool, ToolContext, Interrupt, MultipartToolResponse, Prompt,
    # Errors: GenkitError is internal, PublicError is safe to show clients.
    GenkitError, PublicError, ErrorReason,
)

from genkit.model import (
    # Defining a model, and the ctx its fn receives.
    Model, BackgroundModel, ModelContext,
    # Typed handle to a model and its config base class.
    ModelRef, ModelConfig,
    # The request a model fn receives.
    ModelRequest, GenerateActionOptions, OutputConfig, ToolDefinition, ToolRequest, ToolResponse,
    # What a model declares it supports, and token accounting.
    ModelInfo, ModelSupports, ConstrainedSupport, ModelStage, GenerationUsage,
)

from genkit.embedder import (
    # Defining an embedder and its handle.
    Embedder, EmbedderRef, EmbedderInfo, EmbedderSupports,
    # Embed request and response.
    EmbedRequest, EmbedResponse,
)

from genkit.evaluator import (
    # Defining an evaluator: per data point or batch.
    Evaluator, BatchEvaluator, EvaluatorRef,
    # Evaluator input and scored output.
    EvaluatorRequest, EvaluatorResponse, BaseDataPoint, Score, ScoreDetails, ScoreStatus,
)

from genkit.middleware import (
    # Subclass Middleware, override wrap_generate / wrap_model / wrap_tool, register with @ai.middleware.
    Middleware, MiddlewareContext, GenerateHookParams, ModelHookParams, ToolHookParams,
)

from genkit.formats import (
    # Custom output formats (JS/Go names).
    Formatter, FormatterConfig, FormatHandler,
)

from genkit.web import (
    # Building blocks for serving flows over HTTP; error_body/error_status redact non-public errors.
    RequestData, read_body, wants_stream, error_body, error_status,
)

from genkit.telemetry import (
    # OpenTelemetry wiring and custom spans.
    Instrumentation, DisposableInstrumentation, FlushableInstrumentation,
    SpanContext, SpanMetadata, SpanNext,
    configure_instrumentation, run_in_new_span, is_instrumented_by, reset_instrumentation,
)

from genkit.testing import (
    # Fake models for unit tests.
    EchoModel, ScriptedModel, StaticResponseModel,
    define_echo_model, define_scripted_model, define_static_response_model,
)

from genkit.plugin_api import (
    # What plugin authors build on.
    Plugin, Action, ActionKind, DynamicActionProvider, GenkitConfig,
    # Helpers for provider plugins.
    StatusName, StrEnum, provider_error, get_logger, loop_local_client, GENKIT_USER_AGENT, is_dev_environment,
)

from genkit.exp import (
    # Experimental: agents and sessions (genkit.exp.agent adds AgentContext for custom agent fns).
    Genkit, current_session,
)

from genkit_google_genai import (
    # Plugins; refs come from classmethods: GoogleAI.gemini('gemini-flash-latest') -> ModelRef[GeminiConfig].
    GoogleAI, VertexAI,
    # One flat config class per model family.
    GeminiConfig, GeminiImageConfig, GeminiTtsConfig, GemmaConfig, VeoConfig, LyriaConfig,
    DeepResearchConfig, AntigravityConfig,
    # Literal and nested types used inside those configs.
    ThinkingLevel, SafetySetting, HarmCategory, HarmBlockThreshold, HarmBlockMethod, ResponseModality, ...,
)

from genkit_anthropic import (
    # Plugin; Anthropic.claude('claude-sonnet-4-5') -> ModelRef[AnthropicConfig]; tool choice comes from generate(tool_choice=).
    Anthropic, AnthropicConfig, Effort, ThinkingDisplay, ThinkingMode,
)
```

---

## 2. Model Generation (`ai.generate`)

### Structured Output with Pydantic

Models enforce structured output through JSON schema constraints, parsed directly into Pydantic models.

```python
from pydantic import BaseModel, Field
from genkit import Genkit
from genkit_google_genai import GoogleAI

# 1. Initialize runtime with a default model ref
ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini('gemini-flash-latest'))

class InventoryItem(BaseModel):
    sku: str = Field(description='Stock keeping unit identifier')
    quantity: int = Field(description='Quantity available in warehouse')
    reorder_recommended: bool

# 2. Run generation constrained by schema
response = await ai.generate(
    prompt='Warehouse audit: 4 units remaining for SKU-5821.',
    output_schema=InventoryItem,
)

# 3. Access validated Pydantic model
item = response.output
print(f'{item.sku}: {item.quantity} units (Reorder: {item.reorder_recommended})')
# => SKU-5821: 4 units (Reorder: True)
```

### Reading Message Parts

A `Message` is a role plus a list of `Part`s. A `Part` is flat: exactly one of `text`, `media`, `tool_request`, `tool_response`, `data`, `reasoning`, or `resource` is set, plus optional `metadata`. Setting a second kind raises.

#### Shortcuts

```python
from genkit_google_genai import GeminiImageConfig, GoogleAI

response = await ai.generate(
    model=GoogleAI.gemini_image('gemini-2.5-flash-image'),
    prompt='Plate photo for the spring menu, then describe it in one line.',
    config=GeminiImageConfig(response_modalities=['TEXT', 'IMAGE']),
)

# 1. Visible text only; reasoning parts are excluded
print(response.text)
# => Seared scallops over pea purée, finished with mint oil.

# 2. Every media part on the reply
for media in response.media:
    print(media.content_type, media.url[:30])
    # => image/png data:image/png;base64,iVBORw0K

# 3. The raw parts: one image, one text
print(len(response.message.content))
# => 2
```

#### Every part, by kind

```python
for part in response.message.content:
    if part.text is not None:
        print('text:', part.text)
        # => text: Seared scallops over pea purée, finished with mint oil.
    elif part.media is not None:
        save_image(part.media.url, part.media.content_type)
    elif part.reasoning is not None:
        print('thinking:', part.reasoning)
    elif part.tool_request is not None:
        print('tool call:', part.tool_request.name, part.tool_request.input)
    elif part.data is not None:
        print('data:', part.data)
```

#### Walking the whole conversation

`response.messages` is the request history plus the reply. After a tool loop it includes each tool call and its result, matched by `ref`.

```python
response = await ai.generate(prompt='Is ORD-9921 delivered?', tools=[lookup_order])

for message in response.messages:
    for part in message.content:
        if part.tool_request:
            print(f'{message.role}: call {part.tool_request.name}({part.tool_request.input}) ref={part.tool_request.ref}')
        elif part.tool_response:
            print(f'{message.role}: result {part.tool_response.output} ref={part.tool_response.ref}')
        elif part.text:
            print(f'{message.role}: {part.text}')
# => user: Is ORD-9921 delivered?
# => model: call lookup_order(ORD-9921) ref=0
# => tool: result ORD-9921: delivered 14:02 ref=0
# => model: Yes, it was delivered at 14:02.
```

### Streaming Responses

Streaming yields incremental text chunks while resolving final token usage upon completion.

```python
# 1. Initiate async streaming generator
stream = ai.generate_stream(
    prompt='Draft a release notice for maintenance on Sunday at 02:00 UTC.',
)

# 2. Consume chunks as they arrive
async for chunk in stream.stream:
    print(chunk.text, end='', flush=True)
    # => Scheduled Maintenance: Systems will be offline Sunday at 02:00 UTC.

# 3. Await final aggregated response
response = await stream.response
print(f'\nTotal tokens: {response.usage.total_tokens}')
# => Total tokens: 34
```

### Streaming Tool Chunks

A tool declares its chunk type with `ToolContext[ChunkT]`, separate from its return type. The same tool streams two ways.

#### Inside `generate_stream()`: partial tool responses

Each `ctx.send_chunk()` arrives on the generate stream as a partial tool response (`part.is_partial`). Partial parts stay out of `response.messages`, so the model never sees mid-run progress on the next turn.

```python
from pydantic import BaseModel
from genkit import ToolContext

class DeployInput(BaseModel):
    service: str

class DeployStep(BaseModel):
    step: str
    percent: int

class Rollout(BaseModel):
    url: str
    revision: str

# 1. Tool streams DeployStep chunks and returns a Rollout
@ai.tool
async def deploy_service(input: DeployInput, ctx: ToolContext[DeployStep]) -> Rollout:
    ctx.send_chunk(DeployStep(step='building image', percent=25))
    ctx.send_chunk(DeployStep(step='pushing layers', percent=75))
    return Rollout(url=f'https://{input.service}.run.app', revision='rev-0042')

# 2. Model calls the tool; partial chunks arrive live, then the final return
stream = ai.generate_stream(prompt='Deploy payments', tools=[deploy_service])
async for chunk in stream.stream:
    for part in chunk.tool_responses:
        tr = part.tool_response
        if part.is_partial:
            print(f'[{tr.name}] progress: {tr.output}')
            # => [deploy_service] progress: step='building image' percent=25
            # => [deploy_service] progress: step='pushing layers' percent=75
        else:
            print(f'[{tr.name}] done: {tr.output}')
            # => [deploy_service] done: url='https://payments.run.app' revision='rev-0042'
    if chunk.text:
        print(chunk.text, end='')

# 3. History holds the final Rollout only
response = await stream.response
```

#### Direct: `tool.stream()`

Called without a model, the tool is a `StreamResponse[DeployStep, Rollout]`. Chunks are typed `DeployStep`; the response is the `Rollout` itself, same as `await deploy_service(...)`.

```python
# 1. Stream the tool directly
stream = deploy_service.stream(DeployInput(service='payments'))

# 2. Chunks are DeployStep
async for step in stream.stream:
    print(f'{step.step} ({step.percent}%)')
    # => building image (25%)
    # => pushing layers (75%)

# 3. Response is Rollout, not a tool-response envelope
rollout = await stream.response
print(rollout.url)
# => https://payments.run.app
```

### Interrupts (human-in-the-loop)

A tool raises `Interrupt(metadata)` to pause the turn. `generate` returns with `finish_reason == INTERRUPTED`, and the paused tool calls are on `response.interrupts`. You resume by passing the history back with one of two answers:

- **`part.restart(...)`:** run the tool again, e.g. after approval. The tool sees `ctx.is_resumed()` and `ctx.resumed_metadata`.
- **`part.respond(output)`:** answer for the tool without running it.

`Interrupt` subclasses `BaseException`, so an `except Exception` inside a tool can't swallow it and skip approval.

#### Approve, then re-run

```python
from genkit import FinishReason, Interrupt, ToolContext

# 1. Refunds over $100 pause for a manager
@ai.tool
async def issue_refund(order_id: str, amount: float, ctx: ToolContext) -> str:
    if amount > 100 and not ctx.is_resumed():
        raise Interrupt({'reason': 'needs_manager', 'amount': amount})
    approver = (ctx.resumed_metadata or {}).get('approved_by', 'auto')
    return f'refunded ${amount} on {order_id} (approved by {approver})'

response = await ai.generate(prompt='Refund $240 on ORD-9921.', tools=[issue_refund])

# 2. The turn pauses; nothing was refunded
print(response.finish_reason)
# => FinishReason.INTERRUPTED
paused = response.interrupts[0]
print(paused.tool_request.name, paused.metadata['interrupt'])
# => issue_refund {'reason': 'needs_manager', 'amount': 240.0}

# 3. Manager approves; re-run the same call with the approval attached
response = await ai.generate(
    messages=response.messages,
    tools=[issue_refund],
    resume_restart=[paused.restart(resumed_metadata={'approved_by': 'dana'})],
)
print(response.text)
# => Done: refunded $240.00 on ORD-9921, approved by dana.
```

#### Answer for the tool

```python
from pydantic import BaseModel

class Question(BaseModel):
    question: str
    choices: list[str]

# 1. An interrupt-only tool: always pauses, the user's answer is its output
ask_guest = ai.define_interrupt('ask_guest', input_schema=Question, description='Ask the guest to choose.')

response = await ai.generate(prompt='Book a table for 4 tonight.', tools=[ask_guest])
paused = response.interrupts[0]
print(paused.tool_request.input)
# => {'question': 'Which time works?', 'choices': ['18:30', '20:45']}

# 2. Reply with the guest's choice; the tool never runs
response = await ai.generate(
    messages=response.messages,
    tools=[ask_guest],
    resume_respond=[paused.respond('20:45')],
)
print(response.text)
# => Booked a table for 4 at 20:45.
```

### Provider Configuration & ModelRef

Refs come from plugin classmethods and carry their config class. `GeminiConfig` is flat: `temperature` sits next to `thinking_level`.

```python
from genkit_google_genai import GeminiConfig, GoogleAI

# 1. Typed ref: config is checked as GeminiConfig at the call site
analyst = GoogleAI.gemini('gemini-flash-latest')

# 2. Flat config: common and Gemini-only fields side by side
response = await ai.generate(
    model=analyst,
    prompt='Analyze customer churn indicators in financial records.',
    config=GeminiConfig(
        temperature=0.2,
        max_output_tokens=2048,
        thinking_level='high',
        safety_settings=[
            {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_LOW_AND_ABOVE'},
        ],
    ),
)

print(response.text)
# => Key churn indicators identified: payment failure frequency and login recency drop.
```

### Background Models

For jobs that outlive a request (video, deep research), a background model splits into `start` and `check` (plus optional `cancel`). `start` returns an `Operation` handle and `check` polls it. All three get a `ModelContext`; on these functions it's for `ctx.context` (per-request secrets, auth) and `ctx.abort_signal`, not for streaming.

```python
from genkit import Operation
from genkit.model import ModelContext, ModelRequest

# 1. start submits the job and returns a handle
async def start_render(request: ModelRequest, ctx: ModelContext) -> Operation:
    job_id = await render_api.submit(prompt=request.messages[-1].text, key=ctx.context['secrets']['api_key'])
    return Operation(id=job_id, done=False)

# 2. check polls the job; output is set once done
async def check_render(op: Operation, ctx: ModelContext) -> Operation:
    job = await render_api.status(op.id, key=ctx.context['secrets']['api_key'])
    op.done = job.done
    if job.done:
        op.output = {'video_url': job.url}
    return op

ai.define_background_model('acme/promo-video', start=start_render, check=check_render)

# 3. Caller starts the job; no tool loop, no output parsing
secrets = {'secrets': {'api_key': RENDER_KEY}}
op = await ai.generate_operation(model='acme/promo-video', prompt='15s promo for the spring menu', context=secrets)
print(op.id, op.done)
# => job_7f3a False

# 4. Poll until done; pass the same context again
while not op.done:
    await asyncio.sleep(5)
    op = await ai.check_operation(op, context=secrets)
print(op.output)
# => {'video_url': 'https://cdn.acme.dev/job_7f3a.mp4'}
```

Plugins build the same thing with `BackgroundModel(name, start=..., check=...)` and return it from `list_actions()`. Gemini's Veo comes back from `GoogleAI.veo('veo-3.0-generate-001')`.

---

## 3. Mid-Turn Error Recovery

A tool that fails partway through a multi-step turn doesn't throw away the work before it. `ai.generate` returns a response with `finish_reason == FAILED` and the error on `response.error`. `response.messages` holds the history up to the last completed step; the unanswered tool call is dropped. Pass that history back to pick up where it stopped.

Setup problems (bad config, unknown model) still raise `GenkitError` before the turn starts.

```python
from genkit import FinishReason, GenkitError

@ai.tool
async def lookup_order(order_id: str) -> str:
    return f'{order_id}: 2x pad thai, paid $31.50'

@ai.tool
async def issue_refund(order_id: str) -> str:
    return await payments.refund(order_id)  # first call times out, retry succeeds

try:
    # 1. lookup_order succeeds, then issue_refund fails
    response = await ai.generate(
        prompt='Refund order ORD-9921.',
        tools=[lookup_order, issue_refund],
    )

    if response.finish_reason == FinishReason.FAILED:
        print(response.error.message)
        # => payments API timed out after 10s

        # 2. History up to the failure is intact: the lookup isn't lost
        print([m.role for m in response.messages])
        # => ['user', 'model', 'tool']

        # 3. Restart from that history; the model doesn't redo the lookup
        response = await ai.generate(
            messages=response.messages,
            tools=[lookup_order, issue_refund],
        )

    print(response.text)
    # => Refunded $31.50 for ORD-9921.

except GenkitError as e:
    # Raised before the turn: bad config, unknown model, etc.
    print(e.status, e.message)
```

---

## 4. Flows (`ai.flow`)

### Structured Input & Output

Flows encapsulate typed boundaries using Pydantic models for inputs and outputs.

```python
from pydantic import BaseModel
from genkit import Genkit, FlowContext

ai = Genkit()

class ClaimRequest(BaseModel):
    claim_id: str
    amount: float
    description: str

class ClaimDecision(BaseModel):
    approved: bool
    review_required: bool
    notes: str

# 1. Define flow with typed boundaries
@ai.flow
async def evaluate_claim(request: ClaimRequest) -> ClaimDecision:
    # 2. Invoke generation within flow span
    res = await ai.generate(
        prompt=f'Evaluate claim {request.claim_id} for ${request.amount}: {request.description}',
        output_schema=ClaimDecision,
    )
    return res.output
```

### Streaming Flow Responses

The chunk type comes from the `FlowContext[ChunkT]` annotation, so `send_chunk` and the caller's `async for` are both typed.

```python
from typing import Literal
from pydantic import BaseModel
from genkit import FlowContext

class ReportChunk(BaseModel):
    stage: Literal['fetching', 'drafting', 'done']
    text: str

class Report(BaseModel):
    quarter: str
    summary: str

# 1. Flow typed as Flow[str, Report, ReportChunk]
@ai.flow
async def quarterly_report(quarter: str, ctx: FlowContext[ReportChunk]) -> Report:
    ctx.send_chunk(ReportChunk(stage='fetching', text=f'Pulling {quarter} ledger'))

    # 2. Forward model tokens as typed chunks
    summary = ''
    stream = ai.generate_stream(prompt=f'Draft the {quarter} executive summary.')
    async for chunk in stream.stream:
        summary += chunk.text
        ctx.send_chunk(ReportChunk(stage='drafting', text=chunk.text))

    ctx.send_chunk(ReportChunk(stage='done', text=''))
    return Report(quarter=quarter, summary=summary)

# 3. Caller: chunks are ReportChunk, response is Report
stream = quarterly_report.stream('Q3')
async for chunk in stream:
    print(chunk.stage, chunk.text)
    # => fetching Pulling Q3 ledger
    # => drafting Revenue grew 12%
    # => drafting  quarter over quarter...
    # => done

report = await stream.response
print(report.quarter, report.summary)
# => Q3 Revenue grew 12% quarter over quarter...
```

### Tradeoffs Around Streamed Chunks

* **Typed vs. Raw Chunks**: Emitting Pydantic models provides strict schema guarantees on every frame, but incurs serialization overhead per token. Emitting raw strings minimizes event loop latency and payload size, leaving client-side parsing to the consumer.
* **Accumulator Latency vs. Time-to-First-Token (TTFT)**: Immediate byte dispatch reduces TTFT for chat clients. However, buffering small chunks into line/word boundaries reduces network packet overhead and CPU load on mobile receivers.
* **Flow Resumability & State**: Genkit records state at tool and action boundaries, not at intermediate chunk emissions. If a flow fails mid-stream, resuming execution begins from the last recorded durable step rather than mid-chunk stream.

---

## 5. Web Serving (`genkit.web`) & Error Redaction

Four levels of control. Each level down gives you more of the route and leaves less to Genkit. All four speak the same wire format and redact errors the same way.

- **`serve_flow`:** Genkit owns the route.
- **`handle_genkit_request`:** you own the route signature and `Depends`; Genkit owns parsing, JSON vs SSE, and errors.
- **`stream.to_sse()`:** you own the route and pick what to stream; Genkit owns SSE framing.
- **`genkit.web`:** you own everything; helpers keep you on the wire contract. For Flask, Django, Starlette, or your own adapter.

Wire format, shared by all four:

```text
POST {"data": <input>}
  JSON  => {"result": <output>}
  SSE   => data: {"message": <chunk>}   (repeated)
           data: {"result": <output>}
  error => {"message": ..., "status": ...}  or  data: {"error": {...}}  mid-stream
```

### Shared flow

```python
from fastapi import Depends, FastAPI, Header
from genkit import FlowContext, Genkit, PublicError
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini('gemini-flash-latest'))
app = FastAPI()

# 1. FastAPI dependency that resolves the caller
async def current_user(authorization: str = Header()) -> dict[str, object]:
    return {'user_id': verify_token(authorization)}

# 2. Flow streams status lines and returns an ETA
@ai.flow
async def track_order(order_id: str, ctx: FlowContext[str]) -> str:
    if not order_id.startswith('ORD-'):
        raise PublicError('INVALID_ARGUMENT', f'{order_id} is not an order id')
    ctx.send_chunk(f'[{ctx.context["user_id"]}] locating {order_id}')
    ctx.send_chunk('courier is 2 stops away')
    return 'ETA 14:20'
```

### Level 1: `serve_flow`

One line per flow. `context_dependency` reuses your `Depends` auth; its value becomes `ctx.context`. The client picks JSON or SSE with `Accept: text/event-stream` or `?stream=true`.

```python
from genkit_fastapi import serve_flow

# 1. Mount the flow at POST /api/track_order
app.include_router(serve_flow(track_order, context_dependency=current_user), prefix='/api')

# 2. JSON
# POST /api/track_order  {"data": "ORD-9921"}
# => {"result": "ETA 14:20"}

# 3. SSE (Accept: text/event-stream)
# => data: {"message": "[u_42] locating ORD-9921"}
# => data: {"message": "courier is 2 stops away"}
# => data: {"result": "ETA 14:20"}
```

### Level 2: `handle_genkit_request`

Your route, your `Depends`, your path. Genkit still reads `{"data": ...}`, negotiates JSON vs SSE, and formats errors.

```python
from fastapi import Request
from genkit_fastapi import handle_genkit_request

# 1. Route signature and dependencies are yours
@app.post('/orders/track', response_model=None)
async def track(request: Request, user: dict[str, object] = Depends(current_user)):
    # 2. Pass the resolved context; same JSON/SSE behavior as serve_flow
    return await handle_genkit_request(request, action=track_order, context=user)
```

### Level 3: `stream.to_sse()`

You decide the input shape and what streams. `.to_sse()` on any `StreamResponse` (a flow, `ai.generate_stream()`, or a tool) or `AgentTurn` frames chunks, the final result, and mid-stream errors as SSE events. A failure mid-stream ends with one `error` frame and no `result`.

```python
from fastapi.responses import StreamingResponse

# 1. Typed query param instead of {"data": ...}; always SSE
@app.get('/orders/{order_id}/live')
async def live(order_id: str, user: dict[str, object] = Depends(current_user)):
    stream = track_order.stream(order_id, context=user)
    return StreamingResponse(stream.to_sse(), media_type='text/event-stream')

# 2. Stream a model call directly, no flow
@app.post('/support/chat')
async def chat(prompt: str, user: dict[str, object] = Depends(current_user)):
    stream = ai.generate_stream(prompt=prompt, context=user)
    return StreamingResponse(stream.to_sse(), media_type='text/event-stream')
    # => data: {"message": {"content": [{"text": "Your order"}], ...}}
    # => data: {"result": {"message": {...}, "finishReason": "stop", ...}}
```

### Level 4: `genkit.web` primitives

No adapter. Use this for another framework or when you're writing an adapter. Four helpers cover the whole contract.

```python
from starlette.requests import Request
from starlette.responses import JSONResponse
from genkit.web import RequestData, error_body, error_status, read_body, wants_stream

async def track_endpoint(request: Request):
    try:
        # 1. {"data": x} -> x; {} or {"data": null} -> no input
        order_id = read_body(await request.json())

        # 2. Build context from headers (names lowercased, repeats comma-joined)
        req = RequestData(request=request, method=request.method, headers=request.headers, input=order_id)
        context = {'user_id': verify_token(req.headers.get('authorization'))}

        # 3. Accept: text/event-stream or ?stream=true
        if wants_stream(accept=request.headers.get('accept'), stream=request.query_params.get('stream')):
            stream = track_order.stream(order_id, context=context)
            return StreamingResponse(stream.to_sse(), media_type='text/event-stream')

        result = await track_order.run(order_id, context=context)
        return JSONResponse({'result': result.response})
    except Exception as e:
        # 4. Redacts everything but PublicError
        return JSONResponse(error_body(e), status_code=error_status(e))
```

### Per-tenant API keys

A tenant's provider key goes in one place: `context={'secrets': {'api_key': ...}}`. The Google GenAI models read it from there and fall back to the plugin's key when it's absent.

- **Wrong slot fails loudly:** a key in `config=` or at the top level of `context` raises `INVALID_ARGUMENT` that names `context.secrets`.
- **Inherited:** inside a flow, `ai.generate()` with no `context=` uses the flow's context, so tools and nested calls get the same key.
- **Not traced:** the Dev UI shows `secrets` and `auth` as `<redacted>`.
- **Not stored on the `Operation`:** a background job's handle carries no key, so every `check_operation` / `cancel_operation` passes it again.

```python
from fastapi import Depends, Header, Request
from fastapi.responses import StreamingResponse
from genkit import Operation
from genkit_fastapi import handle_genkit_request
from genkit_google_genai import GoogleAI

# 1. One dependency resolves the tenant and builds the context Genkit expects
async def tenant_context(authorization: str = Header()) -> dict[str, object]:
    tenant = await tenants.from_token(authorization)
    return {
        'auth': {'tenant_id': tenant.id},
        'secrets': {'api_key': await secret_manager.get(f'gemini-key/{tenant.id}')},
    }

# 2. Level 2: the flow's ai.generate() inherits the context, key included
@app.post('/orders/track', response_model=None)
async def track(request: Request, ctx: dict[str, object] = Depends(tenant_context)):
    return await handle_genkit_request(request, action=track_order, context=ctx)

# 3. Level 3: call ai.generate_stream() directly and pass the context yourself
@app.post('/support/chat')
async def chat(prompt: str, ctx: dict[str, object] = Depends(tenant_context)):
    stream = ai.generate_stream(prompt=prompt, context=ctx)
    return StreamingResponse(stream.to_sse(), media_type='text/event-stream')

# 4. Background job: start with the tenant's key...
veo = GoogleAI.veo('veo-3.0-generate-001')

@app.post('/promos')
async def start_promo(prompt: str, ctx: dict[str, object] = Depends(tenant_context)) -> Operation:
    return await ai.generate_operation(model=veo, prompt=prompt, context=ctx)
    # => {"id": "operations/abc123", "done": false}

# 5. ...and poll with it again; the Operation doesn't carry it
@app.post('/promos/poll')
async def poll_promo(op: Operation, ctx: dict[str, object] = Depends(tenant_context)) -> Operation:
    return await ai.check_operation(op, context=ctx)
    # => {"id": "operations/abc123", "done": true, "output": {...}}

# Wrong slot: rejected before the provider is called
await ai.generate(prompt='hi', context={'api_key': key})
# => INVALID_ARGUMENT: API key belongs in context.secrets, not config or the top-level context.
#    Pass the key as context={'secrets': {'api_key': ...}}.
```

### Error redaction

In process, you get the real exception with its type, `__cause__`, and traceback. Over HTTP, `error_body` / `error_status` decide what leaves the server, at every level above:

- **`PublicError`:** its message, status, and details go out with the mapped HTTP code.
- **Bad request to the flow itself** (e.g. input fails the schema): 4xx status, generic message.
- **Anything else** (`GenkitError`, provider errors, `RuntimeError`): `500 {"message": "Internal Error", "status": "INTERNAL"}`. The real message stays in your logs and trace.

```python
@ai.flow
async def refund_order(order_id: str) -> str:
    if order_id == 'ORD-0000':
        # 1. Author says this text is safe for the caller
        raise PublicError('NOT_FOUND', f'{order_id} does not exist')
    # 2. Internal detail; never leaves the server
    raise RuntimeError('ledger-primary: connection pool exhausted')

# In process: the real exception
try:
    await refund_order('ORD-9921')
except RuntimeError as e:
    print(e)
    # => ledger-primary: connection pool exhausted

# Over HTTP, JSON
# POST {"data": "ORD-0000"}
# => 404 {"message": "ORD-0000 does not exist", "status": "NOT_FOUND"}
# POST {"data": "ORD-9921"}
# => 500 {"message": "Internal Error", "status": "INTERNAL"}

# Over HTTP, SSE: chunks already sent stay sent; the stream ends with one error frame
# => data: {"message": "..."}
# => data: {"error": {"message": "Internal Error", "status": "INTERNAL"}}
```

---

## 6. Telemetry & OpenTelemetry

`genkit_otel` emits `gen_ai.*` spans and metrics per the OTel GenAI semantic conventions. Your app owns the OTel SDK and exporter. Configure the instrumentation before `Genkit()` so every action registered after it is covered. It runs alongside the Dev UI trace pipeline; the two export separately.

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from genkit import Genkit
from genkit.telemetry import configure_instrumentation
from genkit_google_genai import GoogleAI
from genkit_otel import GenAiInstrumentation

# 1. App owns the OTel SDK
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint='http://localhost:4318/v1/traces')))
trace.set_tracer_provider(provider)

# 2. Configure instrumentation before creating Genkit; prompts and outputs stay off spans by default
configure_instrumentation(GenAiInstrumentation(content_capturing_mode='NO_CONTENT'))

# 3. Then create the app
ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini('gemini-flash-latest'))

# 4. Flows and model calls produce nested spans (tool spans: emit_tool_spans=True)
@ai.flow
async def audit_vendor(vendor_id: str) -> str:
    response = await ai.generate(prompt=f'Run a compliance scan for {vendor_id}.')
    return response.text

await audit_vendor('VEN-118')
# => span audit_vendor
#      span chat gemini-flash-latest  (kind=CLIENT)
#        gen_ai.operation.name=chat
#        gen_ai.request.model=gemini-flash-latest
#        gen_ai.usage.input_tokens=14
#        gen_ai.usage.output_tokens=52
```

Set `content_capturing_mode='SPAN_ONLY'` (or `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`) to record prompts and outputs on spans. An explicit `'NO_CONTENT'` wins over the env var, so it works as a PII opt-out.

---

## 7. Embedders

Embedders vectorize documents for retrieval. Register a custom embedder with `ai.define_embedder(name, fn)` (or return an `Embedder` from a plugin's `list_actions()`), and call it with `ai.embed` or `ai.embed_many`.

```python
from genkit import Embedding, Genkit
from genkit.embedder import EmbedRequest, EmbedResponse

ai = Genkit()

# 1. Define a custom embedder function (takes EmbedRequest, returns EmbedResponse)
async def local_vectorizer(req: EmbedRequest) -> EmbedResponse:
    return EmbedResponse(embeddings=[Embedding(embedding=[0.012, 0.451, -0.231]) for _ in req.input])

ai.define_embedder('custom/text_vectors', local_vectorizer)

# 2. Embed a single string or Document (use ai.embed_many for batches)
result = await ai.embed(
    embedder='custom/text_vectors',
    content='Search indexed warranty policies',
)
print(result[0].embedding)
# => [0.012, 0.451, -0.231]
```

---

## 8. Evaluators

Evaluators score dataset rows against reference outputs and contexts. Register a per-row evaluator with `ai.define_evaluator(name, fn, ...)` or a whole-dataset evaluator with `ai.define_batch_evaluator(name, fn, ...)`, and run it with `ai.evaluate`.

```python
from genkit import Genkit
from genkit.evaluator import BaseDataPoint, EvaluatorResponse, Score, ScoreDetails, ScoreStatus

ai = Genkit()

# 1. Score one dataset row at a time
async def relevance_evaluator(row: BaseDataPoint, options: dict[str, object]) -> EvaluatorResponse:
    approved = 'approved' in str(row.output).lower()
    return EvaluatorResponse(
        test_case_id=row.test_case_id or '',
        evaluation=[
            Score(
                score=1.0 if approved else 0.0,
                status=ScoreStatus.PASS if approved else ScoreStatus.FAIL,
                details=ScoreDetails(reasoning='Checked for approval keyword'),
            )
        ],
    )

# 2. Register the evaluator by name
ai.define_evaluator(
    'custom/relevance',
    relevance_evaluator,
    display_name='Relevance',
    definition='Whether the output confirms claim approval.',
)

# 3. Run evaluation over a dataset
rows = await ai.evaluate(
    evaluator='custom/relevance',
    dataset=[
        BaseDataPoint(
            test_case_id='claim-1',
            input='What is the claim status?',
            output='Claim is approved for refund',
        )
    ],
)
print(rows[0].evaluation[0].score)
# => 1.0
```

---

## 9. Middleware

Middleware wraps the three layers of a generate call: `wrap_generate` (the whole tool loop), `wrap_model` (each model call), and `wrap_tool` (each tool call). It can also add tools through `tools(ctx)`. Settings live on a Pydantic config, so the Dev UI can render a form for them.

`genkit_a2ui.Surfaces` is a real example. The model writes ```` ```a2ui ```` fences, and `Surfaces` turns them into `application/a2ui+json` data parts a client can render as UI cards, both on the stream and on the final message.

### Using it

```python
from genkit_a2ui import Surfaces, envelopes_from_parts, is_a2ui_part

# 1. Add it per call; settings are typed (SurfacesConfig)
stream = ai.generate_stream(
    prompt='Show tonight\'s open tables as cards I can tap to book.',
    use=[Surfaces(validate='strict')],
)

# 2. Cards arrive as data parts while the model is still writing
async for chunk in stream:
    for part in chunk.content:
        if is_a2ui_part(part):
            render_card(part)
        elif part.text:
            print(part.text, end='')

# 3. The final message holds the same cards, with the same surface ids
response = await stream.response
envelopes = envelopes_from_parts(response.message.content)
```

With `validate='strict'`, a malformed card fails the turn (`finish_reason == FAILED`). `response.messages` then ends at the user turn, so a retry doesn't feed the bad card back to the model.

### How it's built

A condensed version of `Surfaces.wrap_model`: rewrite the request, swap in a chunk handler, call the model, rewrite the response.

```python
from typing import Literal
from pydantic import BaseModel, Field
from genkit import FinishReason
from genkit.middleware import Middleware, MiddlewareContext, ModelHookParams

# 1. Config is a Pydantic model; the Dev UI renders it as a form
class SurfacesConfig(BaseModel):
    instructions: Literal['system', 'none'] = 'system'
    validation: Literal['off', 'warn', 'strict'] = Field(default='warn', alias='validate')
    catalog: str | None = None

# 2. Middleware[Config] gives you self.config, typed
class Surfaces(Middleware[SurfacesConfig]):
    name = 'surfaces'

    async def wrap_model(self, params: ModelHookParams, ctx: MiddlewareContext, next_fn):
        catalog = resolve_catalog(ctx=ctx, catalog=self.config.catalog)
        parser = StreamParser(catalog=catalog, validate=self.config.validation)

        # 3. Before the model: turn prior cards back into text, add catalog instructions
        params.request = sanitize_inbound(request=params.request)
        if self.config.instructions != 'none':
            params.request = inject_instructions(request=params.request, catalog=catalog)

        # 4. During: rewrite chunks as each fence closes
        if ctx.on_chunk is not None:
            downstream = ctx.on_chunk

            def on_chunk(chunk):
                rewritten = transform_chunk(chunk=chunk, parser=parser)  # None while a fence is open
                if rewritten is not None:
                    downstream(rewritten)

            ctx.replace_on_chunk(on_chunk)

        response = await next_fn(params, ctx)

        # 5. After: leave stopped turns alone, otherwise rewrite the final message
        if response.finish_reason.is_abnormal() or response.finish_reason == FinishReason.UNKNOWN:
            return response
        return transform_response(response=response, catalog=catalog, validate=self.config.validation)
```

The full version also restores the original chunk callback in a `finally` and reuses the stream's surface ids on the final parse. Plugins ship middleware like this from `Plugin.list_middleware()`; an app can register its own with `@ai.middleware`.

---

## 10. Runtime Architecture: Reflection & Action Registry

```
+--------------------------------------------------------------+
|                        Genkit Runtime                        |
|                                                              |
|   +-----------------------+      +-----------------------+   |
|   |    Action Registry    | <--- |   Plugins (GoogleAI,  |   |
|   | (Models, Flows, Tools)|      |   Anthropic, Local)   |   |
|   +-----------------------+      +-----------------------+   |
|               |                                              |
|               +-----------------------+                      |
|                                       v                      |
|   +-----------------------+      +-----------------------+   |
|   |  App Event Loop       |      |  Reflection Daemon    |   |
|   |  (FastAPI / Workers)  |      |  (Background Thread)  |   |
|   |  Runs business logic  |      |  Serves Dev UI (JSON) |   |
|   +-----------------------+      +-----------------------+   |
+--------------------------------------------------------------+
```

### The Action Registry
All Genkit capabilities (models, tools, flows, embedders, evaluators) inherit from [`Action`](../packages/genkit/src/genkit/_core/_action.py). Plugins register actions during initialization. The registry maintains action metadata, validates JSON schemas, and resolves model references dynamically.

### Reflection Server & Event Loop Coordination
* **Background Daemon**: When `GENKIT_ENV=dev` is active, Genkit spawns a lightweight reflection HTTP server on a dedicated background OS thread.
* **Dev UI Protocol**: The reflection server surfaces schemas, active actions, and trace inspections over `/api/__genkit/actions` without blocking the main event loop.
* **Lifecycle Management (`ai.run_main()`)**: In CLI and script execution, `ai.run_main(coroutine)` binds the main event loop to application tasks while orchestrating graceful teardown of the reflection thread on `SIGINT` or process termination. In production application servers (e.g. `uvicorn main:app`), the reflection server remains disabled, running zero background threads.
