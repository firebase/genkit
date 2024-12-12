# Genkit Express Plugin

This plugin provides utilities for conveninetly exposing Genkit flows and actions via Express HTTP server as REST APIs.

```ts
import { handler } from '@genkit-ai/express';
import express from 'express';

const simpleFlow = ai.defineFlow(
  'simpleFlow',
  async (input, streamingCallback) => {
    const { text } = await ai.generate({
      model: gemini15Flash,
      prompt: input,
      streamingCallback,
    });
    return text;
  }
);

const app = express();
app.use(express.json());

app.post('/simpleFlow', handler(simpleFlow));

app.listen(8080);
```

You can also set auth policies:

```ts
// middleware for handling auth headers.
const authMiddleware = async (req, resp, next) => {
  // parse auth headers and convert to auth object.
  (req as RequestWithAuth).auth = {
    user:
      req.header('authorization') === 'open sesame' ? 'Ali Baba' : '40 thieves',
  };
  next();
};

app.post(
  '/simpleFlow',
  authMiddleware,
  handler(simpleFlow, {
    authPolicy: ({ auth }) => {
      if (auth.user !== 'Ali Baba') {
        throw new Error('not authorized');
      }
    },
  })
);
```

Flows and actions exposed using the `handler` function can be accessed using `genkit/client` library:

```ts
import { runFlow, streamFlow } from 'genkit/client';

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
for await (const chunk of result.stream()) {
  console.log(chunk);
}
console.log(await result.output());
```

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0
