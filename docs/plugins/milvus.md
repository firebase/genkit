# Milvus plugin

The Milvus plugin provides indexer and retriever implementatons that use the
[Milvus](https://milvus.io/) vector database.

## Installation

```posix-terminal
npm i --save genkitx-milvus
```

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { milvus } from 'genkitx-milvus';

export default configureGenkit({
  plugins: [
    milvus([
      {
        collectionName: 'collection_01',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  // ...
});
```

You must specify a Milvus collection and the embedding model you want to use. In
addition, there are three optional parameters:

- `dbName`: Specified database

- `clientParams`: If you're not running your Milvus server on the same machine
  as your Genkit flow, you need to specify auth options, or you're otherwise not
  running a default Milvus server configuration, you can specify a Milvus

  ```js
  clientParams: {
    address: "",
    token: "",
  }
  ```

- `embedderOptions`: Use this parameter to pass options to the embedder:

  ```js
  embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
  ```
  ## Usage

Import retriever and indexer references like so:

```js
import { milvusRetrieverRef, milvusIndexerRef } from 'genkitx-milvus';
```

Then, pass the references to `retrieve()` and `index()`:

```js
// To use the index you configured when you loaded the plugin:
let docs = await retrieve({ retriever: milvusRetrieverRef, query });

// To specify an index:
export const customRetriever = milvusRetrieverRef({
  collectionName: 'collection_01',
});
docs = await retrieve({ retriever: customRetriever, query });
```

```js
// To use the index you configured when you loaded the plugin:
await index({ indexer: milvusIndexerRef, documents });

// To specify an index:
export const customIndexer = milvusIndexerRef({
  collectionName: 'collection_01',
});
await index({ indexer: customIndexer, documents });
```