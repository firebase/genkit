# RAG

RAG is a very broad area and there are many different techniques used to achieve the best quality RAG. The core Genkit framework offers two main abstractions/APIs to help you do RAG:

1. Retrievers - retrieves documents from an "index" given a query.
2. Indexers - adds documents to the "index".

The definitions are broad on purpose because Genkit is not too opinionated about what an "index" is or how exactly documents are retrived from it. Genkit only provides document formats for `TextDocument` and `MultipartDocument`. Everything else is defined by retriever/indexer implementation provider (via the plugions system).

## Retrievers

Retriever is a concept which encapsulates logic relates to any kind of document retrieval. The most popular retrieval cases typically include retrieval from vector stores.

To create a retriever you can use one of the provided implementations or easily
create your own.

Let's take a look at a dev local file based vector similarity retriever that Genkit provides out-of-the box for simple testing/prototyping (DO NOT USE IN PRODUCTION).

```javascript
import { geminiPro, vertexAI, textembeddingGecko } from '@google-genkit/plugin-vertex-ai';
import { devLocalVectorstore } from '@google-genkit/plugin-dev-local-vectorstore';

export default configureGenkit({
  plugins: [
    // vertexAI provides the textembeddingGecko embedder that'll use.
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
    devLocalVectorstore([
      {
        indexName: 'spongebob-facts',
        embedder: textembeddingGecko,
      }
    ]),
    // ...
  ],
  // ...
});
```

Once configured, create a references for your index:

```javascript
export const spongeBobFactRetriever = devLocalRetrieverRef('spongebob-facts');
export const spongeBobFactIndexer = devLocalIndexerRef('spongebob-facts');
```

You can then import documents into the store.

```javascript
const spongebobFacts = [
  {
    content: "SpongeBob's primary job is working as the fry cook at the Krusty Krab.",
    metadata: { type: "tv", show: "Spongebob" },
  },
  {
    content: "SpongeBob is a yellow sea sponge.",
    metadata: { type: "tv", show: "Spongebob" },
  },
]

await index({
  indexer: spongeBobFactIndexer,
  docs: spongebobFacts,
});
```

you can then use the provided `retrieve` function to retrieve documents from the store:

```javascript
const docs = await retrieve({
  retriever: spongeBobFactRetriever,
  query, // e.g. "Where does spongebob work?"
  options: { k: 3 },
});
```

It's also very easy to create your own retriever. This is useful if your
documents are managed in a document store that is not currently supported in
Genkit (eg: MySQL, Google Drive, etc.). The Genkit SDK provides a flexible
`defineRetriever` method that lets you provide custom code for fetching documents.
You can also define custom retrievers that build on top of existing retrievers
in Genkit and apply advanced RAG techniques (ex. reranking or prompt
extensions) on top.


```javascript
import {
  CommonRetrieverOptionsSchema,
  TextDocumentSchema,
  defineRetriever,
  retrieve,
} from "@google-genkit/ai/retrievers";
import * as z from 'zod';

const MyAdvancedOptionsSchema = CommonRetrieverOptionsSchema.extend({
  preRerankK: z.number().max(1000),
});

const advancedRetriever = defineRetriever({
  provider: 'custom',
  retrieverId: `custom/myAdvancedRetriver`,
  queryType: z.string(),
  documentType: TextDocumentSchema,
  customOptionsType: MyAdvancedOptionsSchema,
},
  async (input, options) => {
    const extendedPrompt = await extendPrompt(input);
    const docs = await retrieve({
      retriever: spongeBobFactsRetriever,
      query: extendedPrompt,
      options: { k: options.preRerankK || 10 }
    });
    const rerankedDocs = await rerank(docs);
    return rerankedDocs.slice(0, options.k || 3);
  }
);
```

(`extendPrompt` and `rerank` is something you would have to implement yourself, currently not provided by the framework)

And then you can just swap out your retriever:

```javascript
const docs = await retrieve({
  retriever: advancedRetriever,
  query: "Who is spongebob?",
  options: { preRerankK: 7, k: 3 }
});
```

It's very easy to swap out your retriever if for example you want to try a different one.

```javascript
import { chroma } from '@google-genkit/plugin-chroma';

export default configureGenkit({
  plugins: [
    chroma({
      collectionName: 'spongebob_collection',
      embedder: textembeddingGecko,
    }),
    // ...
  ],
  // ...
});
```

```javascript
import {
  chromaIndexerRef,
  chromaRetrieverRef,
} from '@google-genkit/plugin-chroma';

export const spongeBobFactsRetriever = chromaRetrieverRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts retriever',
});

export const spongeBobFactsIndexer = chromaIndexerRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts indexer',
});
```

```javascript
const docs = await retrieve({
  retriever: spongeBobFactsRetriever,
  query: "Who is spongebob?"
});
```