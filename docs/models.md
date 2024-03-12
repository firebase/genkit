
# Models

Models in Genkit are very easy to use libraries and abstractions that provide access to various Google and 3P LLMs.

Models are fully instrumented for observability and come with tooling integrations provided via Genkit Dev UI -- you can try any model via the model playground.

When working with Models in Genkit you first need to configure the model you want to work with. Model configuration is performed via the plugin system. In this example we are configuring VertexAI plugin which provides gemini models (refer to plugin documentation to see which models it provides).

```
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

Also note that different pluging and model use different methods of authentication. For example, Vertex API uses [Google Auth Library](https://cloud.google.com/nodejs/docs/reference/google-auth-library/latest) so it can pull required credentials using [Application Default Credentials](https://cloud.google.com/nodejs/docs/reference/google-auth-library/latest#application-default-credentials). To configure a "text" model you just need to run: 


To use models provided by the plugin you can either refer to them by name (e.g. `'vertex-ai/gemini-1.0-pro'`) or some plugins export model ref objects which provide additional type info about the model capabilities and options.

```javascript
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
```

### Working with models

`generate` is a helper function for working with text models.

To simply call the model:

```javascript
import { generate } from '@genkit-ai/ai/generate';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';

const llmResponse = await generate({
  model: geminiPro,
  prompt: "Tell me a joke."
});

console.log(await llmResponse.text());
```

you can pass in various model options for that model, including custom model for specific LLM.

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

Model also supports tools/function calling. Currently tool support depends on specific models.

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

This will automatically call the tools in order to fulfill user prompt.

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
