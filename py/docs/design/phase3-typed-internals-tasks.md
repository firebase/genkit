# Phase 3: Implementation Tasks

## Phase 3a: Typed Logger Wrapper

### Task 1: Create Logger Module
- [ ] Create `py/packages/genkit/src/genkit/core/logging.py`
- [ ] Define `Logger` protocol with all method signatures
- [ ] Implement `get_logger()` function with type cast
- [ ] Add docstrings and type hints

### Task 2: Update Imports - Core Modules
- [ ] `genkit/core/tracing.py`
- [ ] `genkit/core/reflection.py`
- [ ] `genkit/core/registry.py`
- [ ] `genkit/core/flows.py`
- [ ] `genkit/core/action/_action.py`
- [ ] `genkit/core/trace/default_exporter.py`
- [ ] `genkit/core/trace/realtime_processor.py`
- [ ] `genkit/core/trace/adjusting_exporter.py`

### Task 3: Update Imports - AI Modules
- [ ] `genkit/ai/_aio.py`
- [ ] `genkit/ai/_base_async.py`
- [ ] `genkit/ai/_registry.py`
- [ ] `genkit/ai/_runtime.py`

### Task 4: Update Imports - Blocks Modules
- [ ] `genkit/blocks/generate.py`
- [ ] `genkit/blocks/prompt.py`
- [ ] `genkit/blocks/retriever.py`
- [ ] `genkit/blocks/reranker.py`
- [ ] `genkit/blocks/embedding.py`
- [ ] `genkit/blocks/evaluator.py`
- [ ] `genkit/blocks/resource.py`
- [ ] `genkit/blocks/document.py`

### Task 5: Update Imports - Web Modules
- [ ] `genkit/web/manager/_manager.py`
- [ ] `genkit/web/manager/_adapters.py`
- [ ] `genkit/web/manager/signals.py`
- [ ] `genkit/web/manager/_server.py`

### Task 6: Export from Barrel
- [ ] Add export to `genkit/core/__init__.py`
- [ ] Verify import works: `from genkit.core import get_logger`

### Task 7: Verify
- [ ] Run `basedpyright` and count `reportAny` warnings
- [ ] Confirm ~95 logger-related warnings eliminated
- [ ] Run test suite to ensure no regressions

---

## Phase 3b: Typed Registry Lookups

### Task 8: Add Typed Methods to Registry
- [ ] Add `resolve_retriever()` method
- [ ] Add `resolve_indexer()` method  
- [ ] Add `resolve_embedder()` method
- [ ] Add `resolve_reranker()` method
- [ ] Add `resolve_model()` method
- [ ] Add `resolve_evaluator()` method
- [ ] Add `resolve_flow()` method (if applicable)
- [ ] Add `resolve_tool()` method (if applicable)

### Task 9: Update Callers - Retriever
- [ ] `genkit/ai/_aio.py` - `retrieve()` method
- [ ] `genkit/blocks/retriever.py` - internal lookups

### Task 10: Update Callers - Indexer
- [ ] `genkit/ai/_aio.py` - `index()` method

### Task 11: Update Callers - Embedder
- [ ] `genkit/ai/_aio.py` - `embed()` method
- [ ] `genkit/ai/_aio.py` - `embed_many()` method
- [ ] `genkit/blocks/embedding.py` - internal lookups

### Task 12: Update Callers - Reranker
- [ ] `genkit/ai/_aio.py` - `rerank()` method
- [ ] `genkit/blocks/reranker.py` - `rerank()` function

### Task 13: Update Callers - Model
- [ ] `genkit/blocks/generate.py` - model resolution
- [ ] Any other model lookups

### Task 14: Update Callers - Evaluator
- [ ] `genkit/blocks/evaluator.py` - evaluator lookups

### Task 15: Verify
- [ ] Run `basedpyright` and count `reportAny` warnings
- [ ] Confirm ~50 action-response warnings eliminated
- [ ] Run test suite to ensure no regressions
- [ ] Test IDE autocomplete on response fields

---

## Verification Checklist

### Before Implementation
```bash
cd /Users/jeffhuang/Desktop/genkit
py/.venv/bin/basedpyright py/packages/genkit/src 2>&1 | grep -c "reportAny"
# Record baseline: ___
```

### After Phase 3a
```bash
py/.venv/bin/basedpyright py/packages/genkit/src 2>&1 | grep -c "reportAny"
# Expected: baseline - ~95
```

### After Phase 3b
```bash
py/.venv/bin/basedpyright py/packages/genkit/src 2>&1 | grep -c "reportAny"
# Expected: baseline - ~145
```

### Final Verification
- [ ] All tests pass: `pytest py/packages/genkit/tests`
- [ ] IDE autocomplete works for logger methods
- [ ] IDE autocomplete works for action response fields
- [ ] No new runtime errors in sample apps

---

## Commits

### Commit 1: Add typed logger wrapper
```
feat(py): add typed logger wrapper for structlog

- Create genkit/core/logging.py with Logger protocol
- Provides type hints for all logger methods
- Eliminates ~95 reportAny warnings
```

### Commit 2: Update logger imports
```
refactor(py): use typed logger across codebase

- Replace structlog.get_logger() with genkit.core.logging.get_logger()
- No runtime behavior change
```

### Commit 3: Add typed registry lookups
```
feat(py): add typed action lookup methods to Registry

- Add resolve_retriever(), resolve_embedder(), etc.
- Returns fully typed Action[InputT, OutputT, ChunkT]
- Eliminates ~50 reportAny warnings on action responses
```

### Commit 4: Use typed registry lookups
```
refactor(py): use typed registry lookups internally

- Replace resolve_action() calls with typed variants
- Improves type inference for action responses
```
