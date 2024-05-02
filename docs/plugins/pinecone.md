# Pinecone plugin

The Pinecone plugin provides indexer and retriever implementatons that use the
[Pinecone](https://www.pinecone.io/) cloud vector database.

## Installation

```posix-terminal
npm i --save genkitx-pinecone
```

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { pinecone } from 'genkitx-pinecone';

export default configureGenkit({
  plugins: [
    pinecone([
      {
        indexId: 'bob-facts',
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

Import retriever and indexer references like so:

```js
import { pineconeRetrieverRef } from 'genkitx-pinecone';
import { pineconeIndexerRef } from 'genkitx-pinecone';
```

Then, pass the references to `retrieve()` and `index()`:

```js
// To use the index you configured when you loaded the plugin:
let docs = await retrieve({ retriever: pineconeRetrieverRef, query });

// To specify an index:
export const bobFactsRetriever = pineconeRetrieverRef({
  indexId: 'bob-facts',
});
docs = await retrieve({ retriever: bobFactsRetriever, query });
```

```js
// To use the index you configured when you loaded the plugin:
await index({ indexer: pineconeIndexerRef, documents });

// To specify an index:
export const bobFactsIndexer = pineconeIndexerRef({
  indexId: 'bob-facts',
});
await index({ indexer: bobFactsIndexer, documents });
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on indexers and retrievers.
