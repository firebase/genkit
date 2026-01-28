# Phase 2 Generic Action: Implementation Tasks

This is a step-by-step implementation checklist for a junior engineer. Each task
is scoped to a specific file or area and includes a clear expected outcome.

## Task List

1. **Add typing_extensions dependency**
   - **File:** `py/packages/genkit/pyproject.toml`
   - **Change:** add `typing_extensions>=4.0` to `dependencies`
   - **Why:** needed for `TypeVar(default=...)` and `Never` on Python 3.10

2. **Make `Action` generic with defaults**
   - **File:** `py/packages/genkit/src/genkit/core/action/_action.py`
   - **Change:** add `Generic[InputT, OutputT, ChunkT]` with defaults:
     - `InputT = TypeVar("InputT", default=Any)`
     - `OutputT = TypeVar("OutputT", default=Any)`
     - `ChunkT = TypeVar("ChunkT", default=Never)`
   - **Update signatures:**
     - `run(self, input: InputT | None = None, ...) -> ActionResponse[OutputT]`
     - `arun(self, input: InputT | None = None, ...) -> ActionResponse[OutputT]`
     - `arun_raw(self, raw_input: InputT | None = None, ...) -> ActionResponse[OutputT]`
     - `stream(self, input: InputT | None = None, ...) -> tuple[AsyncIterator[ChunkT], asyncio.Future[ActionResponse[OutputT]]]`

3. **Update registry return types**
   - **File:** `py/packages/genkit/src/genkit/core/registry.py`
   - **Change:** update `register_action` return type to `Action[InputT, OutputT, ChunkT]`
   - **Note:** keep runtime behavior unchanged

4. **Connect FlowWrapper to typed Action**
   - **File:** `py/packages/genkit/src/genkit/ai/_registry.py`
   - **Change:** update `FlowWrapper.__init__` to accept a typed `Action`
   - **Expected:** `FlowWrapper.stream()` returns `AsyncIterator[ChunkT]` and `Future[ActionResponse[OutputT]]`

5. **Fix unbound TypeVars in formatter types**
   - **Files:**
     - `py/packages/genkit/src/genkit/blocks/formats/types.py`
     - `py/packages/genkit/src/genkit/blocks/model.py`
   - **Change:** delete unbound type aliases and inline type vars into generic class signatures:
     - `message_parser: Callable[[MessageWrapper], OutputT]`
     - `chunk_parser: Callable[[GenerateResponseChunkWrapper], ChunkT]`

6. **Add type-checking tests**
   - **Folder:** `tests/typing/`
   - **Files:** create the test files defined in:
     - `py/docs/design/phase2-generic-action-verification.md`
   - **Expected:** type checkers pass for positive tests, fail for negative tests

7. **Add unit tests**
   - **File:** `tests/test_typing_verification.py`
   - **Expected:** all runtime assertions pass

8. **Update CI to run type checkers**
   - **File:** `.github/workflows/python.yml`
   - **Change:** add steps for `pyright`, `mypy`, `ty` using explicit config paths
   - **Expected:** CI fails if negative tests do not error

9. **Run local verification**
   - **Commands:**
     - `pyright --project tests/typing/pyrightconfig.json`
     - `mypy --config-file tests/typing/mypy.ini tests/typing/`
     - `ty check tests/typing/`
     - `pytest tests/test_typing_verification.py -v`
   - **Expected:** all checks pass, negative tests report errors

## Definition of Done

- All tasks above completed
- Type checkers pass on positive tests
- Negative tests produce errors in all checkers
- Unit tests pass
- Reviewer signs off on type-flow improvements

