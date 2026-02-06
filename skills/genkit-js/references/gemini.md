# Gemini

## Installation

To use Gemini models with Genkit, you need to install the Google GenAI plugin:

```bash
npm i @genkit-ai/google-genai
```

and configure it for the Gemini API or Vertex AI API depending on the user's needs:

```ts
import { googleAI } from '@genkit-ai/google-genai'; // for Gemini API
import { vertexAI } from '@genkit-ai/google-genai'; // for Vertex AI API

const ai = genkit({
  // ...
  plugins: [
    googleAI(), // for Gemini API, GEMINI_API_KEY env variable must be set
    vertexAI({ location: 'global' }), // for Vertex AI, Google Application Default Credentials must be available
  ],
});

googleAI.model('gemini-3-flash-preview'); // specify models for Gemini API
vertexAI.model('gemini-3-pro-preview'); // specify models for Vertex AI API
```

## Basic Usage

```ts
import { ai, z } from '...'; // path to genkit instance
import { googleAI } from '@genkit-ai/google-genai';

const { text } = await ai.generate({
  model: googleAI.model('gemini-3-flash-preview'),
  prompt: 'Tell me a story in a pirate accent',
});
```

ALWAYS use `gemini-3-*` or`gemini-2.5-*` series models, they are the best and current generation of Gemini models. NEVER use `gemini-2.0-*` or `gemini-1.5-*` models. For general purpose inference, use one of these models:

- `gemini-3-flash-preview`: balance of speed and performance, good default
- `gemini-3-pro-preview`: most powerful, use for complex prompts
- `gemini-2.5-flash`: GA model with balance of speed/performance
- `gemini-2.5-pro`: GA model for complex prompts
- `gemini-2.5-flash-lite`: GA model for simple prompts

All of these models can accept multi-modal input, but for image or audio output see the available documentation for specialized models.

## Common Usage Scenarios

### Setting Thinking Level (Gemini 3 Models Only)

```ts
const response = await ai.generate({
  model: googleAI.model('gemini-3-pro-preview'),
  prompt: 'what is heavier, one kilo of steel or one kilo of feathers',
  config: {
    thinkingConfig: {
      thinkingLevel: 'HIGH', // Or 'LOW'
      includeThoughts: true, // Include thought summaries
    },
  },
});
```

### Google Search Grounding

When enabled, Gemini models can use Google Search to find current information to answer prompts.

```ts
const response = await ai.generate({
  model: googleAI.model('gemini-2.5-flash'),
  prompt: 'What are the top tech news stories this week?',
  config: {
    googleSearchRetrieval: true,
  },
});

// Access grounding metadata
const groundingMetadata = (response.custom as any)?.candidates?.[0]
  ?.groundingMetadata;
if (groundingMetadata) {
  console.log('Sources:', groundingMetadata.groundingChunks);
```

### Image Generation

See `references/nano-banana.md` for information about using Nano Banana models for image generation and editing.
