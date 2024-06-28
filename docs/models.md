# Generating content

Firebase Genkit provides an easy interface for generating content with LLMs.

## Models

Models in Firebase Genkit are libraries and abstractions that provide access to
various Google and non-Google LLMs.

Models are fully instrumented for observability and come with tooling
integrations provided by the Genkit Developer UI -- you can try any model using
the model runner.

When working with models in Genkit, you first need to configure the model you
want to work with. Model configuration is performed by the plugin system. In
this example you are configuring the Vertex AI plugin, which provides Gemini
models.

```js
import { configureGenkit } from '@genkit-ai/core';
import { firebase } from '@genkit-ai/firebase';
import { vertexAI } from '@genkit-ai/vertexai';

configureGenkit({
  plugins: [vertexAI()],
});
```

Note: Different plugins and models use different methods of
authentication. For example, Vertex API uses the Google Auth Library so it can
pull required credentials using Application Default Credentials.

To use models provided by the plugin, you can either refer to them by name (e.g.
`'vertexai/gemini-1.0-pro'`) or some plugins export model ref objects which
provide additional type info about the model capabilities and options.

```js
import { geminiPro } from '@genkit-ai/vertexai';
```

## Supported models

Genkit provides model support through its plugin system. The following plugins
are officially supported:

| Plugin                    | Models                                                                   |
| ------------------------- | ------------------------------------------------------------------------ |
| [Google Generative AI][1] | Gemini Pro, Gemini Pro Vision                                            |
| [Google Vertex AI][2]     | Gemini Pro, Gemini Pro Vision, Gemini 1.5 Flash, Gemini 1.5 Pro, Imagen2 |
| [Ollama][3]               | Many local models, including Gemma, Llama 2, Mistral, and more           |

[1]: plugins/google-genai.md
[2]: plugins/vertex-ai.md
[3]: plugins/ollama.md

See the docs for each plugin for setup and usage information. There's also
a wide variety of community supported models available you can discover by
[searching for packages starting with `genkitx-` on npmjs.org](https://www.npmjs.com/search?q=genkitx).

## How to generate content

`generate` is a helper function for working with models.

To just call the model:

```javascript
import { generate } from '@genkit-ai/ai';
import { geminiPro } from '@genkit-ai/vertexai';

(async () => {
  const llmResponse = await generate({
    model: geminiPro,
    prompt: 'Tell me a joke.',
  });

  console.log(await llmResponse.text());
})();
```

You can pass in various model options for that model, including specifying a
custom model for specific LLMs.

```javascript
const response = await generate({
  model: geminiPro,
  prompt,
  config: {
    temperature: 1,
    stopSequences: ['abc'],
  },
});
```

If the model supports multimodal input, you can pass in images as input:

```javascript
const result = await generate({
  model: geminiProVision,
  prompt: [
    { text: 'describe the following image:' },
    { media: { url: imageUrl, contentType: 'image/jpeg' } },
  ],
});
```

Or from a local file:

```javascript
const result = await generate({
  model: geminiProVision,
  prompt: [
    { text: 'describe the following image:' },
    {
      data: {
        url: fs.readFileSync(__dirname + '/image.jpeg', {
          encoding: 'base64',
          flag: 'r',
        }),
        contentType: 'image/jpeg',
      },
    },
  ],
});
```

### Tools and function calling

`Model` also supports tools and function calling. Tool support depends on
specific models.

```javascript
const myTool = action(
  {
    name: 'myJoke',
    description: 'useful when you need a joke to tell.',
    inputSchema: z.object({ subject: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => 'haha Just kidding no joke! got you'
);

const llmResponse = await generate({
  model: geminiPro,
  prompt: 'Tell me a joke.',
  tools: [myTool],
  config: {
    temperature: 0.5,
  },
});
```

This will automatically call the tools in order to fulfill the user prompt.

You can specify `returnToolRequests: true` for manual control of tool calling.

```javascript
const llmResponse = await generate({
  model: geminiPro,
  prompt: 'Tell me a joke.',
  tools: [myTool],
  returnToolRequests: true,
  config: {
    temperature: 0.5,
  },
});
```

And you can stream output from models that support it:

```javascript
await generate({
  model: geminiPro,
  prompt: 'Tell me a very long joke.',
  streamingCallback: (chunk) => {
    console.log(chunk);
  },
});
```

### Adding retriever context

Documents from a retriever can be passed directly to `generate` to provide
grounding context:

```javascript
const docs = await companyPolicyRetriever({ query: question });

await generate({
  model: geminiPro,
  prompt: `Answer using the available context from company policy: ${question}`,
  context: docs,
});
```

The document context is automatically appended to the content of the prompt
sent to the model.

### Recording message history

Genkit models support maintaining a history of the messages sent to the model
and its responses, which you can use to build interactive experiences, such as
chatbots.

To generate message history from a model response, call the `toHistory()`
method:

```js
let response = await generate({
  model: geminiPro,
  prompt: "How do you say 'dog' in French?",
});
let history = response.toHistory();
```

You can serialize this history and persist it in a database or session storage.
Then, pass the history along with the prompt on future calls to `generate()`:

```js
response = await generate({
  model: geminiPro,
  prompt: 'How about in Spanish?',
  history,
});
history = response.toHistory();
```

If the model you're using supports the `system` role, you can use the initial
history to set the system message:

```ts
let history: MessageData[] = [
  { role: 'system', content: [{ text: 'Talk like a pirate.' }] },
];
let response = await generate({
  model: geminiPro,
  prompt: "How do you say 'dog' in French?",
  history,
});
history = response.toHistory();
```

### Streaming responses

Genkit supports chunked streaming of model responses via the `generateStream()` method:

```ts
// import { generateStream } from '@genkit-ai/ai';
const { response, stream } = await generateStream({
  model: geminiPro,
  prompt: 'Tell a long story about robots and ninjas.',
});

for await (const chunk of stream()) {
  console.log(chunk.text());
}

// you can also await the full response
console.log((await response()).text());
```
