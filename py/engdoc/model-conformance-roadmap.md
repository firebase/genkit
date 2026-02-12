# Model Conformance Testing Plan for Python Plugins

> **Status:** Infrastructure + Native Runner Complete (P0–P3 done, P4 pending manual validation)
> **Date:** 2026-02-11 (updated)
> **Owner:** Python Genkit Team
> **Scope:** Phase 1 covers google-genai, anthropic, and compat-oai (OpenAI).
>   All 13 plugins have entry points and specs.  Native test runner replaces
>   genkit CLI dependency.  Unified multi-runtime table.

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

The `conform` tool supports two execution modes:

```
                py/bin/conform check-model [PLUGIN...]
                              |
                     +--------+--------+
                     |                 |
            default (native)    --use-cli (legacy)
                     |                 |
           +---------+---------+       |
           |         |         |       v
        python      js        go    genkit dev:test-model
           |         |         |       |
     InProcess   Reflection  Reflection
      Runner      Runner     Runner
           |         |         |       |
      import    subprocess subprocess subprocess
     entry.py   entry.ts   entry.go   genkit CLI
           |         |         |       |
      action.   async HTTP  async HTTP  |
      arun_raw   reflection  reflection |
           |         |         |       |
           +----+----+----+----+       |
                |         |            |
           10 Validators  |            |
           (1:1 with JS)  |            |
                |         |            |
         Unified Results Table         |
         (Runtime column when          v
          multiple runtimes)    Legacy per-runtime
                                   tables
```

**Native runner (default):**

1. For Python: imports `conformance_entry.py` in-process, calls
   `action.arun_raw()` directly (no subprocess, no HTTP, no genkit CLI).
2. For JS/Go: starts the entry point subprocess, discovers the reflection
   server via `.genkit/runtimes/*.json`, communicates via async HTTP.
3. 10 validators ported 1:1 from the canonical JS source.
4. Results displayed in a unified table with Runtime column.

**Legacy CLI runner (`--use-cli`):**

1. Delegates to `genkit dev:test-model` via subprocess.
2. Discovers the running Python runtime via `.genkit/runtimes/*.json`.
3. Sends standardized test requests via `POST /api/runAction`.
4. Validates responses using built-in validators.

---

## Cross-Runtime Feature Parity Analysis

### Plugins with JS Counterparts

| Plugin | JS Location | JS Models | Python Models | Parity | Gaps in Python | Python Extras |
|--------|-------------|-----------|---------------|--------|----------------|---------------|
| **google-genai** | In-repo `js/plugins/google-genai/` | 24 (Gemini, TTS, Gemini-Image, Gemma, Imagen, Veo) | 23+ (same families) | **Partial** | Imagen under `googleai/` prefix (only registered under `vertexai/`) | More legacy Gemini preview versions |
| **anthropic** | In-repo `js/plugins/anthropic/` | 8 (Claude 3-haiku through opus-4-5) | 8 (identical list and capabilities) | **Full** | None | None |
| **compat-oai** | In-repo `js/plugins/compat-oai/` | 49 (30 chat, 2 image gen, 3 TTS, 3 STT, 3 embed, 2 DeepSeek, 6 xAI) | 30+ (22+ chat, 2 image gen, 3 TTS, 3 STT, 3 embed) | **Full** | Vision (gpt-4-vision*), gpt-4-32k (older models) | DeepSeek/xAI split into dedicated plugins |
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
| **mistral** | 30+ (Large 3, Medium 3.1, Small 3.2, Ministral 3, Magistral, Codestral, Devstral, Voxtral, Pixtral, Embed) | No JS plugin exists. PR #4485: embeddings + streaming fix. PR #4486: full capability update. |
| **huggingface** | 10+ popular models + any HF model ID | No JS plugin exists |
| **cloudflare-workers-ai** | 15+ (Llama, Mistral, Qwen, Gemma, Phi, DeepSeek) | No JS plugin exists |

