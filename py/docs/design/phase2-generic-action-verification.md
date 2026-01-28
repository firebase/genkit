# Phase 2 Generic Action: Verification Tests

This document defines automated verification tests for the generic Action implementation.

## Test Matrix

| # | Scenario | Type Check | Unit Test | Notes |
|---|----------|------------|-----------|-------|
| 1 | Flow return type | Yes | Yes | Ensures flow output type is preserved |
| 2 | Tool return type | Yes | Yes | Ensures tool output type is preserved |
| 3 | ActionResponse typing | Yes | Yes | Ensures `response` preserves `OutputT` |
| 4 | Streaming (ChunkT) | Yes | Yes | Ensures stream returns `AsyncIterator[ChunkT]` |
| 5 | Input type validation | Yes | No | Ensures wrong input types are caught |
| 6 | No-input flows | Yes | Yes | Ensures `input: InputT | None = None` works |
| 7 | Negative tests | Yes | No | Ensures type errors ARE caught |
| 8 | Unparameterized Action | Yes | Yes | Ensures backwards compat with defaults |

## Tooling

Run all three type checkers for maximum coverage:

| Tool | Strengths | Config |
|------|-----------|--------|
| `pyright` | Strict, best `reveal_type` output | `pyrightconfig.json` |
| `mypy` | Widely used, catches different edge cases | `mypy.ini` or `pyproject.toml` |
| `ty` | Fast, already in CI | `pyproject.toml` |

### Configuration Files

**`tests/typing/pyrightconfig.json`:**
```json
{
  "include": ["."],
  "typeCheckingMode": "strict",
  "pythonVersion": "3.10",
  "reportMissingTypeStubs": false
}
```

**`tests/typing/mypy.ini`:**
```ini
[mypy]
python_version = 3.10
strict = true
warn_return_any = true
warn_unused_configs = true
plugins = pydantic.mypy

[mypy-genkit.*]
ignore_missing_imports = true
```

---

## Type-Checking Tests

Create `tests/typing/` directory. Run with `pyright tests/typing/`.

### 1. Flow Return Type

**File:** `tests/typing/flow_return_type.py`

```python
from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


@ai.flow()
async def stringify(x: int) -> str:
    return str(x)


class UserInput(BaseModel):
    name: str


@ai.flow()
async def greet(user: UserInput) -> str:
    return f"Hello, {user.name}"


async def main() -> None:
    result = await stringify(123)
    length: int = len(result)  # Should type-check: result is str
    reveal_type(result)  # Expected: str
```

### 2. Tool Return Type

**File:** `tests/typing/tool_return_type.py`

```python
from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


class UserOutput(BaseModel):
    name: str


@ai.tool()
def get_user(name: str) -> UserOutput:
    return UserOutput(name=name)


async def main() -> None:
    output = await get_user("alice")
    upper: str = output.name.upper()  # Should type-check
    reveal_type(output)  # Expected: UserOutput
```

### 3. ActionResponse Typing

**File:** `tests/typing/action_response_type.py`

```python
from __future__ import annotations

from genkit.core.action import Action, ActionRunContext
from genkit.core.action.types import ActionKind, ActionResponse


def int_to_str(x: int) -> str:
    return str(x)


def main() -> None:
    action: Action[int, str] = Action(
        kind=ActionKind.FLOW,
        name="int_to_str",
        fn=int_to_str,
    )
    result = action.run(7)
    reveal_type(result)  # Expected: ActionResponse[str]
    reveal_type(result.response)  # Expected: str
```

### 4. Streaming (ChunkT)

**File:** `tests/typing/stream_type.py`

```python
from __future__ import annotations

from genkit import Genkit
from genkit.core.action import ActionRunContext

ai = Genkit()


@ai.flow()
async def streaming_flow(x: int, ctx: ActionRunContext) -> str:
    for i in range(x):
        ctx.send_chunk(f"chunk-{i}")
    return str(x)


async def main() -> None:
    chunks, final = streaming_flow.stream(5)
    
    async for chunk in chunks:
        reveal_type(chunk)  # Expected: chunk type
    
    result = await final
    reveal_type(result.response)  # Expected: str
```

