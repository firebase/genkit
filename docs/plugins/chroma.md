# Chroma plugin

The Chroma plugin provides indexer and retriever implementatons that use the
[Chroma](https://docs.trychroma.com/) vector database in client/server mode.

## Installation

```posix-terminal
npm i --save genkitx-chromadb
```

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { chroma } from 'genkitx-chromadb';

export default configureGenkit({
  plugins: [
    chroma([
      {
        collectionName: 'bob_collection',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  // ...
});
```

You must specify a Chroma collection and the embedding model you want to use. In
addition, there are two optional parameters:

- `clientParams`: If you're not running your Chroma server on the same machine
  as your Genkit flow, you need to specify auth options, or you're otherwise not
  running a default Chroma server configuration, you can specify a Chroma
  [`ChromaClientParams` object](https://docs.trychroma.com/js_reference/Client)
  to pass to the Chroma client:

  ```js
  clientParams: {
    path: "http://192.168.10.42:8000",
  }
  ```

- `embedderOptions`: Use this parameter to pass options to the embedder:

  ```js
  embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
  ```

## Usage

Import retriever and indexer references like so:

```js
import { chromaRetrieverRef } from 'genkitx-chromadb';
import { chromaIndexerRef } from 'genkitx-chromadb';
```

Then, pass the references to `retrieve()` and `index()`:

```js
import { retrieve } from '@genkit-ai/ai';

// To use the index you configured when you loaded the plugin:
let docs = await retrieve({ retriever: chromaRetrieverRef, query });

// To specify an index:
export const bobFactsRetriever = chromaRetrieverRef({
  collectionName: 'bob-facts',
});
docs = await retrieve({ retriever: bobFactsRetriever, query });
```

```js
import { retrieve } from '@genkit-ai/ai';

// To use the index you configured when you loaded the plugin:
await index({ indexer: chromaIndexerRef, documents });

// To specify an index:
export const bobFactsIndexer = chromaIndexerRef({
  collectionName: 'bob-facts',
});
await index({ indexer: bobFactsIndexer, documents });
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on indexers and retrievers.
