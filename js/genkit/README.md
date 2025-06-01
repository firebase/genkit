# Genkit

Genkit is a framework for building AI-powered applications. It provides open source libraries for Node.js and Go, along with tools to help you debug and iterate quickly.

## Prerequisites

This guide assumes that you're familiar with building applications with Node.js.

To complete this quickstart, make sure that your development environment meets
the following requirements:

- Node.js v20+
- npm

## Install Genkit dependencies

Install the following Genkit dependencies to use Genkit in your project:

- `genkit` provides Genkit core capabilities.
- `@genkit-ai/googleai` provides access to the Google AI Gemini models. Check out other plugins: https://www.npmjs.com/search?q=keywords:genkit-plugin

```posix-terminal
npm install genkit @genkit-ai/googleai
```

## Make your first request

Get started with Genkit in just a few lines of simple code.

```ts
// import the Genkit and Google AI plugin libraries
import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

// configure a Genkit instance
const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash, // set default model
});

(async () => {
  // make a generation request
  const { text } = await ai.generate('Hello, Gemini!');
  console.log(text);
})();
```

## Next steps

Now that you’re set up to make model requests with Genkit, learn how to use more
Genkit capabilities to build your AI-powered apps and workflows. To get started
with additional Genkit capabilities, see the following guides:

- [Developer tools](https://genkit.dev/docs/devtools/): Learn how to set up and use
  Genkit’s CLI and developer UI to help you locally test and debug your app.
- [Generating content](https://genkit.dev/docs/models/): Learn how to use Genkit’s unified
  generation API to generate text and structured data from any supported
  model.
- [Creating flows](https://genkit.dev/docs/flows/): Learn how to use special Genkit
  functions, called flows, that provide end-to-end observability for workflows
  and rich debugging from Genkit tooling.
- [Managing prompts](https://genkit.dev/docs/dotprompt/): Learn how Genkit helps you manage
  your prompts and configuration together as code.

Learn more at [https://genkit.dev](https://genkit.dev)

License: Apache 2.0
