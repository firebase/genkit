# Model Conformance Testing Plan for Python Plugins

> **Status:** Draft  
> **Date:** 2026-02-06  
> **Owner:** Python Genkit Team  
> **Scope:** Phase 1 covers google-genai, anthropic, and compat-oai (OpenAI)

---

## Problem Statement

The Genkit CLI provides a `genkit dev:test-model` command
([genkit-tools/cli/src/commands/dev-test-model.ts][dev-test-model]) that runs
standardized conformance tests against model providers. This command already
works cross-runtime (JS and Python) via the reflection API, but we have no
Python-side conformance test specs, entry points, or automation to exercise it.

We need to:

1. Verify that Python model provider plugins produce correct responses for the
   same test cases used by JS plugins.
2. Establish a repeatable, per-plugin conformance testing workflow.
3. Identify and close feature parity gaps between Python and JS plugins.

[dev-test-model]: https://github.com/firebase/genkit/blob/main/genkit-tools/cli/src/commands/dev-test-model.ts

---

## Architecture

```
                 py/bin/test-model-conformance
                           |
                           v
               genkit dev:test-model --from-file spec.yaml
                           |
                    discovers runtime
                           |
                           v
                 Reflection Server (:3100)
                           |
                    /api/runAction
                           |
                           v
              Plugin: GoogleAI / Anthropic / etc.
                           ^
                           |
                 conformance_entry.py
```

**How it works:**

1. A lightweight Python entry point (`conformance_entry.py`) initializes Genkit
   with a single plugin and starts the reflection server.
2. The `genkit dev:test-model` JS CLI discovers the running Python runtime via
   `.genkit/runtimes/*.json` discovery files.
3. The CLI sends standardized test requests to models through `POST /api/runAction`.
4. Responses are validated using built-in validators (tool calling, structured
   output, multimodal, streaming, etc.).

---

## Cross-Runtime Feature Parity Analysis

### Plugins with JS Counterparts

| Plugin | JS Location | JS Models | Python Models | Parity | Gaps in Python | Python Extras |
|--------|-------------|-----------|---------------|--------|----------------|---------------|
| **google-genai** | In-repo `js/plugins/google-genai/` | 24 (Gemini, TTS, Gemini-Image, Gemma, Imagen, Veo) | 23+ (same families) | **Partial** | Imagen under `googleai/` prefix (only registered under `vertexai/`) | More legacy Gemini preview versions |
| **anthropic** | In-repo `js/plugins/anthropic/` | 8 (Claude 3-haiku through opus-4-5) | 8 (identical list and capabilities) | **Full** | None | None |
| **compat-oai** | In-repo `js/plugins/compat-oai/` | 49 (30 chat, 2 image gen, 3 TTS, 3 STT, 3 embed, 2 DeepSeek, 6 xAI) | 25+ (22+ chat, 3 embed) | **Partial** | Image gen (dall-e-3, gpt-image-1), TTS, STT, Vision (gpt-4-vision*), gpt-4-32k | DeepSeek/xAI split into dedicated plugins |
| **ollama** | In-repo `js/plugins/ollama/` | Dynamic discovery | Dynamic discovery | **Full** | Cosmetic: JS declares `media=true`, `toolChoice=true`; Python omits | Python declares `output=['text','json']` |
| **amazon-bedrock** | External [aws-bedrock-js-plugin][bedrock-js] | ~35 (Amazon, Claude 2-3.7, Cohere, Mistral, AI21, Llama) | 50+ (all JS models included) | **Python superset** | None | DeepSeek, Gemma, NVIDIA, Qwen, Writer, Moonshot, newer Claude 4.x |
| **microsoft-foundry** | External [azure-foundry-js-plugin][foundry-js] | ~32 chat + DALL-E + TTS + Whisper + embed | 30+ chat + embed + dynamic catalog | **Partial** | DALL-E image gen, TTS, Whisper STT | Claude, DeepSeek, Grok, Llama, Mistral; dynamic Azure catalog (11k+ models) |
| **deepseek** | JS: in `compat-oai` as `deepseek/` prefix | 2 (deepseek-chat, deepseek-reasoner) | 4 (+ deepseek-v3, deepseek-r1) | **Python superset** | None | 2 additional models |
| **xai** | JS: in `compat-oai` as `xai/` prefix | 6 (grok-3 family, grok-2-vision, grok-2-image) | 6 (grok-3 family, grok-4, grok-2-vision) | **Partial** | Image gen (grok-2-image-1212) | grok-4 (newer model) |