### 5. Input Type Validation

**File:** `tests/typing/input_type.py`

```python
from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


class UserInput(BaseModel):
    name: str


@ai.flow()
async def greet(user: UserInput) -> str:
    return f"Hello, {user.name}"


async def main() -> None:
    # Valid input - should pass
    result = await greet(UserInput(name="alice"))
    reveal_type(result)  # Expected: str

    # Invalid input cases are covered in negative_tests.py
```

### 6. No-Input Flows

**File:** `tests/typing/no_input_flow.py`

```python
from __future__ import annotations

from genkit import Genkit

ai = Genkit()


@ai.flow()
async def hello_world() -> str:
    return "Hello, World!"


async def main() -> None:
    result = await hello_world()  # No arguments
    reveal_type(result)  # Expected: str
```

### 7. Negative Tests (Should Fail)

**File:** `tests/typing/negative_tests.py`

These tests verify that type errors ARE caught. Run separately and expect errors.

```python
from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


class UserInput(BaseModel):
    name: str


@ai.flow()
async def stringify(x: int) -> str:
    return str(x)


@ai.flow()
async def greet(user: UserInput) -> str:
    return f"Hello, {user.name}"


async def negative_tests() -> None:
    result = await stringify(123)
    
    # ERROR: str is not assignable to int
    wrong_type: int = result
    
    # ERROR: str has no attribute 'nonexistent'
    result.nonexistent

    # ERROR: wrong input type (str instead of UserInput)
    await greet("alice")
```

### 8. Unparameterized Action (Backwards Compat)

**File:** `tests/typing/unparameterized_action.py`

```python
from __future__ import annotations

from genkit.core.action import Action
from genkit.core.action.types import ActionKind


def identity(x: object) -> object:
    return x


def main() -> None:
    # Bare Action without type parameters - should default to Any
    action = Action(
        kind=ActionKind.FLOW,
        name="identity",
        fn=identity,
    )
    result = action.run("anything")
    reveal_type(result)  # Expected: ActionResponse[Any] or ActionResponse[Unknown]
    
    # Should still work at runtime
    value = result.response
    reveal_type(value)  # Expected: Any or Unknown
```

---

## Unit Tests

**File:** `tests/test_typing_verification.py`

```python
from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from genkit import Genkit
from genkit.core.action import Action
from genkit.core.action.types import ActionKind


class UserOutput(BaseModel):
    name: str


class UserInput(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_flow_return_type() -> None:
    """Test 1: Flow return type is preserved at runtime."""
    ai = Genkit()

    @ai.flow()
    async def stringify(x: int) -> str:
        return str(x)

    result = await stringify(123)
    assert result == "123"
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_tool_return_type() -> None:
    """Test 2: Tool return type is preserved at runtime."""
    ai = Genkit()

    @ai.tool()
    def get_user(name: str) -> UserOutput:
        return UserOutput(name=name)

    output = await get_user("alice")
    assert output.name == "alice"
    assert isinstance(output, UserOutput)


def test_action_response_type() -> None:
    """Test 3: ActionResponse preserves OutputT at runtime."""
    def int_to_str(x: int) -> str:
        return str(x)

    action: Action[int, str] = Action(
        kind=ActionKind.FLOW,
        name="int_to_str",
        fn=int_to_str,
    )
    result = action.run(7)
    assert result.response == "7"
    assert isinstance(result.response, str)


@pytest.mark.asyncio
async def test_streaming() -> None:
    """Test 4: Streaming returns chunks and final result."""
    ai = Genkit()
    chunks_received: list[str] = []

    @ai.flow()
    async def streaming_flow(x: int, ctx: ActionRunContext) -> str:
        for i in range(x):
            ctx.send_chunk(f"chunk-{i}")
        return str(x)

    # Test that stream() method exists and works
    stream_iter, final_future = streaming_flow.stream(3)
    
    async for chunk in stream_iter:
        chunks_received.append(str(chunk))
    
    final = await final_future
    assert final.response == "3"
    assert chunks_received == ["chunk-0", "chunk-1", "chunk-2"]


@pytest.mark.asyncio
async def test_no_input_flow() -> None:
    """Test 6: Flows with no input work correctly."""
    ai = Genkit()

    @ai.flow()
    async def hello_world() -> str:
        return "Hello, World!"

    result = await hello_world()
    assert result == "Hello, World!"


def test_unparameterized_action() -> None:
    """Test 8: Bare Action works (backwards compat)."""
    def identity(x: object) -> object:
        return x

    # No type parameters - should use defaults
    action = Action(
        kind=ActionKind.FLOW,
        name="identity",
        fn=identity,
    )
    result = action.run("test")
    assert result.response == "test"
```

