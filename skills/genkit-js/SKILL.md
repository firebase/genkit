---
name: genkit-js
description: Use the Genkit AI SDK to build application features and agents with LLMs and other GenAI models for JavaScript/TypeScript applications. ALWAYS use this skill when writing Genkit code.
license: Apache-2.0
metadata:
  author: Google
---

# Genkit JS

## Installation

If Genkit is not already installed and configured in this application (present in `package.json` and `const ai = genkit(...)` present in the codebase), read `references/setup.md` to install and configure Genkit.

## Basic Example

```ts
import { genkit, z } from "genkit";
// this example uses Gemini, but Genkit supports other provider plugins
import { googleAI } from "@genkit-ai/google-genai";

const ai = genkit({
  plugins: [googleAI()],
  // optional: assign a default model
  model: googleAI.model('gemini-2.5-flash'),
});

const myTool = ai.defineTool({name, description, inputSchema: z.object(...)}, (input) => {...});

const {text} = await ai.generate({
  model: googleAI.model('gemini-2.5-flash'), // optional if default model is configured
  system: "the system instructions", // optional
  prompt: "the content of the prompt",
  // OR, for multi-modal content
  prompt: [{text: "what is this image?"}, {media: {url: "data:image/png;base64,..."}}],
  tools: [myTool],
});

// structured output
const CharacterSchema = z.object({...}); // make sure to use .describe() on fields
const {output} = await ai.generate({
  prompt: "generate an RPG character",
  output: {schema: CharacterSchema},
});
```

## Important API Clarifications

**IMPORTANT:** This app uses Genkit v1.x which has changed significantly from pre-1.0 versions. Important changes include:

```ts
const response = await ai.generate(...);

response.text // CORRECT 1.x syntax
response.text() // INCORRECT pre-1.0 syntax

response.output // CORRECT 1.x syntax
response.output() // INCORRECT pre-1.0 syntax

const {stream, response} = ai.generateStream(...); // IMPORTANT: no `await` needed
for await (const chunk of stream) { } // CORRECT 1.x syntax
for await (const chunk of stream()) { } // INCORRECT pre-1.0 syntax
await response; // CORRECT 1.x syntax
await response(); // INCORRECT pre-1.0 syntax
await ai.generate({..., model: googleAI.model('gemini-2.5-flash')}); // CORRECT 1.x syntax
await ai.generate({..., model: gemini15Pro}); // INCORRECT pre-1.0 syntax

const ai = genkit({...}); // CORRECT 1.x syntax
configureGenkit({...}); // INCORRECT pre-1.0 syntax

ai.defineFlow({...}, (input) => {...}); // CORRECT 1.x syntax
import { defineFlow } from "..."; // INCORRECT pre-1.0 syntax
```

- Use `import {z} from "genkit"` when you need Zod to get an implementation consistent with Genkit.
- When defining Zod schemas, ONLY use basic scalar, object, and array types. Use `.optional()` when needed and `.describe('...')` to add descriptions for output schemas.
- Genkit has many capabilities, make sure to read docs when you need to use them.

## References

- [Using Gemini with Genkit](references/gemini.md): Read this to leverage Google's Gemini models with Genkit, including image generation with Nano Banana and Nano Banana Pro models.

## Online Documentation

In addition to the above, you can read official documentation directly from the Genkit website by using `https://genkit.dev/docs/{topic}.md` as the URL. Available topics include:

- `models`: general information about how to generate content
- `flows`: general information about how to define and use flows
- `tool-calling`: general information about how to define and use tools
- `model-context-protocol`: information about how to use and build MCP servers with Genkit
