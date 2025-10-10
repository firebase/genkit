# Genkit Express Plugin

This plugin provides utilities for conveninetly exposing Genkit flows and actions via Express HTTP server as REST APIs.

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
    model: gemini15Flash,
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

## Contributing

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [official Genkit documentation](https://genkit.dev/docs/get-started/).

## License

Licensed under the Apache 2.0 License.
