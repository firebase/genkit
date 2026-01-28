# Typing Evaluation Sample

Demonstrates the difference between typed and untyped code in Genkit.

## The Problem

The current `Action` class uses `object` instead of generic types:

```python
class Action:  # ❌ Not Generic[InputT, OutputT]
    def run(self, input: object) -> ActionResponse:  # ❌ Untyped
```

This means users get no IDE autocomplete on flow results.

## Run the Examples

```bash
# See runtime errors from untyped code
python src/before_typing.py

# See how generics preserve type info  
python src/after_typing.py
```

## Visual Comparison

```
WITHOUT GENERICS              WITH GENERICS
─────────────────────────────────────────────────
result = action.run(x)        result = action.run(x)
result.response.???           result.response.name ✓
       │                             │
       └── Any (no help)             └── User (autocomplete!)
```

## The Fix

Make `Action` generic:

```python
class Action(Generic[InputT, OutputT, ChunkT]):
    def run(self, input: InputT) -> ActionResponse[OutputT]:
        ...
```
