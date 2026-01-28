# Phase 3: Typed Internal APIs

## Overview

This document outlines improvements to eliminate `Any` type warnings in the Genkit Python SDK by:
1. Creating a typed logger wrapper for structlog
2. Adding typed action lookup methods to the registry

These changes will eliminate ~150 type warnings and improve IDE support for internal SDK development.

## Problem Statement

### Current State

Running `basedpyright` on the SDK produces ~620 `reportAny`/`reportExplicitAny` warnings:

| Category | Count | Root Cause |
|----------|-------|------------|
| Structlog logger methods | ~95 | `structlog.get_logger()` returns `Any` |
| Dynamic registry lookup | ~50 | `resolve_action()` loses generic types |
| `dict[str, Any]` metadata | ~100+ | Intentional (idiomatic) |
| `Callable[..., Any]` | ~50+ | Intentional (dynamic callbacks) |

### Impact

1. **IDE noise**: Developers see warnings on nearly every logger call
2. **Hidden bugs**: Real type issues can be masked by the volume of warnings
3. **Reduced confidence**: Hard to trust type checking when there's so much noise

## Solution 1: Typed Logger Wrapper

### Background

`structlog.get_logger()` returns `Any` because it supports dynamic binding of log methods. Every call to `logger.info()`, `logger.debug()`, etc. produces a type warning.

```python
# Current usage - produces warnings
logger = structlog.get_logger(__name__)
logger.info("Starting server")  # Type of "info" is Any
await logger.ainfo("Async log")  # Type of "ainfo" is Any
```

### Proposed Solution

Create a typed protocol and wrapper that provides proper type hints:

```python
# py/packages/genkit/src/genkit/core/logging.py

from typing import Protocol, Any
import structlog

class Logger(Protocol):
    """Protocol defining the logger interface used throughout Genkit."""
    
    def debug(self, event: str, **kw: Any) -> None: ...
    def info(self, event: str, **kw: Any) -> None: ...
    def warning(self, event: str, **kw: Any) -> None: ...
    def error(self, event: str, **kw: Any) -> None: ...
    def exception(self, event: str, **kw: Any) -> None: ...
    
    # Async variants
    async def adebug(self, event: str, **kw: Any) -> None: ...
    async def ainfo(self, event: str, **kw: Any) -> None: ...
    async def awarning(self, event: str, **kw: Any) -> None: ...
    async def aerror(self, event: str, **kw: Any) -> None: ...


def get_logger(name: str | None = None) -> Logger:
    """Get a typed logger instance.
    
    This is a typed wrapper around structlog.get_logger() that provides
    proper type hints for IDE support and type checking.
    
    Args:
        name: Optional logger name (typically __name__).
        
    Returns:
        A typed logger instance.
    """
    # Cast is safe because structlog's BoundLogger implements these methods
    return structlog.get_logger(name)  # type: ignore[return-value]
```

### Migration

Replace all `structlog.get_logger()` calls:

```python
# Before
import structlog
logger = structlog.get_logger(__name__)

# After
from genkit.core.logging import get_logger
logger = get_logger(__name__)
```

### Files to Update

| File | Logger Calls |
|------|--------------|
| `ai/_aio.py` | ~5 |
| `ai/_base_async.py` | ~15 |
| `ai/_registry.py` | ~3 |
| `blocks/generate.py` | ~10 |
| `blocks/prompt.py` | ~8 |
| `core/reflection.py` | ~10 |
| `core/tracing.py` | ~5 |
| `web/manager/*.py` | ~10 |
| **Total** | **~70 files** |

### Expected Impact

- Eliminates ~95 `reportAny` warnings
- No runtime behavior change
- Improves IDE autocomplete for logger methods

---

## Solution 2: Typed Action Registry Lookups

### Background

The registry stores actions by name and returns them via `resolve_action()`:

```python
# Current - loses type information
action = await registry.resolve_action(ActionKind.RETRIEVER, "my-retriever")
# action is Action | None, not Action[RetrieverRequest, RetrieverResponse, Never]

response = await action.arun(request)
# response.response is Any, not RetrieverResponse
```

The generic type parameters (`InputT`, `OutputT`, `ChunkT`) are erased because the registry stores all actions as `Action` without type arguments.

### Proposed Solution

Add typed lookup methods for each action kind that return properly typed actions:

