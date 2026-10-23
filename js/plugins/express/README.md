# Genkit Express Plugin

This plugin provides utilities for conveninetly exposing Genkit flows and actions via Express HTTP server as REST APIs.

> **Building with a coding agent? Install the Genkit JS skill first.**
>
> ```bash
> npx skills add genkit-ai/skills --skill developing-genkit-js
> ```
>
> It teaches your agent the current Genkit JS APIs and common gotchas.
> Source, manual install and skills for other languages:
> [genkit-ai/skills](https://github.com/genkit-ai/skills).

See [official documentation](https://genkit.dev/docs/frameworks/express/) for more.

## Installation

To use this plugin, install it in your project:

```bash
npm i @genkit-ai/express
```

## Usage

```ts
import { expressHandler } from '@genkit-ai/express';
import express from 'express';

const simpleFlow = ai.defineFlow('simpleFlow', async (input, { sendChunk }) => {
  const { text } = await ai.generate({
    model: googleAI.model('gemini-flash-latest'),
    prompt: input,
    onChunk: (c) => sendChunk(c.text),
  });
  return text;
});

const app = express();
app.use(express.json());

app.post('/simpleFlow', expressHandler(simpleFlow));

app.listen(8080);
```

You can also handle auth using context providers:

```ts
import { UserFacingError } from 'genkit';
import { ContextProvider, RequestData } from 'genkit/context';

const context: ContextProvider<Context> = (req: RequestData) => {
  if (req.headers['authorization'] !== 'open sesame') {
    throw new UserFacingError('PERMISSION_DENIED', 'not authorized');
  }
  return {
    auth: {
      user: 'Ali Baba',
    },
  };
};

app.post(
  '/simpleFlow',
  authMiddleware,
  expressHandler(simpleFlow, { context })
);
```

### Durable Streaming (Beta)

You can configure flows to use a `StreamManager` to persist their state. This allows clients to disconnect and reconnect to a stream without losing its state.

To enable durable streaming, provide a `streamManager` in the `expressHandler` options. The `InMemoryStreamManager` is useful for development and testing:

```ts
import { InMemoryStreamManager } from 'genkit/beta';

// ...

app.post(
  '/myDurableFlow',
  expressHandler(myFlow, {
    streamManager: new InMemoryStreamManager(),
  })
);
```

For production environments, you should use a durable `StreamManager` implementation, such as `FirestoreStreamManager` or `RtdbStreamManager` from the `@genkit-ai/firebase` plugin, or a custom implementation.

Clients can then connect and reconnect to the stream using the `streamId`:

```ts
// Start a new stream
const result = streamFlow({
  url: `http://localhost:8080/myDurableFlow`,
  input: 'tell me a long story',
});
const streamId = await result.streamId; // Save this ID

// ... later, reconnect if needed ...
const reconnectedResult = streamFlow({
  url: `http://localhost:8080/myDurableFlow`,
  streamId: streamId,
});
```

Flows and actions exposed using the `expressHandler` function can be accessed using `genkit/beta/client` library:

```ts
import { runFlow, streamFlow } from 'genkit/beta/client';

const result = await runFlow({
  url: `http://localhost:${port}/simpleFlow`,
  input: 'say hello',
});

console.log(result); // hello

// set auth headers (when using auth policies)
const result = await runFlow({
  url: `http://localhost:${port}/simpleFlow`,
  headers: {
    Authorization: 'open sesame',
  },
  input: 'say hello',
});

console.log(result); // hello

// and streamed
const result = streamFlow({
  url: `http://localhost:${port}/simpleFlow`,
  input: 'say hello',
});
for await (const chunk of result.stream) {
  console.log(chunk);
}
console.log(await result.output);
```

### Initialization Data

If your flow or action accepts initialization data (defined via `initSchema`), you can pass it using the `init` option in the client:

```ts
const result = await runFlow({
  url: `http://localhost:${port}/myFlow`,
  input: 'say hello',
  init: { sessionId: 'abc123', config: { temperature: 0.7 } },
});

