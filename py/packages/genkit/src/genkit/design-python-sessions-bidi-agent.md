# Python Design: Sessions, Bidi Actions, and Agent Primitive

## 1. Overview

**Bidi Actions** are bidirectional streaming actions where client sends init + input stream and server responds with output stream + final result. Unlike standard actions, bidi actions keep a channel open for multi-turn interaction within a single HTTP/WebSocket invocation. The input channel enables interrupts (tool approval) and incremental prompts; the output channel enables token streaming, status updates, and artifact delivery.

**Session** is a thread-safe state container holding `messages`, `custom` (user state generic `S`), `artifacts`, and `input_variables`. **SessionStore** is a protocol for persistence via snapshots—enabling server-managed state where client sends only `snapshot_id` to resume. Client-managed mode (no store) passes full state each turn. Go's implementation uses `sync.RWMutex`; Python uses `threading.RLock` for sync accessors.

**SessionFlow** wraps bidi actions with automatic turn management: `SessionRunner.run(fn)` loops over inputs, adds messages to session, increments `turn_index`, triggers snapshot callbacks, and sends `EndTurn` chunks. **Agent** is sugar over SessionFlow with standardized schemas for chat—replaces `Chat` API. Go's `DefineSessionFlow` maps to Python's `define_session_flow`; Go's experimental `DefineAgent` maps to `define_agent`.

---

## 2. Python API Surface

### 2.1 BidiAction

```python
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Generic, TypeVar

Init = TypeVar('Init')
In = TypeVar('In')
Out = TypeVar('Out')
Stream = TypeVar('Stream')

class BidiAction(Generic[Init, In, Out, Stream]):
    """Bidirectional streaming action."""
    name: str

    async def run(
        self,
        init: Init,
        input_stream: AsyncIterator[In],
    ) -> tuple[AsyncIterator[Stream], Awaitable[Out]]:
        """Returns (output_stream, result_future)."""
        ...

BidiActionFn = Callable[
    [Init, AsyncIterator[In], 'Responder[Stream]'],
    Awaitable[Out]
]

def define_bidi_action(
    registry: Registry,
    name: str,
    fn: BidiActionFn[Init, In, Out, Stream],
    *,
    init_schema: type[Init] | None = None,
    input_schema: type[In] | None = None,
    output_schema: type[Out] | None = None,
) -> BidiAction[Init, In, Out, Stream]:
    ...
```

### 2.2 Session

```python
from typing import Generic, TypeVar
from genkit.core.typing import Message, Artifact, SessionState

S = TypeVar('S')

class Session(Generic[S]):
    """Thread-safe state container."""

    @property
    def messages(self) -> list[Message]: ...

    @property
    def custom(self) -> S | None: ...

    @property
    def artifacts(self) -> list[Artifact]: ...

    def add_messages(self, *messages: Message) -> None:
        """Append to history. Thread-safe."""
        ...

    def set_custom(self, state: S) -> None:
        """Replace custom state. Thread-safe."""
        ...

    def add_artifacts(self, *artifacts: Artifact) -> None:
        """Add/replace by name. Thread-safe."""
        ...

    def state(self) -> SessionState[S]:
        """Deep copy of current state."""
        ...

    async def save(self) -> str:
        """Create snapshot, return snapshot_id. Requires store."""
        ...
```

### 2.3 SessionStore Protocol

```python
from typing import Protocol, runtime_checkable
from genkit.core.typing import SessionSnapshot

@runtime_checkable
class SessionStore(Protocol[S]):
    """Pluggable persistence backend."""

    async def load(self, snapshot_id: str) -> SessionSnapshot[S] | None:
        """Load snapshot by ID. Returns None if not found."""
        ...

    async def save(self, snapshot: SessionSnapshot[S]) -> None:
        """Persist snapshot."""
        ...
```

### 2.4 SessionFlow

```python
from genkit.core.typing import SessionFlowInput, SessionFlowResult, SessionFlowInit, SessionFlowOutput, SessionFlowStreamChunk

class SessionRunner(Generic[S]):
    """Extended Session with turn management."""
    session: Session[S]
    input_stream: AsyncIterator[SessionFlowInput]
    turn_index: int

    async def run(self, fn: Callable[[SessionFlowInput], Awaitable[None]]) -> None:
        """Loop over inputs calling fn per turn. Auto-adds messages, snapshots, sends EndTurn."""
        ...

    def result(self) -> SessionFlowResult:
        """Build result from current state."""
        ...

class Responder(Generic[Stream]):
    """Output channel."""
    def send_model_chunk(self, chunk: ModelResponseChunk) -> None: ...
    def send_status(self, status: Stream) -> None: ...
    def send_artifact(self, artifact: Artifact) -> None: ...

SessionFlowFn = Callable[[Responder[Stream], SessionRunner[S]], Awaitable[SessionFlowResult | None]]

class SessionFlow(Generic[Stream, S]):
    name: str

    async def run(
        self,
        init: SessionFlowInit[S],
        input_stream: AsyncIterator[SessionFlowInput],
    ) -> tuple[AsyncIterator[SessionFlowStreamChunk[Stream]], Awaitable[SessionFlowOutput[S]]]:
        ...

def define_session_flow(
    registry: Registry,
    name: str,
    fn: SessionFlowFn[Stream, S],
    *,
    store: SessionStore[S] | None = None,
    snapshot_callback: Callable[[SnapshotContext[S]], bool] | None = None,
) -> SessionFlow[Stream, S]:
    ...
```

### 2.5 Agent

