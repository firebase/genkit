# Flows

Flows are functions with some additional characteristics: they are strongly
typed, streamable, locally and remotely callable, and fully observable. Genkit
provides CLI and Dev UI tooling for working with flows (running, debugging,
etc).

## Defining flows

```javascript
import * as z from 'zod';
import { defineFlow } from '@genkit-ai/flow';

export const myFlow = defineFlow(
  { name: 'myFlow', inputSchema: z.string(), outputSchema: z.string() },
  async (input) => {
    const output = doSomethingCool(input);

    return output;
  }
);
```

Input and output schemas for flows are defined using `zod`.

## Running flows

There are a couple main ways to run flows:

### Direct invocation

This will invoke the flow and block until the flow is finished:

```js
const response = await runFlow(jokeFlow, 'banana');
```

You can use the CLI to run flows as well:

```posix-terminal
npx genkit flow:run jokeFlow '"banana"'
```

### Streamed

Similar to "direct invocation" you can also stream the flow response, if the
flow streams any values.

```javascript
const response = streamFlow(streamer, 5);

for await (const chunk of response.stream()) {
  console.log('chunk', chunk);
}

console.log('streamConsumer done', await response.operation());
```

You can use the CLI to stream flows as well:

```posix-terminal
npx genkit flow:run jokeFlow '"banana"' -s
```

Here's a simple example of a flow that can stream values:

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
invoking client is doing streaming.

## Deploying flows

If you want to be able to access your flow over HTTP you will need to deploy it
first. Genkit provides integrations for Cloud Functions for Firebase and
express.js hosts such as Cloud Run.

To use flows with Cloud Functions for Firebase use the `firebase` plugin
and replace `flow` with `onFlow`.

```js
import { onFlow, noAuth } from '@genkit-ai/plugin-firebase/functions';

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

To deploy flows using Cloud Run and similar services, define your flows with
`flow` and then call `startFlowsServer()`:

```js
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';

export const jokeFlow = defineFlow(
  { name: 'jokeFlow', inputSchema: z.string(), outputSchema: z.string() },
  async (subject, streamingCallback) => {
    // ....
  }
);

startFlowsServer();
```

Deployed flows support all the same features as local flows (like streaming and
observability).

Sometimes when using 3rd party SDKs that that are not instrumented for
observability, you might want to still see them as a separate step in the Dev
UI. All you need to do is wrap the code in the `run` function.

```js
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