[bedrock-js]: https://github.com/genkit-ai/aws-bedrock-js-plugin
[foundry-js]: https://github.com/genkit-ai/azure-foundry-js-plugin

### Python-Only Plugins (no JS counterpart)

| Plugin | Models | Notes |
|--------|--------|-------|
| **mistral** | 11 (Mistral Large/Small, Codestral, Pixtral, Ministral, etc.) | No JS plugin exists |
| **huggingface** | 10+ popular models + any HF model ID | No JS plugin exists |
| **cloudflare-workers-ai** | 15+ (Llama, Mistral, Qwen, Gemma, Phi, DeepSeek) | No JS plugin exists |

### Gaps Summary (Ordered by Priority)

| Priority | Plugin | Gap | Impact | Fix Effort |
|----------|--------|-----|--------|------------|
| **HIGH** | google-genai | Imagen under `googleai/` prefix | Blocks spec symlink for conformance tests | Low (~20 lines in `google.py`) |
| **MEDIUM** | compat-oai | Image gen (dall-e-3, gpt-image-1) | Missing feature category | Medium (new handler) |
| **MEDIUM** | compat-oai | TTS (tts-1, tts-1-hd, gpt-4o-mini-tts) | Missing feature category | Medium (new handler) |
| **MEDIUM** | compat-oai | STT (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe) | Missing feature category | Medium (new handler) |
| **MEDIUM** | microsoft-foundry | DALL-E, TTS, Whisper | Mirrors compat-oai gaps | Medium |
| **LOW** | xai | Image gen (grok-2-image-1212) | Single model missing | Medium (new handler) |
| **LOW** | compat-oai | Vision models (gpt-4-vision*), gpt-4-32k | Older models, multimodal works via gpt-4o | Low (add model defs) |
| **LOW** | ollama | `media`, `toolChoice` metadata | Cosmetic only, no functional impact | Trivial |

---

## Dependency Graph

All tasks for Phase 1 and their dependency relationships:

```
DEPENDENCY GRAPH
================

           +-----------------+       +-----------------+
           | fix-imagen-gap  |       | setup-dir       |
           | (P0)            |       | (P0)            |
           +----+-------+----+       +--+---------+--+-+
                |       |               |         |  |
                |  +----+---------------+         |  |
                |  |    |                         |  |
           +----v--v-+  +----v-----------+  +-----v--+  +-----v--------+
           | symlink |  | entry-         |  | spec-  |  | spec-        |
           | gemini  |  | google-genai   |  | anthr. |  | compat-oai   |
           | (P1)    |  | (P1)           |  | (P1)   |  | (P1)         |
           +----+----+  +-------+--------+  +---+----+  +-----+--------+
                |               |               |              |
                +-------+-------+-------+-------+--------------+
                        |
                   +----v-----------+
                   | runner-script  |
                   | (P2)           |
                   +----+-----------+
                        |
                   +----v-----------+
                   | validate-      |
                   | google-genai   |
                   | (P3)           |
                   +----------------+
```

**Edge list (A -> B means "A must complete before B can start"):**

