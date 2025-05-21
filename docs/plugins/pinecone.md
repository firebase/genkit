# Pinecone plugin

The Pinecone plugin provides indexer and retriever implementations that use the
[Pinecone](https://www.pinecone.io/) cloud vector database.

## Installation

```posix-terminal
npm i --save genkitx-pinecone
```

## Configuration

To use this plugin, specify it when you initialize Genkit:

```ts
import { genkit } from 'genkit';
import { pinecone } from 'genkitx-pinecone';

const ai = genkit({
  plugins: [
    pinecone([
      {
        indexId: 'bob-facts',
        embedder: textEmbedding004,
      },
    ]),
  ],
});
```

You must specify a Pinecone index ID and the embedding model you want to use.

In addition, you must configure Genkit with your Pinecone API key. There are two
ways to do this:

*   Set the `PINECONE_API_KEY` environment variable.
*   Specify it in the `clientParams` optional parameter:

    ```ts
    clientParams: {
      apiKey: ...,
    }
    ```

    The value of this parameter is a `PineconeConfiguration` object, which gets passed to the Pinecone client; you can use it to pass any parameter the client supports.

## Usage

Import retriever and indexer references like so:

```ts
import { pineconeRetrieverRef } from 'genkitx-pinecone';
import { pineconeIndexerRef } from 'genkitx-pinecone';
```

Then, use these references with `ai.retrieve()` and `ai.index()`:

```ts
// To use the index you configured when you loaded the plugin:
let docs = await ai.retrieve({ retriever: pineconeRetrieverRef, query });

// To specify an index:
export const bobFactsRetriever = pineconeRetrieverRef({
  indexId: 'bob-facts',
});
docs = await ai.retrieve({ retriever: bobFactsRetriever, query });
```

```ts
// To use the index you configured when you loaded the plugin:
await ai.index({ indexer: pineconeIndexerRef, documents });

// To specify an index:
export const bobFactsIndexer = pineconeIndexerRef({
  indexId: 'bob-facts',
});
await ai.index({ indexer: bobFactsIndexer, documents });
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on indexers and retrievers.