```python
from genkit.core.typing import Message

AgentFn = Callable[[Responder[Stream], SessionRunner[S], SessionFlowInput], Awaitable[None]]

class Agent(Generic[Stream, S]):
    """High-level chat agent. Replaces Chat API."""
    name: str

    async def chat(
        self,
        message: Message | str,
        *,
        session_id: str | None = None,
        state: SessionState[S] | None = None,
    ) -> tuple[AsyncIterator[SessionFlowStreamChunk[Stream]], Awaitable[SessionFlowOutput[S]]]:
        ...

def define_agent(
    registry: Registry,
    name: str,
    fn: AgentFn[Stream, S],
    *,
    store: SessionStore[S] | None = None,
) -> Agent[Stream, S]:
    ...
```

---

## 3. Python Deviations from JS/Go

| Feature | JS/Go Approach | Python Approach | Reason |
|---------|----------------|-----------------|--------|
| **Async model** | JS: `async function*` generator; Go: goroutine+channel | `async def` + `AsyncIterator` + `Channel` class | Python async generators can't do bidi; explicit Channel from `genkit.aio` |
| **Streaming input** | JS: `for await (const x of inputStream)`; Go: `for x := range ch` | `async for x in input_stream` | Direct mapping; Python's async for identical semantics |
| **Streaming output** | JS: `sendChunk()` callback; Go: `responder <- chunk` | `Responder` class with `send_model_chunk()`, `send_status()`, `send_artifact()` | No typed send-only channels in Python; methods provide type safety |
| **Cancellation** | JS: `AbortController`; Go: `ctx.Done()` | `asyncio.CancelledError` propagation | Native asyncio cancellation; no explicit tokens needed |
| **Generics** | Go: `[State any]`; TS: `<State>` | `Generic[S]` with `TypeVar('S')` | Python typing module; requires `@runtime_checkable Protocol` for store |
| **Decorator vs function** | Go: `DefineSessionFlow()`; JS: `defineAgent()` | Both `@ai.session_flow()` decorator AND `define_session_flow()` | Matches existing `@ai.flow()` + `define_flow()` pattern in codebase |
| **Session thread safety** | Go: `sync.RWMutex` | `threading.RLock` | Session methods are sync (quick in-memory); RLock for reentrant locking |
| **Store protocol** | Go: interface; JS: duck-typed | `@runtime_checkable class SessionStore(Protocol[S])` | Enables `isinstance()` checks + static type checking |
| **Deep copy** | Go: JSON marshal/unmarshal | `pydantic.model_copy(deep=True)` | Pydantic native; avoids JSON overhead |
| **State in output** | Go: full state if no store, else `snapshot_id` only | Same: `SessionFlowOutput.state` populated only if `store=None` | Matches Go exactly |

---

## 4. Open Questions for Jeff

1. **`Session.save()` vs auto-snapshot**: Go triggers snapshots via callback at turn-end/invocation-end. Should Python expose explicit `await session.save()` for manual control, or keep it automatic only? Explicit gives control for interrupt points; automatic is simpler. Recommend: both (auto + optional manual).

2. **Sync vs async Session accessors**: `session.messages` (property) vs `await session.get_messages()`. Go uses sync with mutex. Python: keep sync with `threading.RLock` (no await ceremony for quick reads), or go full async with `asyncio.Lock`? Recommend: sync properties, async only for `save()`.

3. **`Responder` lifetime**: Go closes channel when flow function returns. Python: make `Responder` a context manager (`async with responder:`) for explicit cleanup, or implicit close on function exit? Recommend: implicit (no context manager needed).

4. **`SessionRunner.run()` vs manual loop**: Go's `SessionRunner.Run(fn)` auto-handles turn mechanics. Should Python require `await sess.run(handler)` or allow raw `async for input in sess.input_stream:` with manual bookkeeping? Recommend: both, but document `run()` as preferred.

5. **Generic inference**: `define_agent[MyState](...)` vs `define_agent(..., state_type=MyState)`. Explicit type param requires annotation at call site. Schema param enables runtime validation. Recommend: `state_schema: type[S] | None = None` param; infer from initial state if not provided.

6. **`InMemorySessionStore` location**: Go puts in `exp` package. Python options: `genkit.core.session`, `genkit.testing`, or `genkit.stores.memory`. Recommend: `genkit.testing` (signal it's not production).

7. **WebSocket transport**: Bidi requires persistent connection. Reflection API v2 adds WebSocket. Should bidi actions work over HTTP/SSE fallback (client polls, server SSE), or require WebSocket? Recommend: WebSocket required for true bidi; SSE fallback for output-only streaming.

---

## 5. Dependency Order

```
1. genkit.core.typing (DONE)
   └── SessionState, Artifact, SessionFlowInput/Output/StreamChunk, SnapshotEvent
   └── Pure Pydantic models, no behavior

2. genkit.core.session
   └── Session[S], SessionSnapshot, SessionStore protocol, InMemorySessionStore
   └── Depends on: typing

3. genkit.aio.channel (enhancement)
   └── Add buffered receive, close signaling for bidi input
   └── Depends on: nothing new

4. genkit.core.bidi
   └── BidiAction, define_bidi_action, Responder
   └── Depends on: action, channel, typing

5. genkit.core.session_flow
   └── SessionRunner, SessionFlow, define_session_flow
   └── Depends on: session, bidi, tracing

6. genkit.ai.agent
   └── Agent, define_agent, @ai.agent() decorator
   └── Depends on: session_flow, registry

7. Reflection API v2
   └── WebSocket endpoint for bidi in dev tools
   └── Parallel track; not blocking 1-6
```

**MVP (Phase 1)**: 1-5. Full session flow with in-memory store.
**Phase 2**: 6. Agent sugar, Chat deprecation.
**Phase 3**: 7 + plugin stores (Firestore, Postgres, Redis).