// Also works with streaming
const streamed = streamFlow({
  url: `http://localhost:${port}/myFlow`,
  input: 'say hello',
  init: { sessionId: 'abc123' },
});
for await (const chunk of streamed.stream) {
  console.log(chunk);
}
console.log(await streamed.output);
```

The `init` data is sent in the request body alongside `data` and is validated against the action's `initSchema` on the server side. If the `init` data does not conform to the `initSchema`, the request fails with a `400 INVALID_ARGUMENT` error before the flow runs.

You can also use `startFlowServer` to quickly expose multiple flows and actions:

```ts
import { startFlowServer } from '@genkit-ai/express';
import { genkit } from 'genkit';

const ai = genkit({});

export const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
  },
  async (restaurantTheme) => {
    // ...
  }
);

startFlowServer({
  flows: [menuSuggestionFlow],
});
```

You can also configure the server:

```ts
startFlowServer({
  flows: [menuSuggestionFlow],
  port: 4567,
  cors: {
    origin: '*',
  },
});
```

### Agents (Beta)

`serveAgent` returns an Express router that serves an agent in the layout `remoteAgent` expects:

```ts
import { serveAgent } from '@genkit-ai/express/beta';

app.use('/api', serveAgent(weatherAgent, { contextProvider }));
```

`serveAgents` serves several agents from one router, each at `/{agent name}`, with one `contextProvider` for all of them. It throws if two agents would serve the same route. For a custom path or a provider per agent, use `serveAgent`.

```ts
import { serveAgents } from '@genkit-ai/express/beta';

app.use(
  '/api',
  serveAgents([weatherAgent, researchAgent], { contextProvider })
);
```

It mounts only the routes the agent supports. `path` defaults to `/{agent name}`:

| Route                         | Action                                                     | Mounted when                          |
| ----------------------------- | ---------------------------------------------------------- | ------------------------------------- |
| `POST {path}`                 | the agent (one turn per request, `?stream=true` supported) | always                                |
| `POST {path}/getSnapshot`     | `getSnapshotDataAction`                                    | server-managed (has a store)          |
| `POST {path}/waitForSnapshot` | `waitForSnapshotAction`                                    | server-managed (has a store)          |
| `POST {path}/abort`           | `abortAgentAction`                                         | the store can signal the running turn |

The `contextProvider` applies to every route of the agent. The router parses JSON bodies itself, so `app.use(express.json())` is optional. A client connects with `remoteAgent({ url: '/api/weatherAgent' })` and needs no other URL options.

When you migrate from `expressHandler`, a provider typed for the turn route (`ContextProvider<C, AgentInput>`) does not compile, because the companion routes send it `{ snapshotId }`. Type its input as `ServeAgentRequest`, or leave it untyped.

The provider runs before input validation, and it cannot tell the companion routes apart: `getSnapshot`, `waitForSnapshot` and `abort` all receive `{ snapshotId }`. To allow reads but deny aborts, check snapshot ownership in the session store, which receives the context, or mount each route with its own `expressHandler`.

The JSON body limit is body-parser's default of 100kb, as with `startFlowServer`. An agent without a store gets its full conversation in every request, so a long conversation reaches the limit and the turn fails with HTTP 413. Raise the turn route's limit with `jsonParserOptions`:

```ts
app.use(
  '/api',
  serveAgent(weatherAgent, { jsonParserOptions: { limit: '5mb' } })
);
```

`jsonParserOptions` applies only to the turn route, and only to requests whose body no earlier middleware has parsed. The companion routes keep the default. If the app runs `express.json()` first, set the limit there instead.

The router answers `OPTIONS` requests to its routes itself. Mount `cors()`, and other middleware that must see preflight requests, before `serveAgent`:

```ts
app.use(cors());
app.use('/api', serveAgent(weatherAgent));
```

To serve a companion route that `serveAgent` does not mount, mount its action with `expressHandler`.

## Contributing

The sources for this package are in the main [Genkit](https://github.com/genkit-ai/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [official Genkit documentation](https://genkit.dev/docs/get-started/).

## License

Licensed under the Apache 2.0 License.
