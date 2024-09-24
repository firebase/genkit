# Get started

This guide shows you how to get started with Genkit in a Node.js app.

## Prerequisites

This guide assumes that you're familiar with building applications with Node.js.

To complete this quickstart, make sure that your development environment meets the following requirements:

* Node.js v18+  
* npm

## Install Genkit dependencies

Install the following Genkit dependencies to use Genkit in your project:

* `genkit` provides the Genkit CLI and tooling  
* `@genkit-ai/ai` and `@genkit-ai/core` provide Genkit core capabilities  
* `@genkit-ai/googleai` provide access to the Google AI Gemini models

```
npm install genkit @genkit-ai/ai @genkit-ai/core @genkit-ai/googleai
```

## Configure your model API key

For this tutorial, we’ll use the Gemini API which provides a generous free tier and does not require a credit card to get started. To use the Gemini API, you'll need an API key. If you don't already have one, create a key in Google AI Studio.

<a class="button" href="https://makersuite.google.com/app/apikey" target="_blank" rel="noopener noreferrer">Get an API key from Google AI Studio</a>

After you’ve created an API key, set the `GOOGLE_GENAI_API_KEY` environment variable to your key with the following command:

```
export GOOGLE_GENAI_API_KEY=<your API key>
```

Note: While this tutorial uses the Gemini API from AI Studio, Genkit supports a wide variety of model providers including [Gemini from Vertex AI](https://firebase.google.com/docs/genkit/plugins/vertex-ai#generative_ai_models), Anthropic’s Claude 3 models and Llama 3.1 through the [Vertex AI Model Garden](https://firebase.google.com/docs/genkit/plugins/vertex-ai#anthropic_claude_3_on_vertex_ai_model_garden), open source models through [Ollama](https://firebase.google.com/docs/genkit/plugins/ollama), and several other [community-supported providers](https://firebase.google.com/docs/genkit/models#models-supported) like OpenAI and Cohere.

## Import the library

Import the Genkit core libraries and the plugin for the Google AI Gemini APIs.

```javascript
import { generate } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { googleAI, gemini15Flash } from '@genkit-ai/googleai';
```

## Make your first request

Use the `generate` method to generate a text response.

```javascript
// Make sure to include these imports:
// import { generate } from '@genkit-ai/ai';
// import { configureGenkit } from '@genkit-ai/core';
// import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

configureGenkit({ plugins: [googleAI()] });

const result = await generate({
    model: gemini15Flash,
    prompt: 'Tell me a heroic story about a software developer.',
});

console.log(result.text())
```

## Next steps

Now that you’re set up to make model requests with Genkit, learn how to use more Genkit capabilities to build your AI-powered apps and workflows. To get started with additional Genkit capabilities, see the following guides:

* [Developer tools](docs/genkit/devtools): Learn how to set up and use Genkit’s CLI and developer UI to help you locally test and debug your app.  
* [Generating content](/docs/genkit/models): Learn how to use Genkit’s unified generation API to generate text and structured data from any supported model.  
* [Creating flows](docs/genkit/flows): Learn how to use special Genkit functions, called flows, that provide end-to-end observability for workflows and rich debugging from Genkit tooling.  
* [Prompting models](/docs/genkit/prompts): Learn how Genkit lets you treat prompt templates as functions, encapsulating model configurations and input/output schema.