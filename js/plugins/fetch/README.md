# Genkit Web Fetch Plugin

This plugin provides utilities for exposing Genkit flows and actions over the **Web Fetch API** (`Request` / `Response`). Use it with any runtime or framework that supports the standard Fetch API (such as Hono, Bun, Cloudflare Workers, Deno, Node (18+), Vercel Edge, Netlify Edge, Elysia, SvelteKit, etc).

No framework-specific dependencies; only `genkit` and the standard Web APIs.

## Installation

```bash
npm i @genkit-ai/fetch
```

## Usage (Hono)

### Single flow with `handleFlow`

```ts
import { handleFlow } from '@genkit-ai/fetch';
import { Hono } from 'hono';

const simpleFlow = ai.defineFlow('simpleFlow', async (input, { sendChunk }) => {
  const { text } = await ai.generate({
    model: googleAI.model('gemini-2.0-flash'),
    prompt: input,
    onChunk: (c) => sendChunk(c.text),
  });
  return text;
});

const app = new Hono();
app.all('/simpleFlow', async (c) => handleFlow(c.req.raw, simpleFlow));
```

### Multiple flows with `handleFlows`

Mount several flows under one path; the flow is selected by the request path (e.g. `/api/hello` runs the flow named `hello`):

```ts
import { handleFlows } from '@genkit-ai/fetch';

const flows = [helloFlow, greetingFlow, streamingFlow];

app.all('/api/*', async (c) => handleFlows(c.req.raw, flows, '/api'));
```

Clients call `POST /api/<flowName>` with body `{ "data": <input> }`.

### Auth with context providers

Use a context provider (e.g. for auth) and attach it to a flow with `withFlowOptions`:

```ts
import { UserFacingError } from 'genkit';
import type { ContextProvider, RequestData } from 'genkit/context';
import { handleFlow, handleFlows, withFlowOptions } from '@genkit-ai/fetch';

const authContext: ContextProvider<{ userId: string }> = (req: RequestData) => {
  if (req.headers['authorization'] !== 'Bearer open-sesame') {
    throw new UserFacingError('PERMISSION_DENIED', 'not authorized');
  }
  return { userId: 'authenticated-user' };
};

// Single flow with auth
app.all('/secureFlow', async (c) =>
  handleFlow(c.req.raw, secureFlow, { contextProvider: authContext })
);

// Or wrap the flow for use with handleFlows
const flows = [
  publicFlow,
  withFlowOptions(secureFlow, { contextProvider: authContext }),
];
app.all('/api/*', async (c) => handleFlows(c.req.raw, flows, '/api'));
```

### Durable streaming (Beta)

You can configure flows to use a `StreamManager` so stream state is persisted. Clients can disconnect and reconnect without losing the stream.

Provide a `streamManager` in the options. For development, use `InMemoryStreamManager`:

```ts
import { InMemoryStreamManager } from 'genkit/beta';
import { handleFlow, withFlowOptions } from '@genkit-ai/fetch';

app.all('/myDurableFlow', async (c) =>
  handleFlow(c.req.raw, myFlow, {
    streamManager: new InMemoryStreamManager(),
  })
);

// Or with handleFlows
const flows = [
  withFlowOptions(myFlow, {
    streamManager: new InMemoryStreamManager(),
  }),
];
app.all('/api/*', async (c) => handleFlows(c.req.raw, flows, '/api'));
```

For production, use a durable implementation such as `FirestoreStreamManager` or `RtdbStreamManager` from `@genkit-ai/firebase`, or a custom `StreamManager`.

Clients can reconnect using the `streamId`:

```ts
import { streamFlow } from 'genkit/beta/client';

// Start a new stream
const result = streamFlow({
  url: 'http://localhost:3780/api/myDurableFlow',
  input: 'tell me a long story',
});
const streamId = await result.streamId; // save for reconnect

// Reconnect later
const reconnected = streamFlow({
  url: 'http://localhost:3780/api/myDurableFlow',
  streamId,
});
```

### Calling flows from the client

Use `runFlow` and `streamFlow` from `genkit/beta/client` (same protocol as the Express plugin):

```ts
import { runFlow, streamFlow } from 'genkit/beta/client';

const result = await runFlow({
  url: 'http://localhost:3780/api/hello',
  input: 'world',
});
console.log(result);

// With auth headers
const result = await runFlow({
  url: 'http://localhost:3780/api/secureGreeting',
  headers: { Authorization: 'Bearer open-sesame' },
  input: { name: 'Alex' },
});

// Streaming
const result = streamFlow({
  url: 'http://localhost:3780/api/streaming',
  input: { prompt: 'Say hello in chunks' },
});
for await (const chunk of result.stream) {
  console.log(chunk);
}
console.log(await result.output);
```

## API summary

| Export              | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| `handleFlow(request, action, options?)` | Handles a single flow/action; returns `Promise<Response>`.                  |
| `handleFlows(request, flows, pathPrefix?)` | Dispatches by path to one of the given flows; returns `Promise<Response>`. |
| `withFlowOptions(flow, options)`       | Wraps a flow with `contextProvider`, `streamManager`, or custom `path`.    |
| `FlowWithOptions`   | Type for a flow plus options.                                               |
| `HandleFlowOptions` | Options for `handleFlow`: `contextProvider`, `streamManager`.               |

Request body must be JSON with a `data` field: `{ "data": <input> }`. For streaming, use `Accept: text/event-stream` or query `?stream=true`.

## Contributing

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests there.

More details are in the [Genkit documentation](https://genkit.dev/docs/get-started/).

## License

Licensed under the Apache 2.0 License.
