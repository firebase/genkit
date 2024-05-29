# Qdrant plugin

The Qdrant plugin provides indexer and retriever implementations that use the [Qdrant](https://qdrant.tech/) vector database/search engine

## Installation

```posix-terminal
npm i genkitx-qdrant
```

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { qdrant } from 'genkitx-qdrant';

export default configureGenkit({
  plugins: [
    qdrant([
      {
        clientParams: {
          host: 'localhost',
          port: 6333,
        },
        collectionName: 'some-collection',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  // ...
});
```

You'll need to specify a collection name, the embedding model you want to use and the Qdrant client parameters. In
addition, there are a few optional parameters:

- `embedderOptions`: Additional options to pass options to the embedder:

  ```js
  embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
  ```

- `contentPayloadKey`: Name of the payload filed with the document content. Defaults to "content".

  ```js
  contentPayloadKey: 'content';
  ```

- `metadataPayloadKey`: Name of the payload filed with the document metadata. Defaults to "metadata".

  ```js
  metadataPayloadKey: 'metadata';
  ```

- `collectionCreateOptions`: [Additional options](<(https://qdrant.tech/documentation/concepts/collections/#create-a-collection)>) when creating the Qdrant collection.

## Usage

Import retriever and indexer references like so:

```js
import { qdrantIndexerRef, qdrantRetrieverRef } from 'genkitx-qdrant';
```

Then, pass the references to `retrieve()` and `index()`:

```js
// To specify an index:
export const qdrantIndexer = qdrantIndexerRef({
  collectionName: 'some-collection',
  displayName: 'Some Collection indexer',
});
await index({ indexer: qdrantIndexer, documents });
```

```js
// To specify a retriever:
export const qdrantRetriever = qdrantRetrieverRef({
  collectionName: 'some-collection',
  displayName: 'Some Collection Retriever',
});
let docs = await retrieve({ retriever: qdrantRetriever, query });
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on indexers and retrievers.
