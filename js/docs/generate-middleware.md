# Generate Middleware

Middleware in Genkit JS allows you to intercept, inspect, and modify the execution of models and tools during a `generate` call.
This is useful for implementing cross-cutting concerns like logging, telemetry, caching, and retry logic.

## Defining Middleware

Genkit provides a `generateMiddleware` helper to create configurable middleware that can be distributed as plugins.

Middleware hooks into different stages of generation:

- `generate`: Wraps the entire generation process (including the tool loop). Called for each tool call iteration.
- `model`: Wraps the call to the model implementation. Called for each model call.
- `tool`: Wraps the execution of independent tool calls. Called once per tool request.

```typescript
import { generateMiddleware } from '@genkit-ai/ai';
import { z } from 'zod';

export const myLogger = generateMiddleware(
  {
    name: 'myLogger',
    configSchema: z.object({
      verbose: z.boolean().optional(),
    }),
  },
  (config) => ({
    async generate(options, ctx, next) {
      if (config?.verbose) {
        console.log(
          'Generate started with options:',
          JSON.stringify(options, null, 2)
        );
      }
      const result = await next(options, ctx);
      if (config?.verbose) {
        console.log('Generate finished:', result);
      }
      return result;
    },
    async model(request, ctx, next) {
      console.log('Model called:', request);
      return next(request, ctx);
    },
    async tool(request, ctx, next) {
      console.log('Tool called:', request.toolRequest.name);
      return next(request, ctx);
    },
    // Inject additional tools into the generation
    tools: [
      // myCustomTool
    ],
  })
);
```

## Usage

You can use the defined middleware directly in your `generate` calls:

```typescript
import { generate } from '@genkit-ai/ai';
import { myLogger } from './my-logger';

await generate({
  model: 'googleai/gemini-1.5-flash',
  prompt: 'Hello',
  use: [myLogger({ verbose: true })],
});
```

## Registering as a Plugin

If you want to register the middleware globally or make it available via the registry (e.g. for inspection tools), you can use the `.plugin()` method:

```typescript
import { genkit } from 'genkit';
import { myLogger } from './my-logger';

const ai = genkit({
  plugins: [
    myLogger.plugin(), // Can pass default config here
  ],
});
```
