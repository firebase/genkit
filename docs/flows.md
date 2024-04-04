# Flows

Flows are functions with some additional characteristics: they are strongly
typed, streamable, locally and remotely callable, and fully observable. Genkit
provides CLI and Developer UI tooling for working with flows (running,
debugging, etc).

## Defining flows

```javascript
import { defineFlow } from '@genkit-ai/flow';

export const myFlow = defineFlow({ name: 'myFlow' }, async (input) => {
  const output = doSomethingCool(input);

  return output;
});
```

Input and output schemas for flows can be defined using `zod`.

```javascript
import { defineFlow } from '@genkit-ai/flow';
import * as z from 'zod';

export const myFlow = defineFlow(
  {
    name: 'myFlow',
    inputSchema: z.object({ subject: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    const output = doSomethingCool(input.subject);

    return output;
  }
);
```

When schema is specified Genkit will validate the schema for inputs and outputs.

## Running flows

Use the `runFlow` function to run the flow:

```js
const response = await runFlow(jokeFlow, 'banana');
```

You can use the CLI to run flows as well:

```posix-terminal
genkit flow:run jokeFlow '"banana"'
```

### Streamed

Here's a simple example of a flow that can stream values from a flow:

```javascript
export const streamer = defineFlow(
  {
    name: 'streamer',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamType: z.object({ count: z.number() }),
  },
  async (count, streamingCallback) => {
    var i = 0;
    if (streamingCallback) {
      for (; i < count; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        streamingCallback({ count: i });
      }
    }
    return `done: ${count}, streamed: ${i} times`;
  }
);
```

Note that `streamingCallback` can be undefined. It's only defined if the
invoking client is requesting streamed response.

To invoke a flow in streaming mode use `streamFlow` function:

```javascript
const response = streamFlow(streamer, 5);

for await (const chunk of response.stream()) {
  console.log('chunk', chunk);
}

console.log('streamConsumer done', await response.output());
```

If the flow does not implement streaming `streamFlow` will behave identically to `runFlow`.

You can use the CLI to stream flows as well:

```posix-terminal
genkit flow:run jokeFlow '"banana"' -s
```

## Deploying flows

If you want to be able to access your flow over HTTP you will need to deploy it
first. Genkit provides integrations for Cloud Functions for Firebase and
Express.js hosts such as Cloud Run.

Deployed flows support all the same features as local flows (like streaming and
observability).

### Cloud Function for Firebase

To use flows with Cloud Functions for Firebase use the `firebase` plugin and replace `defineFlow` with `onFlow`.

```js
import { onFlow, noAuth } from '@genkit-ai/firebase/functions';

export const jokeFlow = onFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    authPolicy: noAuth(),
  },
  async (subject, streamingCallback) => {
    // ....
  }
);
```

### Express.js

To deploy flows using Cloud Run and similar services, define your flows using `defineFlow` and then call `startFlowsServer()`:

```js
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';

export const jokeFlow = defineFlow({ name: 'jokeFlow' }, async (subject) => {
  // ....
});

startFlowsServer();
```

By default `startFlowsServer` will serve all the flows that you have defined in your codebase as HTTP endpoints (e.g. `http://localhost:3400/jokeFlow`).

You can choose which flows are exposed via the flows server. You can specify a custom port (it will use the `PORT` environment variable if set). You can also set CORS settings.

```js
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';

export const flowA = defineFlow({ name: 'flowA' }, async (subject) => {
  // ....
});

export const flowB = defineFlow({ name: 'flowB' }, async (subject) => {
  // ....
});

startFlowsServer({
  flows: [flowB],
  port: 4567,
  cors: {
    origin: '*',
  },
});
```

## Flow observability

Sometimes when using 3rd party SDKs that that are not instrumented for observability, you might want to see them as a separate trace step in the Developer UI. All you need to do is wrap the code in the `run` function.

```js
import { defineFlow, run } from '@genkit-ai/flow';

export const myFlow = defineFlow(
  { name: 'myFlow', inputSchema: z.string(), outputSchema: z.string() },
  async (input) => {
    const output = await run('step-name', async () => {
      return await doSomething(input);
    });
    return output;
  }
);
```
