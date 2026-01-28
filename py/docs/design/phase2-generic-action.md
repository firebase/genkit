# Phase 2: Generic Action Implementation

**Status:** Ready for Implementation  
**Prerequisite:** PR #4270 (completed)  
**Estimated Effort:** 2-3 days

## Executive Summary

Add generics to `Action` class so users get IDE autocomplete on flow/tool inputs and outputs. This matches the Genkit JS implementation.

## JS Reference Implementation

Genkit JS already has typed Actions (`js/core/src/action.ts` lines 160-177):

```typescript
export type Action<
  I extends z.ZodTypeAny = z.ZodTypeAny,  // Input type
  O extends z.ZodTypeAny = z.ZodTypeAny,  // Output type  
  S extends z.ZodTypeAny = z.ZodTypeAny,  // Stream chunk type
> = ((input?: z.infer<I>, options?: RunOptions) => Promise<z.infer<O>>) & {
  run(input?: z.infer<I>, options?: ...): Promise<ActionResult<z.infer<O>>>;
  stream(input?: z.infer<I>, opts?: ...): StreamingResponse<O, S>;
};
```

**Key insight:** JS actions take ONE input argument (plus context/options). Python should match this.

## Current Python State

### Already Generic
```python
# core/action/types.py - DONE ✅
class ActionResponse(BaseModel, Generic[ResponseT]):
    response: ResponseT
    trace_id: str
```

### NOT Generic
```python
# core/action/_action.py - NEEDS WORK ❌
class Action:  # Not Generic
    def run(self, input: object = None) -> ActionResponse:  # Untyped
```

## Proposed Solution

### Dependencies

Add `typing_extensions` to `pyproject.toml`:

```toml
dependencies = [
    "typing_extensions>=4.0",
    # ... existing deps
]
```

> **Note:** `Never` and `TypeVar` with `default=` require `typing_extensions` for Python < 3.11/3.13. We use `typing_extensions` consistently for cross-version compatibility.

### Type Setup

```python
from typing import Any
from typing_extensions import Never, TypeVar

# All TypeVars have defaults for backwards compatibility
InputT = TypeVar("InputT", default=Any)
OutputT = TypeVar("OutputT", default=Any)
ChunkT = TypeVar("ChunkT", default=Never)  # Never = "not used" for non-streaming
```

### Action Class

```python
class Action(Generic[InputT, OutputT, ChunkT]):
    """
    Generic action matching JS implementation.
    
    Type Parameters:
        InputT: Type of the input argument (default: Any)
        OutputT: Type of the output/response (default: Any)
        ChunkT: Type of streaming chunks (default: Never for non-streaming)
    """
    
    def run(
        self,
        input: InputT | None = None,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, object] | None = None,
    ) -> ActionResponse[OutputT]:
        ...
    
    async def arun(
        self,
        input: InputT | None = None,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, object] | None = None,
    ) -> ActionResponse[OutputT]:
        ...
    
    def stream(
        self,
        input: InputT | None = None,
        context: dict[str, object] | None = None,
    ) -> tuple[AsyncIterator[ChunkT], asyncio.Future[ActionResponse[OutputT]]]:
        ...
```

### Type Mapping: JS → Python

| JS | Python | Default |
|----|--------|---------|
| `I` (Zod) | `InputT` | `Any` |
| `O` (Zod) | `OutputT` | `Any` |
| `S` (Zod) | `ChunkT` | `Never` |

### Usage Examples

```python
# Unparameterized (backwards compatible, no type safety)
action = Action(...)  # Action[Any, Any, Never]

# Output only (most common)
action: Action[Any, UserOutput] = Action(...)

# Full typing
action: Action[UserInput, UserOutput] = Action(...)

# Streaming
action: Action[UserInput, UserOutput, MyChunk] = Action(...)
```

## Addressing Review Feedback

### 1. "ParamSpec regression" - NOT AN ISSUE

**Concern:** Changing to single-input typing breaks multi-arg flows.

**Resolution:** Actions only take ONE input (matching JS). Here's the actual control flow:

