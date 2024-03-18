Project: /genkit/_project.yaml
Book: /genkit/_book.yaml

# Models

Models in Genkit are libraries and abstractions that provide access to various
Google and non-Google LLMs.

Models are fully instrumented for observability and come with tooling
integrations provided by the Genkit Dev UI -- you can try any model using the
model playground.

When working with models in Genkit you first need to configure the model you
want to work with. Model configuration is performed by the plugin system. In
this example you are configuring the VertexAI plugin which provides Gemini
models.

```js
configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ projectId: getProjectId(), location: getLocation() || 'us-central1' }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});
```

Also note that different plugins and models use different methods of
authentication. For example, Vertex API uses Google Auth Library so it can pull
required credentials using Application Default Credentials.

To use models provided by the plugin you can either refer to them by name (e.g.
`'vertex-ai/gemini-1.0-pro'`) or some plugins export model ref objects which
provide additional type info about the model capabilities and options.

```js
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
```

## Supported models

Genkit provides built-in plugins for the following model providers:

### Google Generative AI

```js
import { googleGenAI } from '@genkit-ai/plugin-google-genai';

export default configureGenkit({
  plugins: [
    googleGenAI(),
  ],
 // ...
});
```

The plugin requires that you set `GOOGLE_API_KEY` environment variable with the
API Key which you can get from
[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

The plugin statically exports references to various supported models:

```js
import { geminiPro, geminiProVision } from '@genkit-ai/plugin-google-genai';
```

### Google Vertex AI

```js
import { vertexAI } from '@genkit-ai/plugin-vertex-ai';
import { getProjectId } from '@genkit-ai/common';

export default configureGenkit({
  plugins: [
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
  ],
 // ...
});
```

The plugin requires that you set the `GCLOUD_PROJECT` environment variable with
your Google Cloud project ID. If you're not running your flow from a Google
Cloud environment, you will also need to [set up Google Cloud Default
Application
Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).
On your local dev environment, do this by running:

```posix-terminal
gcloud auth application-default login
```

The plugin statically exports references to various supported models:

```js
import {
  geminiPro,
  geminiProVision,
  textembeddingGecko,
  imagen2
} from '@genkit-ai/plugin-vertex-ai';
```

### OpenAI

```js
import { vertexAI } from '@genkit-ai/plugin-vertex-ai';

export default configureGenkit({
  plugins: [
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
  ],
 // ...
});
```

The plugin requires that you set the OPENAI_API_KEY environment variable with
your OpenAI API Key.

The plugin statically exports references to various supported models:

```js
import { gpt35Turbo, gpt4, gpt4Turbo, gpt4Vision } from '@genkit-ai/plugin-openai';
```

### Ollama

The plugin requires that you first install and run ollama server. You can follow
the instructions on: [https://ollama.com/download](https://ollama.com/download)

You can use the ollama cli to download the model you are interested in, ex.
`ollama pull gemma`

Configure the ollama plugin like this:

```js
import { ollama } from '@genkit-ai/plugin-ollama';

export default configureGenkit({
  plugins: [
     ollama({
      models: [{ name: 'gemma' }],
      serverAddress: 'http://127.0.0.1:11434', // default ollama local port
    }),
  ],
  // ...
});
```

The plugin does not statically export references for models, but you can use
string references for your configured models, ex:

```js
await generate({
  prompt: `Tell me a joke about ${subject}`,
  model: 'ollama/gemma',
  config: {
    temperature: 1,
  },
  streamingCallback: (c) => {
    console.log(c.content[0].text);
  },
});
```

## Working with models

`generate` is a helper function for working with models.

To just call the model:

```javascript
import { generate } from '@genkit-ai/ai/generate';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';

const llmResponse = await generate({
  model: geminiPro,
  prompt: "Tell me a joke."
});

console.log(await llmResponse.text());
```

You can pass in various model options for that model, including custom model for
specific LLM.

```javascript
const response = await generate({
  model: geminiPro,
  prompt,
  config: {
    temperature: 1,
    custom: {
      stopSequences: ["abc"]
    }
  },
});
```

If the model supports multimodal input you can pass in images as input:

```javascript
import { geminiProVision } from '@genkit-ai/plugin-vertex-ai';

const result = await generate({
  model: geminiProVision,
  prompt: [
    { text: 'describe the following image:' },
    { media: { url: imageUrl, contentType: 'image/jpeg' } },
  ],
});
```

or from a local file

```javascript
const result = await generate({
  model: geminiProVision,
  prompt: [
    { text: 'describe the following image:' },
    {
      data: {
        url: fs.readFileSync(__dirname+"/image.jpeg", {encoding:"base64",flag:"r" }),
        contentType: 'image/jpeg'
     }
    },
  ],
});
```

Model also supports tools and function calling. Tool support depends on
specific models.

```javascript
const myTool = action(
  {
    name: "myJoke",
    description: "useful when you need a joke to tell.",
    input: z.object({ subject: z.string() }),
    output: z.string(),
  },
  async (input) => "haha Just kidding no joke! got you"
);

const llmResponse = await generate({
  model: geminiPro,
  prompt: "Tell me a joke.",
  tools: [myTool],
  options: {
    temperature: 0.5,
  },
});
```

This will automatically call the tools in order to fulfill the user prompt.

You can specify `returnToolRequests: true` for manual control of tool calling.

```javascript
const llmResponse = await generate({
  model: geminiPro,
  prompt: "Tell me a joke.",
  tools: [myTool],
  returnToolRequests: true,
  options: {
    temperature: 0.5,
  },
});
```

And you can stream output from models that support it:

```javascript
await generate({
  model: geminiPro,
  prompt: "Tell me a very long joke.",
  streamingCallback: (chunk) => {
    console.log(chunk)
  }
});
```