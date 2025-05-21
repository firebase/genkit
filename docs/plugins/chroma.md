# Chroma plugin

The Chroma plugin provides indexer and retriever implementations that use the
[Chroma](https://docs.trychroma.com/) vector database in client/server mode.

## Installation

```posix-terminal
npm i --save genkitx-chromadb
```

## Configuration

To use this plugin, specify it when you initialize Genkit:

```ts
import { genkit } from 'genkit';
import { chroma } from 'genkitx-chromadb';

const ai = genkit({
  plugins: [
    chroma([
      {
        collectionName: 'bob_collection',
        embedder: textEmbedding004,
      },
    ]),
  ],
});
```

You must specify a Chroma collection and the embedding model you want to use. In
addition, there are two optional parameters:

*    `clientParams`: If you're not running your Chroma server on the same machine as your Genkit flow, you need to specify auth options, or you're otherwise not running a default Chroma server configuration, you can specify a Chroma <code>[ChromaClientParams object]([https://docs.trychroma.com/js_reference/Client](https://docs.trychroma.com/js_reference/Client))</code> to pass to the Chroma client:

    ```ts
    clientParams: {
      path: "http://192.168.10.42:8000",
    }
    ```

*   `embedderOptions`: Use this parameter to pass options to the embedder:

    ```ts
    embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
    ```

## Usage

Import retriever and indexer references like so:

```ts
import { chromaRetrieverRef } from 'genkitx-chromadb';
import { chromaIndexerRef } from 'genkitx-chromadb';
```

Then, use the references with `ai.retrieve()` and `ai.index()`:

```ts
// To use the index you configured when you loaded the plugin:
let docs = await ai.retrieve({ retriever: chromaRetrieverRef, query });

// To specify an index:
export const bobFactsRetriever = chromaRetrieverRef({
  collectionName: 'bob-facts',
});
docs = await ai.retrieve({ retriever: bobFactsRetriever, query });
```

```ts
// To use the index you configured when you loaded the plugin:
await ai.index({ indexer: chromaIndexerRef, documents });

// To specify an index:
export const bobFactsIndexer = chromaIndexerRef({
  collectionName: 'bob-facts',
});
await ai.index({ indexer: bobFactsIndexer, documents });
```

See the [Retrieval-augmented generation](../rag) page for a general
discussion on indexers and retrievers.
