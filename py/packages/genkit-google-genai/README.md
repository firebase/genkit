# Google GenAI Plugin

This Genkit plugin provides a unified interface for Google AI (Gemini) and Vertex AI models, embedding, and other services.

> **Building with a coding agent? Install the Genkit Python skill first.**
>
> ```bash
> npx skills add genkit-ai/skills --skill developing-genkit-python
> ```
>
> It teaches your agent the current Genkit Python APIs and common gotchas.
> Source, manual install and skills for other languages:
> [genkit-ai/skills](https://github.com/genkit-ai/skills).

## Setup environment

```bash
uv add genkit genkit-google-genai
```

## Configuration

### Google AI (AI Studio)

To use Google AI models, obtain an API key from [Google AI Studio](https://aistudio.google.com/) and set it in your environment:

```bash
export GEMINI_API_KEY='<your-api-key>'
```

### Vertex AI (Google Cloud)

To use Vertex AI models, ensure you have a Google Cloud project and Application Default Credentials (ADC) set up:

```bash
gcloud auth application-default login
```

## Quickstart

```python
from genkit import Genkit
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini_model('gemini-flash-latest'))


@ai.flow()
async def greet(name: str) -> str:
    res = await ai.generate(prompt=f'Say hello to {name}.')
    return res.text
```

## Features

### Dynamic Models

The plugin automatically discovers available models from the API upon initialization. You can use any model name supported by the API (e.g., `GoogleAI.gemini_model('gemini-flash-latest')`, `VertexAI.gemini_model('gemini-3.1-pro-preview')`).

### Typed config

Config classes take flat snake_case keyword arguments, so pyright, pyrefly
and ty check every key. The plugin builds Gemini's nested request objects
(`thinkingConfig`, `speechConfig`, `tools`) when it sends the request. The Dev
UI and `.prompt` files use the same flat fields in camelCase
(`thinkingLevel`); both spellings validate at runtime.

```python
from genkit_google_genai import GeminiConfig, GeminiTtsConfig

# 1. Thinking, safety and grounding on a text model
config = GeminiConfig(
    thinking_level='HIGH',
    include_thoughts=True,
    safety_settings=[{'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_ONLY_HIGH'}],
    google_search=True,
)

# 2. Two voices on a TTS model
tts_config = GeminiTtsConfig(speakers={'Host': 'Kore', 'Chef': 'Puck'}, language_code='en-US')

# 3. Dump the config the way the Dev UI shows it
print(tts_config.model_dump(by_alias=True, exclude_none=True))
# => {'speakers': {'Host': 'Kore', 'Chef': 'Puck'}, 'languageCode': 'en-US'}
```

Choice fields take plain strings. The Literal aliases (`ThinkingLevel`,
`HarmCategory`, `ImageAspectRatio`, ...) export from the package root for
annotating your own code. `safety_settings` entries are `SafetySetting`
TypedDicts: pass a dict literal or `SafetySetting(category=..., threshold=...)`.

Setting any `google_search_*` option turns Google Search on;
`google_search=False` next to an option raises. A nested key such as
`thinkingConfig` raises and names the flat fields that replace it.

Settings that can't be combined raise before anything is sent:

- `thinking_level` with `thinking_budget`, and `voice` with `speakers`. When
  one comes from a model reference default, pass `None` for it on the call.
- `google_search_start_time` without `google_search_end_time`, and
  `file_search_top_k` or `file_search_metadata_filter` without
  `file_search_store_names`.
- Vertex AI only settings on the Gemini API: `google_search_exclude_domains`,
  `google_search_blocking_confidence`, safety `method`, `output_mime_type`,
  `output_compression_quality`, `person_generation`, `prominent_people`.

A cloned (replicated) voice has no flat field; send it through `extra`:

```python
config = GeminiTtsConfig(
    extra={'generationConfig': {'speechConfig': {'voiceConfig': {'replicatedVoiceConfig': {
        'mimeType': 'audio/wav',
        'voiceSampleAudio': sample_b64,
        'consentAudio': consent_b64,
    }}}}},
)
```

### Provider fields the plugin doesn't declare

Gemini, Gemini image, and Veo configs reject keys they don't declare, so a
typo like `temprature` fails before the request is sent. A request field the
schema doesn't declare yet goes in `extra` under its REST wire name. It's
merged over the top of the request body, recursing into nested objects:

```python
from genkit_google_genai import GeminiConfig

config = GeminiConfig.model_validate({
    'temperature': 1.0,
    'extra': {
        'generationConfig': {'newKnob': 1},  # adds one key to generationConfig
        'labels': {'team': 'search'},        # Vertex AI request labels
    },
})
```

`extra` can't set the fields Genkit builds from the request (`contents`,
`systemInstruction`, `tools`, `toolConfig`, the structured-output fields of
`generationConfig`, `cachedContent`); those raise `INVALID_ARGUMENT`.

### Video generation (Veo)

Video is a job, not a round-trip. `generate_operation` hands back a ticket;
`check_operation` is how you find out when the video is ready. When the job
finishes, `operation.output` has a playable `media.url` — Studio sends a
download URL, Vertex often sends the mp4 inline.

**With `GoogleAI`:**

```python
from genkit import Genkit
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()])

operation = await ai.generate_operation(
    model=GoogleAI.veo_model('veo-3.1-fast-generate-preview'),
    prompt='A paper airplane gliding through a bright classroom',
)
while not operation.done:
    operation = await ai.check_operation(operation)
print(operation.output)
```

**With `VertexAI`:**

```python
from genkit import Genkit
from genkit_google_genai import VertexAI

ai = Genkit(plugins=[VertexAI()])

operation = await ai.generate_operation(
    model=VertexAI.veo_model('veo-3.1-generate-001'),
    prompt='A paper airplane gliding through a bright classroom',
)
while not operation.done:
    operation = await ai.check_operation(operation)
print(operation.output)
```

Runnable version: [google-genai-media](https://github.com/genkit-ai/genkit/tree/main/py/samples/google-genai-media).

### Vertex AI Evaluators

Built-in evaluators for assessing model output quality, accessed via `ai.evaluate()`. The VertexAI plugin registers them only when a project resolves (`VertexAI(project=...)` or `GOOGLE_CLOUD_PROJECT`); `VertexAI(api_key=...)` without a project lists none. They authenticate with Application Default Credentials, not `api_key` or `credentials`:

```python
from genkit import BaseDataPoint, Genkit
from genkit_google_genai import VertexAI

ai = Genkit(plugins=[VertexAI(project='my-project')])

# Prepare test dataset
dataset = [
    BaseDataPoint(
        input='Write about AI.',
        output='AI is transforming industries through intelligent automation.',
    ),
]

# Evaluate fluency (scores 1-5)
results = await ai.evaluate(
    evaluator='vertexai/fluency',
    dataset=dataset,
)

for result in results:
    print(f'Score: {result.evaluation[0].score}')
```

Runnable snippets are in [`py/samples`](../../samples).