- `fix-imagen-gap` -> `symlink-gemini-spec`
- `fix-imagen-gap` -> `entry-google-genai`
- `setup-dir` -> `symlink-gemini-spec`
- `setup-dir` -> `entry-google-genai`
- `setup-dir` -> `spec-anthropic`
- `setup-dir` -> `spec-compat-oai`
- `symlink-gemini-spec` -> `runner-script`
- `entry-google-genai` -> `runner-script`
- `spec-anthropic` -> `runner-script`
- `spec-compat-oai` -> `runner-script`
- `runner-script` -> `validate-google-genai`

---

## Phased Execution Plan (Reverse Topological Order)

Execute each phase to completion before starting the next. **All tasks within a
phase are independent and should run in parallel** for fastest completion.

**Critical path:** `fix-imagen-gap` -> `symlink-gemini-spec` -> `runner-script`
-> `validate-google-genai`

### Phase 0: Leaves (no dependencies -- start here)

| Task | Description | File(s) | Effort |
|------|-------------|---------|--------|
| `fix-imagen-gap` | Add `googleai/` Imagen support to Python google-genai plugin (`GoogleAI.init`, `_resolve_model`, `list_actions`) | `py/plugins/google-genai/src/genkit/plugins/google_genai/google.py` | Low (~20 lines) |
| `setup-dir` | Create `py/tests/conformance/` directory tree with subdirectories for each Phase 1 plugin | `py/tests/conformance/{google-genai,anthropic,compat-oai}/` | Trivial |

**Parallelizable:** Yes, both tasks are independent.

### Phase 1: Specs + Entry Points (depends on Phase 0)

| Task | Description | Depends On | File(s) |
|------|-------------|------------|---------|
| `symlink-gemini-spec` | Symlink JS spec into conformance dir | `fix-imagen-gap`, `setup-dir` | `py/tests/conformance/google-genai/model-conformance.yaml` -> `js/plugins/google-genai/tests/model-tests-tts.yaml` |
| `entry-google-genai` | Create minimal google-genai entry point | `fix-imagen-gap`, `setup-dir` | `py/tests/conformance/google-genai/conformance_entry.py` |
| `spec-anthropic` | Create anthropic entry point + YAML spec (claude-sonnet-4, claude-haiku-4-5) | `setup-dir` | `py/tests/conformance/anthropic/{conformance_entry.py,model-conformance.yaml}` |
| `spec-compat-oai` | Create compat-oai entry point + YAML spec (gpt-4o, gpt-4o-mini) | `setup-dir` | `py/tests/conformance/compat-oai/{conformance_entry.py,model-conformance.yaml}` |

**Parallelizable:** Yes, all four tasks are independent once Phase 0 is done.

### Phase 2: Orchestration (depends on Phase 1)

| Task | Description | Depends On | File(s) |
|------|-------------|------------|---------|
| `runner-script` | Create shell script to orchestrate per-plugin conformance test runs | All Phase 1 tasks | `py/bin/test-model-conformance` |

### Phase 3: Validation (depends on Phase 2)

| Task | Description | Depends On | File(s) |
|------|-------------|------------|---------|
| `validate-google-genai` | Manual end-to-end validation with live API via `genkit dev:test-model` | `runner-script` | -- (manual run) |

### Execution Timeline

```
TIME -->
==========================================================================

P0:  [fix-imagen-gap ~~~~~~~~~~~~]  [setup-dir ~~~]
     (parallel)                      (parallel)
                                         |
     --- all P0 complete ----------------+--------
                                         |
P1:  [symlink-gemini-spec ~]  [entry-google-genai ~]
     [spec-anthropic ~~~~~~]  [spec-compat-oai ~~~~]
     (all 4 in parallel)
                    |
     --- all P1 complete ---
                    |
P2:  [runner-script ~~~~~~~~~~~~]
                    |
P3:  [validate-google-genai ~~~~]
                    |
     === PHASE 1 SCOPE COMPLETE ===
```

---

## What To Build

### Prerequisite: Fix Imagen Gap in Python google-genai Plugin

