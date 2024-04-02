# Ollama plugin

The Ollama plugin provides interfaces to any of the local LLMs supported by
[Ollama](https://ollama.com/).

## Configuration

This plugin requires that you first install and run ollama server. You can follow
the instructions on: [https://ollama.com/download](https://ollama.com/download)

You can use the Ollama CLI to download the model you are interested in. For
example:

```posix-terminal
ollama pull mixtral
```

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { ollama } from '@genkit-ai/ollama';

export default configureGenkit({
  plugins: [
    ollama({
      models: [
        {
          name: 'mixtral',
          type: 'chat',
        },
      ],
      pullModel: false,
    }),
  ],
});
```

## Usage

This plugin doesn't statically export model references. Specify one of the
models you configured using a string identifier:

```js
const llmResponse = await generate({
  model: 'ollama/mixtral',
  prompt: 'Tell me a joke.',
});
```
