# Neo4j plugin

The Neo4j plugin provides indexer and retriever implementatons that use the
[Neo4j](https://www.neo4j.com/) Native Graph database.

## Installation

```posix-terminal
npm i --save genkitx-neo4j
```

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { neo4j } from 'genkitx-neo4j';

export default configureGenkit({
  plugins: [
    neo4j([
      {
        indexId: 'company-data',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  // ...
});
```

You must specify neo4j client connection parameters, indexId and the embedding model you want to use.

## Usage

Import retriever and indexer references like so:

```js
import { neo4jRetrieverRef } from 'genkitx-neo4j';
import { neo4jIndexerRef } from 'genkitx-neo4j';
```

Then, pass the references to `retrieve()` and `index()`:

```js
// To use the index you configured when you loaded the plugin:
let docs = await retrieve({ retriever: neo4jRetrieverRef, query });

// To specify an index:
export const indexer = neo4jRetrieverRef({
  indexId: 'wikipedia-page',
});
docs = await retrieve({ retriever: neo4jRetrieverRef, query });
```

```js
// To use the index you configured when you loaded the plugin:
await index({ indexer: neo4jIndexerRef, documents });

// To specify an index:
export const companyDataIndexer = neo4jIndexerRef({
  indexId: 'company-data',
});
await index({ indexer: companyDataIndexer, documents });
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on indexers and retrievers.