```python
# py/packages/genkit/src/genkit/core/registry.py

from genkit.core.typing import (
    RetrieverRequest, RetrieverResponse,
    IndexerRequest,
    RerankerRequest, RerankerResponse,
    EmbedRequest, EmbedResponse,
    GenerateRequest, GenerateResponse, GenerateResponseChunk,
    EvaluatorRequest, EvaluatorResponse,
)

class Registry:
    # ... existing code ...
    
    # ===== Typed Action Lookups =====
    
    async def resolve_retriever(
        self, name: str
    ) -> Action[RetrieverRequest, RetrieverResponse, Never] | None:
        """Resolve a retriever action by name with full type information.
        
        Args:
            name: The retriever name (e.g., "my-retriever" or "plugin/retriever").
            
        Returns:
            A fully typed retriever action, or None if not found.
        """
        action = await self.resolve_action(ActionKind.RETRIEVER, name)
        if action is None:
            return None
        return cast(Action[RetrieverRequest, RetrieverResponse, Never], action)
    
    async def resolve_indexer(
        self, name: str
    ) -> Action[IndexerRequest, None, Never] | None:
        """Resolve an indexer action by name with full type information."""
        action = await self.resolve_action(ActionKind.INDEXER, name)
        if action is None:
            return None
        return cast(Action[IndexerRequest, None, Never], action)
    
    async def resolve_embedder(
        self, name: str
    ) -> Action[EmbedRequest, EmbedResponse, Never] | None:
        """Resolve an embedder action by name with full type information."""
        action = await self.resolve_action(ActionKind.EMBEDDER, name)
        if action is None:
            return None
        return cast(Action[EmbedRequest, EmbedResponse, Never], action)
    
    async def resolve_reranker(
        self, name: str
    ) -> Action[RerankerRequest, RerankerResponse, Never] | None:
        """Resolve a reranker action by name with full type information."""
        action = await self.resolve_action(ActionKind.RERANKER, name)
        if action is None:
            return None
        return cast(Action[RerankerRequest, RerankerResponse, Never], action)
    
    async def resolve_model(
        self, name: str
    ) -> Action[GenerateRequest, GenerateResponse, GenerateResponseChunk] | None:
        """Resolve a model action by name with full type information."""
        action = await self.resolve_action(ActionKind.MODEL, name)
        if action is None:
            return None
        return cast(
            Action[GenerateRequest, GenerateResponse, GenerateResponseChunk], 
            action
        )
    
    async def resolve_evaluator(
        self, name: str
    ) -> Action[EvaluatorRequest, EvaluatorResponse, Never] | None:
        """Resolve an evaluator action by name with full type information."""
        action = await self.resolve_action(ActionKind.EVALUATOR, name)
        if action is None:
            return None
        return cast(Action[EvaluatorRequest, EvaluatorResponse, Never], action)
```

### Usage After Change

```python
# Before - produces Any warnings
retrieve_action = await registry.resolve_action(ActionKind.RETRIEVER, name)
response = await retrieve_action.arun(request)
return response.response  # Any

# After - fully typed
retrieve_action = await registry.resolve_retriever(name)
response = await retrieve_action.arun(request)
return response.response  # RetrieverResponse
```

### Files to Update

| File | Method | Current Call |
|------|--------|--------------|
| `ai/_aio.py` | `retrieve()` | `resolve_action(RETRIEVER, ...)` |
| `ai/_aio.py` | `index()` | `resolve_action(INDEXER, ...)` |
| `ai/_aio.py` | `embed()` | `resolve_action(EMBEDDER, ...)` |
| `ai/_aio.py` | `rerank()` | `resolve_action(RERANKER, ...)` |
| `blocks/generate.py` | `generate_action()` | `resolve_action(MODEL, ...)` |
| `blocks/reranker.py` | `rerank()` | `resolve_action(RERANKER, ...)` |
| `blocks/retriever.py` | `retrieve()` | `resolve_action(RETRIEVER, ...)` |
| `blocks/embedding.py` | `embed()` | `resolve_action(EMBEDDER, ...)` |

### Expected Impact

- Eliminates ~50 `reportAny` warnings related to action responses
- Provides better IDE support (autocomplete on response fields)
- Makes action kind mismatches a compile-time error

---

## Implementation Plan

### Phase 3a: Typed Logger (Low Risk)

1. Create `genkit/core/logging.py` with `Logger` protocol and `get_logger()`
2. Update all files to import from `genkit.core.logging`
3. Export from `genkit.core` barrel
4. Run type checker to verify ~95 warnings eliminated

**Estimated effort**: 1-2 hours  
**Risk**: Very low (pure typing change, no runtime impact)

### Phase 3b: Typed Registry Lookups (Medium Risk)

1. Add typed lookup methods to `Registry` class
2. Update internal callers to use typed methods
3. Keep `resolve_action()` for backward compatibility
4. Run type checker to verify ~50 warnings eliminated

**Estimated effort**: 2-3 hours  
**Risk**: Low (adds new methods, doesn't change existing ones)

### Verification

After both phases:

```bash
# Before
basedpyright py/packages/genkit/src 2>&1 | grep -c "reportAny"
# ~276

# After  
basedpyright py/packages/genkit/src 2>&1 | grep -c "reportAny"
# ~130 (remaining are intentional dict[str, Any], Callable[..., Any], etc.)
```

---

## Remaining `Any` Usage (Intentional)

After these changes, the remaining `Any` warnings will be intentional:

| Pattern | Reason |
|---------|--------|
| `dict[str, Any]` | Metadata/config dictionaries have dynamic keys |
| `Callable[..., Any]` | Dynamic callbacks with varying signatures |
| `*args: Any` | Wrapper functions forwarding arbitrary args |
| `Coroutine[Any, Any, T]` | Standard coroutine typing pattern |

These should be accepted as idiomatic Python for a dynamic SDK.

---

## Alternatives Considered

### 1. Disable `reportAny` Rule

**Pros**: Quick, no code changes  
**Cons**: Hides real issues, reduces type safety  
**Decision**: Rejected - prefer fixing root causes

### 2. Use `# type: ignore` Comments

**Pros**: Targeted suppression  
**Cons**: Hundreds of comments, maintenance burden  
**Decision**: Rejected - too noisy

### 3. Full Generic Preservation in Registry

**Pros**: Perfect type safety  
**Cons**: Would require runtime type metadata, complex  
**Decision**: Rejected - typed lookup methods are simpler

---

## Success Criteria

1. `reportAny` warnings reduced from ~276 to ~130
2. No runtime behavior changes
3. All existing tests pass
4. IDE autocomplete works for:
   - Logger methods (`logger.info()`, etc.)
   - Action responses (`response.response.embeddings`, etc.)
