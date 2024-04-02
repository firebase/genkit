# Pinecone plugin

The Pinecone plugin provides indexer and retriever implementatons that use the
[Pinecone](https://www.pinecone.io/) cloud vector database.

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { pinecone } from '@genkit-ai/pinecone';

export default configureGenkit({
  plugins: [
    pinecone([
      {
        indexId: 'spongebob-facts',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  // ...
});
```

You must specify a Pinecone index ID and the embedding model you want to use.

In addition, you must configure Genkit with your Pinecone API key. There are two
ways to do this:

- Set the `PINECONE_API_KEY` environment variable.

- Specify it in the `clientParams` optional parameter:

  ```js
  clientParams: {
    apiKey: ...,
  }
  ```

  The value of this parameter is a `PineconeConfiguration` object, which gets
  passed to the Pinecone client; you can use it to pass any parameter the client
  supports.

## Usage

You can create and use retriever and indexer references like so:

```js
import { pineconeRetrieverRef } from '@genkit-ai/pinecone';

// To use the index you configured when you loaded the plugin:
let docs = await retrieve({ retriever: pineconeRetrieverRef, query });

// To specify an index:
export const spongeBobFactsRetriever = pineconeRetrieverRef({
  indexId: 'spongebob-facts',
});
docs = await retrieve({ retriever: spongeBobFactsRetriever, query });
```

```js
import { pineconeIndexerRef } from '@genkit-ai/pinecone';

// To use the index you configured when you loaded the plugin:
await index({ indexer: pineconeIndexerRef, documents });

// To specify an index:
export const spongeBobFactsIndexer = pineconeIndexerRef({
  indexId: 'spongebob-facts',
});
await index({ indexer: spongeBobFactsIndexer, documents });
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on indexers and retrievers.