```python
# 1. User calls flow with multiple args:
result = await my_flow(x, y)

# 2. FlowWrapper.__call__ forwards all args to the wrapped function:
class FlowWrapper(Generic[P, T]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self._fn(*args, **kwargs)  # _fn is async_wrapper

# 3. async_wrapper (created by @flow decorator) extracts first arg:
async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
    input_arg = args[0] if args else None  # Extract first arg
    return cast(T, (await action.arun(input_arg)).response)

# 4. Action.arun receives only the first argument:
action.arun(input_arg)
```

**Key points:**
- ParamSpec `P` stays on `FlowWrapper` for user-facing API
- `async_wrapper` extracts `args[0]` before calling Action
- Action uses `InputT` for the single input it receives
- This matches the existing runtime behavior

### 2. "Dropped input=None default" - FIXED

**Resolution:** Keep the default:
```python
def run(self, input: InputT | None = None, ...) -> ActionResponse[OutputT]:
```

### 3. "Defaults to Any isn't guaranteed" - FIXED

**Resolution:** Use `typing_extensions.TypeVar` with explicit defaults on ALL TypeVars:
```python
InputT = TypeVar("InputT", default=Any)
OutputT = TypeVar("OutputT", default=Any)
ChunkT = TypeVar("ChunkT", default=Never)
```

This ensures `Action` without parameters defaults to `Action[Any, Any, Never]` consistently across type checkers.

### 4. "Erasing generics loses inference" - FIXED PROPERLY

**Resolution:** Delete the broken type aliases, inline in `Formatter`:

```python
# Before (broken - T unbound):
T = TypeVar('T')
MessageParser = Callable[[MessageWrapper], T]

# After (fixed - inline in generic class):
class Formatter(Generic[OutputT, ChunkT]):
    def __init__(
        self,
        message_parser: Callable[[MessageWrapper], OutputT],
        chunk_parser: Callable[[GenerateResponseChunkWrapper], ChunkT],
    ) -> None:
        ...
```

### 5. "ChunkT under-specified" - FIXED

**Resolution:** Default `ChunkT` to `Never` (not `None`):

```python
ChunkT = TypeVar("ChunkT", default=Never)
```

- `Never` explicitly means "this type is not used"
- Non-streaming: `stream()` returns `AsyncIterator[Never]` (clearly unused)
- Streaming: `stream()` returns `AsyncIterator[MyChunk]` (useful type)

## Files to Modify

| File | Change |
|------|--------|
| `packages/genkit/pyproject.toml` | Add `typing_extensions>=4.0` |
| `core/action/_action.py` | Add `Generic[InputT, OutputT, ChunkT]` with defaults |
| `core/registry.py` | Update `register_action` return type |
| `ai/_registry.py` | Update `FlowWrapper.__init__` to `Action[Any, T, Never]` |
| `blocks/formats/types.py` | Delete unbound TypeVar aliases |
| `blocks/model.py` | Delete unbound TypeVar aliases |

## Implementation Order

1. **Add dependency** (5 min)
   - Add `typing_extensions>=4.0` to `pyproject.toml`

2. **Fix unbound TypeVars** (15 min)
   - Delete `MessageParser`, `ChunkParser` aliases
   - Inline in `Formatter.__init__`

3. **Make Action generic** (2 hours)
   - Add imports from `typing_extensions`
   - Add `Generic[InputT, OutputT, ChunkT]` with defaults
   - Update method signatures
   - Keep `input: InputT | None = None`

4. **Connect FlowWrapper** (30 min)
   - Change `action: Action` to `action: Action[Any, T, Never]`
   - Remove `cast(T, ...)` since type flows through

5. **Update Registry** (30 min)
   - Update return types

6. **Test** (1 hour)
   - Unit tests
   - Type checker verification (`ty`, `mypy`, `pyright`)
   - IDE autocomplete check in VS Code

## Success Criteria

```python
@ai.flow()
async def my_flow(user: UserInput) -> UserOutput:
    ...

result = await my_flow(input)
result.name  # ✅ IDE shows: str (autocomplete works!)
result.typo  # ✅ IDE shows: error (typo caught!)
```

## Backwards Compatibility

Full backwards compatibility:
- `Action` without parameters defaults to `Action[Any, Any, Never]`
- Existing code continues to work without changes
- New code can opt-in to type safety by parameterizing
- No runtime behavior changes
