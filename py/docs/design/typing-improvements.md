# Design Doc: Python Typing Improvements

**Author:** Genkit Team  
**Status:** Draft  
**Created:** 2026-01-25

## Overview

This document outlines a plan to add **generic type support** to the Genkit Python SDK, building on the foundation laid by PR #4270.

## Background: What PR #4270 Did

PR #4270 (`fix(py/genkit): resolve all ty type errors and ensure all functions have proper types`) made significant improvements to the codebase:

### Changes Made
| Change | Files Affected | Purpose |
|--------|----------------|---------|
| Added `ty` type checker | CI, `bin/lint` | Catch type errors in CI |
| `Any` → `object` | ~90 files | More specific than `Any` |
| Added Protocols | `_action.py` | Internal duck typing |
| Enabled `ANN` rules | `pyproject.toml` | Require annotations |
| Added return types | All functions | Pass `ty` checks |

### What This Achieved
- ✅ Codebase passes `ty` type checker
- ✅ All functions have type annotations
- ✅ CI enforces type checking
- ✅ Internal code has better type safety

## The Gap: What's Still Missing

PR #4270 solved **internal type safety** but not **user-facing type safety**. The difference:

| Audience | Goal | Status |
|----------|------|--------|
| **Internal devs** | Catch bugs in Genkit code | ✅ Done |
| **Genkit users** | IDE autocomplete on flows/tools | ❌ Not done |

### Why `object` Doesn't Help Users

The change from `Any` to `object` makes the type checker happy but provides zero benefit to users:

```python
# PR #4270 changed this:
class Action:
    def run(self, input: Any) -> ActionResponse:  # Before
    def run(self, input: object) -> ActionResponse:  # After

# But users still see:
result = await my_flow(data)
result.response  # IDE shows: object - no autocomplete!
```

Both `Any` and `object` mean "I don't know what type this is" from the user's perspective.

### What Users Need: Generics

For users to get IDE support, `Action` needs to be **generic**:

```python
# What we need:
class Action(Generic[InputT, OutputT]):
    def run(self, input: InputT) -> ActionResponse[OutputT]:
        ...

# Then users get:
result = await my_flow(data)  
result.response  # IDE shows: UserOutput - full autocomplete!
```

## Current State Analysis

### Core Issue: Action Not Generic

```python
# Current (after PR #4270):
class Action:
    def run(self, input: object = None) -> ActionResponse:
        ...

# Line 105 still has this TODO:
# TODO: add generics
StreamingCallback = Callable[[object], None]
```

### Unbound TypeVars Still Exist

In `blocks/formats/types.py` and `blocks/model.py`:

```python
T = TypeVar('T')
MessageParser = Callable[[MessageWrapper], T]  # ❌ T is unbound!
ChunkParser = Callable[[GenerateResponseChunkWrapper], T]  # ❌ T is unbound!
```

These are effectively `Any` because `T` isn't bound to anything.

## Proposed Solution

### Phase 1: Generic Action (builds on PR #4270)

```python
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
ChunkT = TypeVar('ChunkT')

class ActionResponse(Generic[OutputT], BaseModel):
    response: OutputT  # Was: object
    trace_id: str

class Action(Generic[InputT, OutputT, ChunkT]):
    def run(self, input: InputT, ...) -> ActionResponse[OutputT]:
        ...
    
    async def arun(self, input: InputT, ...) -> ActionResponse[OutputT]:
        ...
```

### Phase 2: Fix Unbound TypeVars

```python
# Option A: Be explicit about dynamic nature
MessageParser = Callable[[MessageWrapper], object]

# Option B: Use generic class (better)
class Formatter(Generic[OutputT, ChunkT]):
    def __init__(
        self,
        message_parser: Callable[[MessageWrapper], OutputT],
        chunk_parser: Callable[[GenerateResponseChunkWrapper], ChunkT],
    ) -> None:
        ...
```

### Phase 3: Typed Registry

```python
class Registry:
    def register_action(
        self, 
        kind: ActionKind, 
        name: str, 
        fn: Callable[[InputT], OutputT], 
    ) -> Action[InputT, OutputT, Any]:
        ...
```

## Relationship to PR #4270

| PR #4270 Did | This Doc Proposes |
|--------------|-------------------|
| Made `ty` pass | Make IDE autocomplete work |
| `Any` → `object` | `object` → `TypeVar` |
| Added annotations | Add generics |
| Internal safety | User-facing safety |

**PR #4270 is prerequisite foundation.** The annotations and type checker infrastructure make it easier to add generics correctly.

## Implementation Notes

### Backwards Compatibility

Existing code works unchanged:
```python
# Before (still works):
action = Action(...)  # Defaults to Action[Any, Any, Any]

# After (new capability):
action: Action[UserInput, UserOutput, Chunk] = Action(...)
```

### Files to Modify

| File | Change | Builds on PR #4270 |
|------|--------|-------------------|
| `core/action/_action.py` | Add `Generic[InputT, OutputT, ChunkT]` | Uses existing annotations |
| `core/action/types.py` | Make `ActionResponse` generic | Uses existing `object` types |
| `blocks/formats/types.py` | Fix unbound TypeVars | Already has TypeVars defined |
| `blocks/model.py` | Fix unbound TypeVars | Already has TypeVars defined |
| `ai/_registry.py` | Propagate generics | Uses existing Protocols |

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| `ty` passes | ✅ Yes | ✅ Yes |
| IDE autocomplete on flow result | ❌ No | ✅ Yes |
| Type errors on wrong input | ❌ Runtime | ✅ IDE |
| Unbound TypeVars | 4+ | 0 |

## Summary

```
PR #4270:     Internal code → ty passes
This doc:     User code → IDE autocomplete works

PR #4270 laid the foundation. This doc completes the picture.
```
