# Ollama plugin

The Ollama plugin provides interfaces to any of the local LLMs supported by
[Ollama](https://ollama.com/).

## Configuration

This plugin requires that you first install and run ollama server. You can follow
the instructions on: [https://ollama.com/download](https://ollama.com/download)

You can use the Ollama CLI to download the model you are interested in. For
example:

```posix-terminal
ollama pull gemma
```

To use this plugin, specify it when you call `configureGenkit()`.

```js
import { ollama } from '@genkit-ai/ollama';

export default configureGenkit({
  plugins: [
    ollama({
      models: [
        {
          name: 'gemma',
          type: 'generate', // type: 'chat' | 'generate' | undefined
        },
      ],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
  ],
});
```

## Usage

This plugin doesn't statically export model references. Specify one of the
models you configured using a string identifier:

```js
const llmResponse = await generate({
  model: 'ollama/gemma',
  prompt: 'Tell me a joke.',
});
```