---

## How to Run

### Type Checks (All 3 Checkers)

```bash
# Run ALL type checkers
cd tests/typing/

# 1. Pyright (strictest)
pyright .

# 2. Mypy
mypy .

# 3. Ty (fastest)
ty check .

# Or run all three in sequence:
pyright . && mypy . && ty check .
```

### Run Script

Create `tests/typing/run_all_checkers.sh`:

```bash
#!/bin/bash
set -e

echo "=== Running Pyright ==="
pyright .

echo "=== Running Mypy ==="
mypy .

echo "=== Running Ty ==="
ty check .

echo "=== All type checkers passed ==="
```

### Negative Tests (Expect Errors)

```bash
# These should FAIL - validates type safety works
# Run separately and verify errors are produced

pyright --project tests/typing/pyrightconfig.json tests/typing/negative_tests.py 2>&1 | grep -c "error"
# Should output > 0

mypy --config-file tests/typing/mypy.ini tests/typing/negative_tests.py 2>&1 | grep -c "error"
# Should output > 0
```

### Unit Tests

```bash
# Run all verification tests
pytest tests/test_typing_verification.py -v

# Run specific test
pytest tests/test_typing_verification.py::test_flow_return_type -v
```

---

## CI Integration

Add to `.github/workflows/python.yml`:

```yaml
- name: Install type checkers
  run: |
    pip install pyright mypy pydantic

- name: Type check with Pyright
  run: pyright --project tests/typing/pyrightconfig.json

- name: Type check with Mypy
  run: mypy --config-file tests/typing/mypy.ini tests/typing/

- name: Type check with Ty
  run: uv run ty check tests/typing/

- name: Verify negative tests catch errors (Pyright)
  run: |
    if pyright --project tests/typing/pyrightconfig.json tests/typing/negative_tests.py 2>&1 | grep -q "error"; then
      echo "✓ Pyright correctly caught type errors"
    else
      echo "✗ Pyright should have caught errors but didn't"
      exit 1
    fi

- name: Run verification unit tests
  run: pytest tests/test_typing_verification.py -v
```

### Matrix Strategy (Optional)

For parallel execution:

```yaml
jobs:
  type-check:
    strategy:
      matrix:
        checker: [pyright, mypy, ty]
    steps:
      - name: Type check with ${{ matrix.checker }}
        run: |
          case "${{ matrix.checker }}" in
            pyright) pyright tests/typing/ ;;
            mypy) mypy tests/typing/ ;;
            ty) uv run ty check tests/typing/ ;;
          esac
```

---

## Pass/Fail Criteria

### Type Checks (All 3 Must Pass)

| Checker | Requirement |
|---------|-------------|
| `pyright` | Zero errors on all tests (except negative_tests.py) |
| `mypy` | Zero errors on all tests (except negative_tests.py) |
| `ty` | Zero errors on all tests (except negative_tests.py) |

- `negative_tests.py` must produce errors in ALL checkers (validates type safety)
- `reveal_type()` outputs should match expected types

### Unit Tests
- All tests in `test_typing_verification.py` pass
- Runtime behavior matches type annotations

### Overall
- Phase 2 is complete when:
  - All 8 scenarios pass type checking in **all 3 checkers**
  - All unit tests pass
  - Negative tests correctly fail in all checkers
