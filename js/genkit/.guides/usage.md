## Basic Example

```ts
import { genkit, z } from "genkit";
import { googleAI } from "@genkit-ai/google-genai"; // or other model plugin
const ai = genkit({
  plugins: [googleAI()],
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

**IMPORTANT:** This app uses Genkit v1.19 which has changed significantly from pre-1.0 versions. Important changes include:

```ts
// genkit is initialized into an instance
import { genkit, z } from "genkit";
const ai = genkit({plugins: [...]});

// tools, flows, etc. are defined via method calls to the instance
const someFlow = ai.defineFlow({...});
const someTool = ai.defineTool({...});

// methods are called on the initialized instance
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
```

- Use `import {z} from "genkit"` when you need Zod to get an implementation consistent with Genkit.
- When defining Zod schemas, ONLY use basic scalar, object, and array types. Use `.optional()` when needed and `.describe('...')` to add descriptions for output schemas.
- Genkit has many capabilities, ALWAYS read docs when you need to use them.
