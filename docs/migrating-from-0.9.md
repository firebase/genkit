# Migrate from 0.9 to 1.0

Genkit 1.0 introduces many feature enhancements that improve overall
functionality; it also has some breaking changes. If you have been developing
applications with Genkit 0.9, you need to update your application code when you
upgrade to the latest version of Genkit. This guide outlines the most
significant changes, and explains how to migrate your existing applications
smoothly.

## Beta APIs

We're introducing an unstable, Beta API channel, and leaving session, chat and Genkit client APIs in beta as we continue to refine them. More specifically, the following functions are currently in the `beta` namespace:

* `ai.chat`
* `ai.createSession`
* `ai.loadSession`
* `ai.currentSession`
* `ai.defineFormat`
* `ai.defineInterrupt`

Note: When using the APIs as part of the Beta API, you may experience breaking
changes outside of SemVer. Breaking changes may occur on minor releases.

**Old:**

```ts
import { genkit } from 'genkit';
const ai = genkit({...})
const session = ai.createSession({ ... })
```

**New:**

```ts
import { genkit } from 'genkit/beta';
const ai = genkit({...})
const session = ai.createSession({ ... })
```

**Old:**

```ts
import { runFlow, streamFlow } from 'genkit/client';
```

**New:**

```ts
import { runFlow, streamFlow } from 'genkit/beta/client';
```

## Introducing new `@genkit-ai/express` package

