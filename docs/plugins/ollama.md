# Ollama plugin

The Ollama plugin provides interfaces to any of the local LLMs supported by
[Ollama](https://ollama.com/).

## Installation

```posix-terminal
npm i --save genkitx-ollama
```

## Configuration

This plugin requires that you first install and run the Ollama server. You can
follow the instructions on: https://ollama.com/download

You can use the Ollama CLI to download the model you are interested in. For
example:

```posix-terminal
ollama pull gemma
```

To use this plugin, specify it when you initialize Genkit:

```ts
import { genkit } from 'genkit';
import { ollama } from 'genkitx-ollama';

const ai = genkit({
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

### Authentication

If you would like to access remote deployments of Ollama that require custom
headers (static, such as API keys, or dynamic, such as auth headers), you can
specify those in the Ollama config plugin:

Static headers:

```ts
ollama({
  models: [{ name: 'gemma'}],
  requestHeaders: {
    'api-key': 'API Key goes here'
  },
  serverAddress: 'https://my-deployment',
}),
```

You can also dynamically set headers per request. Here's an example of how to
set an ID token using the Google Auth library:

```ts
import { GoogleAuth } from 'google-auth-library';
import { ollama } from 'genkitx-ollama';
import { genkit } from 'genkit';

const ollamaCommon = { models: [{ name: 'gemma:2b' }] };

const ollamaDev = {
  ...ollamaCommon,
  serverAddress: 'http://127.0.0.1:11434',
};

const ollamaProd = {
  ...ollamaCommon,
  serverAddress: 'https://my-deployment',
  requestHeaders: async (params) => {
    const headers = await fetchWithAuthHeader(params.serverAddress);
    return { Authorization: headers['Authorization'] };
  },
};

const ai = genkit({
  plugins: [
    ollama(isDevEnv() ? ollamaDev : ollamaProd),
  ],
});

// Function to lazily load GoogleAuth client
let auth: GoogleAuth;
function getAuthClient() {
  if (!auth) {
    auth = new GoogleAuth();
  }
  return auth;
}

// Function to fetch headers, reusing tokens when possible
async function fetchWithAuthHeader(url: string) {
  const client = await getIdTokenClient(url);
  const headers = await client.getRequestHeaders(url); // Auto-manages token refresh
  return headers;
}

async function getIdTokenClient(url: string) {
  const auth = getAuthClient();
  const client = await auth.getIdTokenClient(url);
  return client;
}
```

## Usage

This plugin doesn't statically export model references. Specify one of the
models you configured using a string identifier:

```ts
const llmResponse = await ai.generate({
  model: 'ollama/gemma',
  prompt: 'Tell me a joke.',
});
```

## Embedders

The Ollama plugin supports embeddings, which can be used for similarity searches
and other NLP tasks.

```ts
const ai = genkit({
  plugins: [
    ollama({
      serverAddress: 'http://localhost:11434',
      embedders: [{ name: 'nomic-embed-text', dimensions: 768 }],
    }),
  ],
});

async function getEmbedding() {
  const embedding = await ai.embed({
      embedder: 'ollama/nomic-embed-text',
      content: 'Some text to embed!',
  })

  return embedding;
}

getEmbedding().then((e) => console.log(e))
```
