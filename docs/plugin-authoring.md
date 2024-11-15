# Writing Genkit plugins

Firebase Genkit's capabilities are designed to be extended by plugins. Genkit plugins are configurable modules
that can provide models, retrievers, indexers, trace stores, and more. You've already seen plugins in
action just by using Genkit:

```ts
import { genkit } from 'genkit';
import { vertexAI } from '@genkit-ai/vertexai';

const ai = genkit({
  plugins: [vertexAI({ projectId: 'my-project' })],
});
```

The Vertex AI plugin takes configuration (such as the user's Google Cloud
project ID) and registers a variety of new models, embedders, and more with the
Genkit registry. The registry powers Genkit's local UI for running and
inspecting models, prompts, and more as well as serves as a lookup service for
named actions at runtime.

## Creating a Plugin

To create a plugin you'll generally want to create a new NPM package:

```posix-terminal
mkdir genkitx-my-plugin

cd genkitx-my-plugin

npm init -y

npm i --save genkit

npm i --save-dev typescript

npx tsc --init
```

Then, define and export your plugin from your main entry point:

```ts
import { Genkit, z } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';

interface MyPluginOptions {
  // add any plugin configuration here
}

export function myPlugin(options?: MyPluginOptions) {
  return genkitPlugin('myPlugin', async (ai: Genkit) => {
    ai.defineModel(...);
    ai.defineEmbedder(...)
    // ....
  });
};
```

### Plugin options guidance

In general, your plugin should take a single `options` argument that includes
any plugin-wide configuration necessary to function. For any plugin option that
requires a secret value, such as API keys, you should offer both an option and a
default environment variable to configure it:

```ts
import { Genkit, z } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { GenkitError } from '@genkit-ai/core';

interface MyPluginOptions {
  apiKey?: string;
}

export function myPlugin(options?: MyPluginOptions) {
  return genkitPlugin('myPlugin', async (ai: Genkit) => {
    if (!apiKey)
      throw new GenkitError({
        source: 'my-plugin',
        status: 'INVALID_ARGUMENT',
        message:
          'Must supply either `options.apiKey` or set `MY_PLUGIN_API_KEY` environment variable.',
      });

    ai.defineModel(...);
    ai.defineEmbedder(...)
    
    // ....
  });
};
```

## Building your plugin

A single plugin can activate many new things within Genkit. For example, the Vertex AI plugin activates several new models as well as an embedder.

### Model plugins

Genkit model plugins add one or more generative AI models to the Genkit registry. A model represents any generative
model that is capable of receiving a prompt as input and generating text, media, or data as output.
Generally, a model plugin will make one or more `defineModel` calls in its initialization function.

A custom model generally consists of three components:

1.  Metadata defining the model's capabilities.
2.  A configuration schema with any specific parameters supported by the model.
3.  A function that implements the model accepting `GenerateRequest` and
    returning `GenerateResponse`.

To build a model plugin, you'll need to use the `@genkit-ai/ai` package:

```posix-terminal
npm i --save @genkit-ai/ai
```

At a high level, a model plugin might look something like this:

```ts
import { genkitPlugin, GenkitPlugin } from 'genkit/plugin';
import { GenkitError } from '@genkit-ai/core';
import { GenerationCommonConfigSchema } from '@genkit-ai/ai/model';
import { simulateSystemPrompt } from '@genkit-ai/ai/model/middleware';
import { z } from 'genkit';


export function myPlugin(options?: MyPluginOptions) {
  return genkitPlugin('my-plugin', async (ai: Genkit) => {
    ai.defineModel({
      // be sure to include your plugin as a provider prefix
      name: 'my-plugin/my-model',
      // label for your model as shown in Genkit Developer UI
      label: 'My Awesome Model',
      // optional list of supported versions of your model
      versions: ['my-model-001', 'my-model-001'],
      // model support attributes
      supports: {
        multiturn: true, // true if your model supports conversations
        media: true, // true if your model supports multimodal input
        tools: true, // true if your model supports tool/function calling
        systemRole: true, // true if your model supports the system role
        output: ['text', 'media', 'json'], // types of output your model supports
      },
      // Zod schema for your model's custom configuration
      configSchema: GenerationCommonConfigSchema.extend({
        safetySettings: z.object({...}),
      }),
      // list of middleware for your model to use
      use: [simulateSystemPrompt()]
    }, async request => {
      const myModelRequest = toMyModelRequest(request);
      const myModelResponse = await myModelApi(myModelRequest);
      return toGenerateResponse(myModelResponse);
    });
  });
};


```

#### Transforming Requests and Responses

The primary work of a Genkit model plugin is transforming the
`GenerateRequest` from Genkit's common format into a format that is recognized
and supported by your model's API, and then transforming the response from your
model into the `GenerateResponseData` format used by Genkit.

Sometimes, this may require massaging or manipulating data to work around model limitations. For example, if your model does not natively support a `system` message, you may need to transform a prompt's system message into a user/model message pair.

#### Model references

Once a model is registered using `defineModel`, it is always available when
requested by name. However, to improve typing and IDE autocompletion, you can
export a model reference from your package that includes only the metadata for a
model but not its implementation:

```ts
import { modelRef } from "@genkit-ai/ai/model";

export myModelRef = modelRef({
  name: "my-plugin/my-model",
  configSchema: MyConfigSchema,
  info: {
    // ... model-specific info
  },
})
```

When calling `generate()`, model references and string model names can be used interchangeably:

```ts
import { myModelRef } from 'genkitx-my-plugin';
import { generate } from '@genkit-ai/ai';

generate({ model: myModelRef });
// is equivalent to
generate({ model: 'my-plugin/my-model' });
```

## Publishing a plugin

Genkit plugins can be published as normal NPM packages. To increase
discoverability and maximize consistency, your package should be named
`genkitx-{name}` to indicate it is a Genkit plugin and you should include as
many of the following `keywords` in your `package.json` as are relevant to your
plugin:

- `genkit-plugin`: always include this keyword in your package to indicate it is a Genkit plugin.
- `genkit-model`: include this keyword if your package defines any models.
- `genkit-retriever`: include this keyword if your package defines any retrievers.
- `genkit-indexer`: include this keyword if your package defines any indexers.
- `genkit-embedder`: include this keyword if your package defines any indexers.
- `genkit-tracestore`: include this keyword if your package defines any trace stores.
- `genkit-statestore`: include this keyword if your package defines any state stores.
- `genkit-telemetry`: include this keyword if your package defines a telemetry provider.
- `genkit-deploy`: include this keyword if your package includes helpers to deploy Genkit apps to cloud providers.
- `genkit-flow`: include this keyword if your package enhances Genkit flows.

A plugin that provided a retriever, embedder, and model might have a `package.json` that looks like:

```js
{
  "name": "genkitx-my-plugin",
  "keywords": ["genkit-plugin", "genkit-retriever", "genkit-embedder", "genkit-model"],
  // ... dependencies etc.
}
```