This new package contains utilities to make it easier to build an Express.js server with Genkit. You can find more details about this on
[this page](https://js.api.genkit.dev/modules/_genkit-ai_express.html).

`startFlowServer` has moved from part of the genkit object to this new
`@genkit-ai/express` package; to use startFlowServer, you must
update your imports.

**Old:**

```ts
const ai = genkit({ ... });
ai.startFlowServer({
  flows: [myFlow1, myFlow2],
});
```

**New:**

```ts
import { startFlowServer } from '@genkit-ai/express';
startFlowServer({
  flows: [myFlow1, myFlow2],
});
```

## Changes to Flows

There are several changes to flows in 1.0:

* `ai.defineStreamingFlow` has been consolidated into `ai.defineFlow`,
* `onFlow` has been replaced by `onCallGenkit`,
* `run` has moved to `ai.run`,
* There are changes to working with auth.

The `run` function for custom trace blocks has moved to part of the `genkit` object; use `ai.run` to invoke it instead.

**Old:**

```ts
ai.defineFlow({name: 'banana'}, async (input) => {
  const step = await run('myCode', async () => {
    return 'something'
  });
})
```

**New:**

```ts
ai.defineFlow({name: 'banana'}, async (input) => {
  const step = await ai.run('myCode', async () => {
    return 'something'
  });
})
```

`ai.defineStreamingFlow` has been removed; use `ai.defineFlow` instead. Also,
`streamingCallback` has moved to a field inside the second argument of the flow
function and is now called `sendChunk`.

**Old:**

```ts
const flow = ai.defineStreamingFlow({name: 'banana'}, async (input, streamingCallback) => {
  streamingCallback({chunk: 1});
})

const {stream} = await flow()
for await (const chunk of stream) {
  // ...
}
```

**New:**

```ts
const flow = ai.defineFlow({name: 'banana'}, async (input, {context, sendChunk}) => {
  sendChunk({chunk: 1});
})

const {stream, output} = flow.stream(input);
for await (const chunk of stream) {
  // ...
}
```

FlowAuth auth is now called context. You can access auth as a field inside context:

**Old:**

```ts
ai.defineFlow({name: 'banana'}, async (input) => {
  const auth = getFlowAuth();
  // ...
})
```

**New:**

```ts
ai.defineFlow({name: 'banana'}, async (input, { context }) => {
  const auth = context.auth;
})
```

`onFlow` moved to `firebase-functions/https` package and has been renamed to
`onCallGenkit`. The following snippet shows an example of how to use it.

**Old**

```ts
import { onFlow } from "@genkit-ai/firebase/functions";

export const generatePoem = onFlow(
  ai,
  {
    name: "jokeTeller",
    inputSchema: z.string().nullable(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (type, streamingCallback) => {
    const { stream, response } = await ai.generateStream(
      `Tell me a longish ${type ?? "dad"} joke.`
    );
    for await (const chunk of stream) {
      streamingCallback(chunk.text);
    }
    return (await response).text;
  }
);
```

**New:**

```ts
import { onCallGenkit } from "firebase-functions/https";
import { defineSecret } from "firebase-functions/params";
import { genkit, z } from "genkit";

const apiKey = defineSecret("GOOGLE_GENAI_API_KEY");

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

export const jokeTeller = ai.defineFlow(
  {
    name: "jokeTeller",
    inputSchema: z.string().nullable(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (type, { sendChunk }) => {
    const { stream, response } = ai.generateStream(
      `Tell me a longish ${type ?? "dad"} joke.`
    );
    for await (const chunk of stream) {
      sendChunk(chunk.text);
    }
    return (await response).text;
  }
);

export const tellJoke = onCallGenkit({ secrets: [apiKey] }, jokeTeller);
```

Auth policies have been removed from `defineFlow`. Handling of auth policies
is now server-dependent.

**Old:**

```ts
export const simpleFlow = ai.defineFlow(
  {
    name: 'simpleFlow',
    authPolicy: (auth, input) => {
      // auth policy
    },
  },
  async (input) => {
    // Flow logic here...
  }
);
```

The following snippet shows an example of handling auth in Express.

**New:**

```ts
import { UserFacingError } from 'genkit';
import { ContextProvider, RequestData } from 'genkit/context';
import { expressHandler, startFlowServer } from '@genkit-ai/express';

const context: ContextProvider<Context> = (req: RequestData) => {
  return {
    auth: parseAuthToken(req.headers['authorization']),
  };
};

export const simpleFlow = ai.defineFlow(
  {
    name: 'simpleFlow',
  },
  async (input, { context }) => {
    if (!context.auth) {
      throw new UserFacingError("UNAUTHORIZED", "Authorization required.");
    }
    if (input.uid !== context.auth.uid) {
      throw new UserFacingError("UNAUTHORIZED", "You may only summarize your own profile data.");
    }
    // Flow logic here...
  }
);

const app = express();
app.use(express.json());
app.post(
  '/simpleFlow',
  expressHandler(simpleFlow, { context })
);
app.listen(8080);

// or

startFlowServer(
  flows: [withContextProvider(simpleFlow, context)],
  port: 8080
);
```

For more details, refer to the [auth documentation](/auth).

The following snippet shows an example of handling auth in Cloud Functions
for Firebase:

```ts
import { genkit } from 'genkit';
import { onCallGenkit } from 'firebase-functions/https';

const ai = genkit({ ... });;

const simpleFlow = ai.defineFlow({
  name: 'simpleFlow',
}, async (input) => {
  // Flow logic here...
});

export const selfSummary = onCallGenkit({
  authPolicy: (auth, data) => auth?.token?.['email_verified'] && auth?.token?.['admin'],
}, simpleFlow);
```


## Prompts

We've made several changes and improvements to prompts.

You can define separate templates for prompt and system messages:

```ts
const hello = ai.definePrompt({
  name: 'hello',
  system: 'talk like a pirate.',
  prompt: 'hello {% verbatim %}{{ name }}{% endverbatim %}',
  input: {
    schema: z.object({
      name: z.string()
    })
  }
});
const { text } = await hello({name: 'Genkit'});
```

Alternatively, you can define multi-message prompts in the messages field:

```ts
const hello = ai.definePrompt({
  name: 'hello',
  messages: '{% verbatim %}{{ role "system" }}{% endverbatim %} talk like a pirate. {% verbatim %}{{ role "user" }}{% endverbatim %} hello {% verbatim %}{{ name }}{% endverbatim %}',
  input: {
    schema: z.object({
      name: z.string()
    })
  }
});
```

Instead of prompt templates you can use a function:

```ts
ai.definePrompt({
  name: 'hello',
  prompt: async (input, { context }) => {
    return `hello ${input.name}`
  },
  input: {
    schema: z.object({
      name: z.string()
    })
  }
});
```

You can access the context (including auth information) from within the prompt:

```ts
const hello = ai.definePrompt({
  name: 'hello',
  messages: 'hello {% verbatim %}{{ @auth.email }}{% endverbatim %}',
});
```



## Streaming functions do not require an `await`


**Old:**

```ts
const { stream, response } = await ai.generateStream(`hi`);
const { stream, output } = await myflow.stream(`hi`);
```

**New:**

```ts
const { stream, response } = ai.generateStream(`hi`);
const { stream, output } = myflow.stream(`hi`);
```



## Embed has a new return type

We've added support for multimodal embeddings. Instead of returning just a
single embedding vector, Embed returns an array of embedding objects, each
containing an embedding vector and metadata.

**Old:**

```ts
const response = await ai.embed({embedder, content, options});  // returns number[]
```

**New:**

```ts
const response = await ai.embed({embedder, content, options}); // returns Embedding[]
const firstEmbeddingVector = response[0].embedding;  // is number[]
```