The JS plugin supports Imagen under the `googleai/` prefix but the Python plugin
only registers it under `vertexai/`. The `ImagenModel` class is already
client-agnostic (uses `client.aio.models.generate_images()` which works for
both); only the registration code needs updating.

**File:** `py/plugins/google-genai/src/genkit/plugins/google_genai/google.py`

**Changes (~20 lines):**

1. **`GoogleAI.init()`** -- Add Imagen model loop after Gemini registration:
   ```python
   for name in genai_models.imagen:
       actions.append(self._resolve_model(googleai_name(name)))
   ```
2. **`GoogleAI._resolve_model()`** -- Add Imagen detection branch (mirror
   VertexAI logic):
   ```python
   if clean_name.lower().startswith('imagen'):
       model_ref = vertexai_image_model_info(clean_name)
       model = ImagenModel(clean_name, self._client)
       IMAGE_SUPPORTED_MODELS[clean_name] = model_ref
       config_schema = ImagenConfigSchema
       # ... create and return Action
   ```
3. **`GoogleAI.list_actions()`** -- Include Imagen in discovered actions list:
   ```python
   for name in genai_models.imagen:
       actions_list.append(
           model_action_metadata(
               name=googleai_name(name),
               info=vertexai_image_model_info(name).model_dump(by_alias=True),
               config_schema=ImagenConfigSchema,
           )
       )
   ```

### Directory Layout

All conformance testing files live under `py/tests/conformance/` to avoid
disturbing other runtimes:

```
py/tests/conformance/
  google-genai/
    conformance_entry.py                  # minimal Genkit entry point
    model-conformance.yaml -> symlink     # -> js/plugins/google-genai/tests/model-tests-tts.yaml
  anthropic/
    conformance_entry.py
    model-conformance.yaml                # anthropic-specific spec
  compat-oai/
    conformance_entry.py
    model-conformance.yaml                # openai-specific spec
py/bin/
  test-model-conformance                  # orchestrator shell script
```

### Entry Point Template

Each plugin gets a minimal Python script that initializes Genkit with just that
plugin. The reflection server starts automatically in dev mode (`GENKIT_ENV=dev`,
set by `genkit start`).

```python
"""Minimal entry point for model conformance testing via genkit dev:test-model."""
import asyncio
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI  # varies per plugin

ai = Genkit(plugins=[GoogleAI()])

async def main():
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    ai.run_main(main())
```

### Spec Files

**google-genai:** Symlink to the JS spec file so both runtimes test the same
models with the same expectations:

```bash
# From py/tests/conformance/google-genai/
ln -s "$(git rev-parse --show-toplevel)/js/plugins/google-genai/tests/model-tests-tts.yaml" model-conformance.yaml
```

The JS spec tests:
- `googleai/imagen-4.0-generate-001` (output-image)
- `googleai/gemini-2.5-flash-preview-tts` (custom TTS test)
- `googleai/gemini-2.5-pro` (tool-request, structured-output, multiturn, system-role, image-base64, image-url, video-youtube)
- `googleai/gemini-3-pro-preview` (same + reasoning, streaming, tool-response custom tests)
- `googleai/gemini-2.5-flash` (same as gemini-2.5-pro)

Env: `GEMINI_API_KEY`

**anthropic:** New spec. Models: `anthropic/claude-sonnet-4` and
`anthropic/claude-haiku-4-5`. Tests: tool-request, multiturn, system-role,
input-image-base64, input-image-url, streaming-multiturn, streaming-tool-request.
Haiku-4-5 adds structured-output and streaming-structured-output.

Env: `ANTHROPIC_API_KEY`

**compat-oai (OpenAI):** New spec. Models: `openai/gpt-4o` and
`openai/gpt-4o-mini`. Tests: tool-request, structured-output, multiturn,
system-role, input-image-base64, input-image-url, streaming-multiturn,
streaming-tool-request, streaming-structured-output.

Env: `OPENAI_API_KEY`

### Test Runner Script

**Location:** `py/bin/test-model-conformance`

