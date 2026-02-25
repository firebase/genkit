# Dev UI + Event Loop Model


## Context


In Python async systems, an event loop is the runtime that drives `await` code.


For web apps, frameworks such as FastAPI typically own that loop for request handling. Genkit Dev UI reflection can also execute flows/actions, which means the same app can receive execution from:
- normal web requests (framework loop)
- Dev UI/reflection execution path (potentially another loop)


Some async clients (provider SDK clients, `httpx.AsyncClient`, etc.) are effectively tied to the loop where they were created. Reusing one instance from another loop can fail at runtime.


## Problem Statement


How do we let one Python app support both web-framework execution and Dev UI execution seamlessly, without:
- forcing framework-specific lifecycle wiring on app developers
- introducing hard-to-debug cross-loop runtime failures?


## Options Considered


### A) Single-event-loop architecture (current solution)


How it works:
- Reflection is forced onto the same event loop as app execution.
- Developers wire framework lifecycle so Genkit reflection starts/stops in-loop.


App code shape:


```python
@asynccontextmanager
async def lifespan(app: FastAPI):
   await ai.start_reflection_same_loop()
   try:
       yield
   finally:
       await ai.stop_reflection()
```


Pros:
- Eliminates cross-loop client reuse by construction.


Cons:
- Framework-specific lifecycle burden for app developers.
- More docs/support surface and framework adapter complexity.
- Harder "it just works" story across FastAPI/Flask/Quart/etc.


### B) Separate loops + loop-local client management


How it works:
- Reflection remains separate-loop in-process.
- Plugin/runtime clients are acquired per-event-loop through a loop-local getter.
- Action handlers use `get_client()` at call time.


Plugin code shape:


```python
from collections.abc import Callable
from genkit.core._loop_local import _loop_local_client


self._get_client: Callable[[], AsyncOpenAI] = _loop_local_client(
   lambda: AsyncOpenAI(**self._params)
)


async def _run(req, ctx):
   client = self._get_client()
   return await call_model(client, req, ctx)
```


Pros:
- No framework lifecycle wiring for most app developers.
- Fits current runtime topology with modest plugin changes.
- Incremental rollout; immediate correctness improvements for provider SDK use.


Cons:
- App-owned global async clients can still be a footgun across loops.
- Requires plugin author discipline and regression tests.


## A vs B (Why B is Better for Product DX)


If primary goal is seamless Dev UI + web framework integration, B is the better fit:
- Better default developer experience (less unrelated concepts for app developer).
- Lower integration friction across frameworks.
- Smaller incremental change than architectural rework.
- Correctness is handled where it matters most (plugin/runtime-managed clients).


A is stricter runtime-wise, but pushes integration burden onto users and framework-specific docs/support.

That also means every framework requires its own lifecycle hook implementation and has to be bridged with a plugin or custom app developer code.

## Remaining Footgun (Explicit)


Still risky app code:


```python
client = httpx.AsyncClient()  # module-global, reused across loops
```


Safer app code:


```python
async with httpx.AsyncClient() as client:
   await client.post(...)
```


Mitigation:
- Keep plugin internals loop-safe by default.
- Add concise docs for app-owned async clients.


## Helper Placement Decision


Question: where should the loop-local helper live?


Options:
- Plugin namespace (`genkit.plugins.<x>.utils`) -> duplicates logic, inconsistent usage.
- Public top-level API (`genkit.loop_local_client`) -> broad public contract, harder to evolve.
- Core internal utility (`genkit.core._loop_local`) -> shared implementation without expanding user API.


Recommendation:
- Keep helper in **core internal** (`genkit.core._loop_local`) for now.
- Use it across official plugins.
- Revisit public export only if app-level demand is clear and stable.