### Gaps Summary (Ordered by Priority)

| Priority | Plugin | Gap | Impact | Fix Effort |
|----------|--------|-----|--------|------------|
| **HIGH** | google-genai | Imagen under `googleai/` prefix | Blocks spec symlink for conformance tests | Low (~20 lines in `google.py`) |
| ~~MEDIUM~~ | compat-oai | ~~Image gen (dall-e-3, gpt-image-1)~~ | ✅ Done (PR #4477) | -- |
| ~~MEDIUM~~ | compat-oai | ~~TTS (tts-1, tts-1-hd, gpt-4o-mini-tts)~~ | ✅ Done (PR #4477) | -- |
| ~~MEDIUM~~ | compat-oai | ~~STT (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe)~~ | ✅ Done (PR #4477) | -- |
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

### Phase 0: Leaves ✅ COMPLETE

| Task | Description | File(s) | Effort | Status |
|------|-------------|---------|--------|--------|
| `fix-imagen-gap` | GoogleAI already registers Imagen under `googleai/` (verified in code) | `google.py` lines 378-380, 523-527, 596-601 | N/A | ✅ Already done |
| `setup-dir` | Created `py/tests/conformance/` with dirs for all 10 plugins | `py/tests/conformance/{google-genai,anthropic,compat-oai,...}/` | Trivial | ✅ Done |

**Parallelizable:** Yes, both tasks are independent.

### Phase 1: Specs + Entry Points ✅ COMPLETE

| Task | Description | Depends On | File(s) | Status |
|------|-------------|------------|---------|--------|
| `symlink-gemini-spec` | Symlinked JS spec into conformance dir | P0 | `google-genai/model-conformance.yaml` → JS spec | ✅ Done |
| `entry-google-genai` | Minimal google-genai entry point | P0 | `google-genai/conformance_entry.py` | ✅ Done |
| `spec-anthropic` | Anthropic entry point + YAML spec | P0 | `anthropic/{conformance_entry.py,model-conformance.yaml}` | ✅ Done |
| `spec-compat-oai` | compat-oai entry point + YAML spec (gpt-4o, gpt-4o-mini, dall-e-3, tts-1) | P0 | `compat-oai/{conformance_entry.py,model-conformance.yaml}` | ✅ Done (updated with multimodal, PR #4477) |

**Note:** All 10 plugins (including Phase 2 plugins) have entry points and specs.

### Phase 2: Orchestration ✅ COMPLETE

| Task | Description | Depends On | File(s) | Status |
|------|-------------|------------|---------|--------|
| `runner-script` | Shell script to orchestrate per-plugin conformance test runs | All Phase 1 tasks | `py/bin/test-model-conformance` | ✅ Done |

### Phase 2.5: Spec Audit + Model Updates ✅ COMPLETE

| Task | Description | File(s) | Status |
|------|-------------|---------|--------|
| `audit-specs` | Verified all 11 plugin specs against official provider documentation (Feb 11, 2026). Fixed model names, corrected Supports flags, added missing models. Total: 24 models across 11 plugins. | All `model-conformance.yaml` files | ✅ Done |

**Changes made during audit:**

| Plugin | Before | After | Changes |
|--------|--------|-------|---------|
| **anthropic** | 2 models | 4 models | Added claude-sonnet-4-5, claude-opus-4-6 |
| **deepseek** | 1 model (no structured-output) | 2 models | Added structured-output to chat, added deepseek-reasoner (no tools) |
| **xai** | 1 model (grok-3, legacy) | 2 models | Replaced grok-3 → grok-4-fast-non-reasoning, added grok-2-vision-1212 |
| **mistral** | 1 model (no vision) | 2 models | Added vision tests, added mistral-large-latest |
| **amazon-bedrock** | Missing structured-output | Fixed | Added structured-output, streaming-structured-output |
| **cloudflare** | Missing tool-request | Fixed | Added tool-request, streaming-multiturn |
| **ollama** | Missing tool-request, vision | Fixed | Added tool-request, input-image-base64 |

### Phase 3: Validation ⏳ PENDING

| Task | Description | Depends On | File(s) | Status |
|------|-------------|------------|---------|--------|
| `validate-google-genai` | Manual end-to-end validation with live API via `genkit dev:test-model` | `runner-script` | -- (manual run) | ⏳ Not yet run |

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
P2.5:[audit-specs ~~~~~~~~~]
                    |
P3:  [conform tool ~~~~~~~~~~~~~~~]  ← native runner, unified table
                    |
P4:  [validate-google-genai ~~~~]
                    |
     === PHASE 1 SCOPE COMPLETE ===
```

### Phase 3: Conform CLI Tool + Native Runner ✅ COMPLETE

| Task | Description | File(s) | Status |
|------|-------------|---------|--------|
| `conform-cli` | Multi-runtime CLI tool (`py/tools/conform/`) | `cli.py`, `config.py`, `runner.py`, etc. | ✅ Done (PR #4593) |
| `native-runner` | In-process runner for Python, reflection runner for JS/Go | `test_model.py`, `reflection.py` | ✅ Done |
| `validators` | 10 validators ported 1:1 from JS canonical source | `validators/*.py` | ✅ Done |
| `unified-table` | Single table with Runtime column across runtimes | `display.py`, `types.py` | ✅ Done |
| `global-flags` | `--runtime` accepts matrix (e.g., `python go`), shown in subcommand help | `cli.py` | ✅ Done |
| `remove-test-model` | Merged into `check-model` (native runner is default, `--use-cli` for legacy) | `cli.py` | ✅ Done |

### Phase 4: Validation ⏳ PENDING

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

All conformance testing files live under `py/tests/conform/`:

```
py/tests/conform/
  google-genai/
    conformance_entry.py                  # minimal Genkit entry point
    model-conformance.yaml -> symlink     # -> js/plugins/google-genai/tests/model-tests-tts.yaml
  anthropic/
    conformance_entry.py
    model-conformance.yaml                # anthropic-specific spec
  compat-oai/
    conformance_entry.py
    model-conformance.yaml                # openai-specific spec
  ...13 plugins total...
py/tools/conform/                         # conform CLI tool
  src/conform/
    cli.py                                # arg parsing + dispatch
    config.py                             # TOML config loader
    runner.py                             # legacy genkit CLI runner
    test_model.py                         # native runner + ActionRunner Protocol
    reflection.py                         # async HTTP client for reflection API
    validators/                           # 10 validators (1:1 with JS)
py/bin/conform                            # wrapper script
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

### Conform CLI Tool

**Location:** `py/bin/conform` (wrapper) → `py/tools/conform/`

```bash
# Usage:
conform check-model                       # test all plugins, all runtimes
conform check-model anthropic xai         # test specific plugins
conform --runtime python go check-model   # matrix: python + go only
conform check-model --use-cli             # legacy genkit CLI fallback
conform list                              # show readiness table
conform check-plugin                      # lint-time file check
```

The tool:
- Uses the native runner by default (in-process for Python, async HTTP for JS/Go)
- Falls back to `genkit dev:test-model` subprocess with `--use-cli`
- Runs across all configured runtimes by default (`--runtime` for matrix)
- Shows a unified table with Runtime column across runtimes
- Reports aggregate pass/fail and exits non-zero on failure

> **Note:** [`uv`](https://docs.astral.sh/uv/) is the project's standard Python
> package manager and task runner, already used throughout the repository (see
> `py/pyproject.toml` workspace configuration and `py/bin/` scripts). It is
> installed as part of the developer setup via `bin/setup`.

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
| **mistral** | tool-request, structured-output, multiturn, system-role, streaming-multiturn, input-image-base64, input-image-url | All Large 3/Medium 3.1/Small 3.2/Ministral 3/Magistral support vision. Voxtral adds audio input. |
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