```bash
#!/usr/bin/env bash
# Usage:
#   py/bin/test-model-conformance google-genai    # test one plugin
#   py/bin/test-model-conformance --all            # test all plugins
```

The script:
- Accepts a plugin name (or `--all`) as argument
- Validates the required env vars are set for that plugin
- Runs: `genkit dev:test-model --from-file <spec> -- uv run <entry_point>`

> **Note:** [`uv`](https://docs.astral.sh/uv/) is the project's standard Python
> package manager and task runner, already used throughout the repository (see
> `py/pyproject.toml` workspace configuration and `py/bin/` scripts). It is
> installed as part of the developer setup via `bin/setup`.
- `dev:test-model` handles process lifecycle (start, wait for runtime, run
  tests, shut down)
- Reports aggregate pass/fail and exits non-zero on failure

### Built-in Test Capabilities

The following test types are available from `dev:test-model` (from
[dev-test-model.ts lines 254-476][dev-test-model]):

| Test | Description |
|------|-------------|
| `tool-request` | Tool/function calling conformance |
| `structured-output` | JSON schema output |
| `multiturn` | Multi-turn conversation |
| `streaming-multiturn` | Streaming + multiturn |
| `streaming-tool-request` | Streaming tool calls |
| `streaming-structured-output` | Streaming structured output |
| `system-role` | System message handling |
| `input-image-base64` | Base64 image input |
| `input-image-url` | URL image input |
| `input-video-youtube` | YouTube video input |
| `output-audio` | TTS/audio output |
| `output-image` | Image generation |

### Built-in Validators

`has-tool-request[:toolName]`, `valid-json`, `text-includes:expected`,
`text-starts-with:prefix`, `text-not-empty`, `valid-media:type`, `reasoning`,
plus streaming variants (`stream-text-includes`, `stream-has-tool-request`,
`stream-valid-json`).

---

## Phase 2 (Future -- after Phase 1 validated)

Add conformance specs for remaining plugins. The parity analysis above informs
which capabilities to test per plugin:

| Plugin | Test Capabilities | Notes |
|--------|-------------------|-------|
| **mistral** | tool-request, structured-output, multiturn, system-role, streaming-multiturn | Pixtral models add input-image-base64, input-image-url |
| **deepseek** | tool-request, structured-output, multiturn, system-role, streaming-multiturn | |
| **xai** | tool-request, structured-output, multiturn, system-role, streaming-multiturn | grok-2-vision adds input-image |
| **ollama** | tool-request, structured-output, multiturn, system-role | Depends on locally installed model |
| **amazon-bedrock** | tool-request, structured-output, multiturn, system-role, streaming-multiturn, input-image-base64 | Model-dependent |
| **huggingface** | tool-request, structured-output, multiturn, system-role | Model-dependent |
| **microsoft-foundry** | tool-request, structured-output, multiturn, system-role, streaming-multiturn, input-image-base64 | Model-dependent |
| **cloudflare-workers-ai** | tool-request, structured-output, multiturn, system-role | Model-dependent |

---

## CI Integration Notes

- These are **live API tests** -- they call real model endpoints. Do NOT run in
  standard CI.
- Gate behind manual trigger or CI label (e.g., `run-conformance-tests`).
- Each plugin requires its own API key/credentials.
- Consider a `--dry-run` mode in the runner script that validates spec files
  parse correctly without making API calls.

---

## Effort Estimates

| Phase | Tasks | Effort | Parallelizable |
|-------|-------|--------|----------------|
| **P0** | 2 tasks (fix-imagen-gap, setup-dir) | ~1 hour | Yes |
| **P1** | 4 tasks (symlink, entry, 2 specs) | ~2 hours | Yes |
| **P2** | 1 task (runner script) | ~1 hour | No |
| **P3** | 1 task (E2E validation) | ~1 hour | No |
| **Total** | 8 tasks | ~3-5 hours (with parallelism) | |
