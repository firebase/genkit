# RFC: Adding `mode` parameter to `GenerateOptions`

## Overview

This RFC proposes adding an optional `mode` parameter to Genkit's `GenerateOptions` (specifically, to the `generate()` method API). The `mode` parameter will allow developers to explicitly state whether they intend to run a model in `foreground` mode (yielding a synchronous or streamed response) or in `background` mode (yielding a long-running operation).

## Motivation

Currently, Genkit allows users to call `ai.generate()` and implicitly routes the request based on the capabilities of the requested model. If a model supports synchronous/streaming responses, Genkit runs it in "foreground" mode. If it only supports long-running operations, Genkit automatically falls back to running it in "background" mode.

Currently all of our supported models can run in either foreground mode or background mode, but none have the capability to do both. While this automatic mode detection based on model capability elegantly supports models that can exclusively run in only one mode, it presents ambiguity for the future. As models become more versatile, it is highly likely that certain models will have the capability to run in *either* foreground or background modes under the exact same model name.

If a model supports both execution modes, Genkit's current automatic resolution will always default to the foreground mode. This leaves the user with no intuitive way to explicitly invoke the background variant using the standard `generate()` function. By introducing an explicit `mode` parameter, we give developers full control over their desired execution behavior without breaking existing automatic routing patterns.

## Public API Proposal

### Extend `GenerateOptions`
We propose adding a new `mode` field to the main `generate()` configuration object:

```typescript
export interface GenerateOptions {
  // ... existing fields
  /**
   * The mode to run the model in ('foreground' vs. 'background').
   * If not provided, it defaults to the model's standard execution mode,
   * typically 'foreground' unless only a 'background' variant exists.
   */
  mode?: 'foreground' | 'background';
}
```

This single parameter grants the developer full control over how Genkit routes their model request, acting as an explicit override to the default fallback behavior.

## Usage Examples

**Example 1: Existing Behavior for Foreground Models (Unchanged)**
```typescript
// 'foreground-only-model' is only capable of running in the foreground.
// Because mode is undefined, it correctly uses the foreground capability.
const { text } = await ai.generate({
  model: 'foreground-only-model',
  prompt: 'Write a quick poem'
});
```

**Example 2: Existing Behavior for Background Models (Unchanged)**
```typescript
// 'background-only-model' is only capable of running in the background.
// Because mode is undefined, it automatically falls back to using the background capability.
const { operation } = await ai.generate({
  model: 'background-only-model',
  prompt: 'Perform a heavy generation task'
});
```

**Example 3: Default Behavior for Versatile Models**
```typescript
// 'versatile-model' is capable of running in both foreground and background.
// Because mode is undefined, Genkit defaults to using the foreground capability.
const { text } = await ai.generate({
  model: 'versatile-model',
  prompt: 'Write a quick summary'
});
```

**Example 4: Explicit Mode Specification for Versatile Models**
```typescript
// 'versatile-model' is capable of running in both foreground and background.

// Explicitly request the background execution mode:
const { operation } = await ai.generate({
  model: 'versatile-model',
  mode: 'background',
  prompt: 'A very large text generation task'
});

// Explicitly request the foreground execution mode:
const { text } = await ai.generate({
  model: 'versatile-model',
  mode: 'foreground',
  prompt: 'A very short text generation task'
});
```

## Backwards Compatibility

This change is entirely backwards compatible.
- Existing applications that omit the `mode` parameter will seamlessly continue utilizing the existing fallback resolution sequence. Standard foreground models will resolve correctly (as they are checked first), and background models will continue to resolve successfully via the fallback.
- This represents a non-breaking API addition that prepares Genkit for more complex, versatile model definitions in the future.

---

## Internal Implementation Details

*This section details the architectural changes required under the hood to support the new `mode` parameter.*

### 1. Update Resolution Logic (`resolveModel` & Registry Paths)
Under the hood, Genkit registers foreground models at the `/model/{name}` path and background models at the `/background-model/{name}` path.

The internal model lookup utilities (`resolveModel` and `lookupModel` in `js/ai/src/model.ts`) must be updated to respect the `mode` parameter:
- If `mode: 'foreground'` is passed, it strictly targets the `/model/{name}` registry path.
- If `mode: 'background'` is passed, it strictly targets the `/background-model/{name}` registry path.
- If `mode` is `undefined`, it maintains the legacy automatic fallback chain (try `/model/` first, then `/background-model/`).

### 2. Update `generateOperation()`
The `generateOperation()` utility currently wraps `generate()` but requires a background model. It will be updated to explicitly pass `mode: 'background'` into `resolveModel()` to ensure it reliably fetches the long-running variant if a versatile model is requested.

### 3. Plumb through Action Options
Because Genkit serializes execution options across process boundaries (via `GenerateActionOptionsSchema` in `js/ai/src/model-types.ts`), the `mode` property must be appended to this Zod schema. This guarantees that when the root `generate()` calls into internal helper utilities like `generateHelper`, the exact mode intent is preserved and applied during deep model resolution.
