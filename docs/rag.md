# Retrieval-augmented generation (RAG)

RAG is a very broad area and there are many different techniques used to achieve the best quality RAG. The core Genkit framework offers two main abstractions/APIs to help you do RAG:

-   Retrievers - retrieves documents from an "index" given a query.
-   Indexers - adds documents to the "index".

The definitions are broad on purpose because Genkit is un-opinionated about what an "index" is or how exactly documents are retrieved from it. Genkit only provides document formats for `TextDocument` and `MultipartDocument`. Everything else is defined by retriever/indexer implementation provider (via the plugions system).

## Retrievers

Retriever is a concept which encapsulates logic related to any kind of document retrieval. The most popular retrieval cases typically include retrieval from vector stores.

To create a retriever you can use one of the provided implementations or easily create your own.

Let's take a look at a dev local file based vector similarity retriever that Genkit provides out-of-the box for simple testing/prototyping (DO NOT USE IN PRODUCTION).

```javascript
import { geminiPro, vertexAI, textembeddingGecko } from '@genkit-ai/plugin-vertex-ai';
import { devLocalVectorstore } from '@genkit-ai/plugin-dev-local-vectorstore';

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

You can then import documents into the store:

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

You can then use the provided `retrieve` function to retrieve documents from the store:

```javascript
const docs = await retrieve({
  retriever: spongeBobFactRetriever,
  query, // e.g. "Where does spongebob work?"
  options: { k: 3 },
});
```

It's very easy to swap out your retriever if for example you want to try a different one.

```js
import { chroma } from '@genkit-ai/plugin-chroma';

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

```js
import {
  chromaIndexerRef,
  chromaRetrieverRef,
} from '@genkit-ai/plugin-chroma';

export const spongeBobFactsRetriever = chromaRetrieverRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts retriever',
});

export const spongeBobFactsIndexer = chromaIndexerRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts indexer',
});

const docs = await retrieve({
  retriever: spongeBobFactsRetriever,
  query: "Who is spongebob?"
});
```

### Retriever plugins

Genkit provides built-in plugins for the following retrievers for some popular vectorstore:

#### Chroma DB

```js
import { chroma } from '@genkit-ai/plugin-chroma';

export default configureGenkit({
  plugins: [
    chroma({
      collectionName: 'spongebob_collection',
      embedder: textEmbeddingGecko001,
      embedderOptions: { temperature: 0 },
    }),
  ],
 // ...
});
```

You can then create retriever and indexer references like so

```js
import { chromaIndexerRef, chromaRetrieverRef } from '@genkit-ai/plugin-chroma';

export const spongeBobFactsRetriever = chromaRetrieverRef({
  collectionName: 'spongebob_collection'
});
export const spongeBobFactsIndexer = chromaIndexerRef({
  collectionName: 'spongebob_collection'
});
```

#### Pinecone

```js
import { pinecone } from '@genkit-ai/plugin-pinecone';

export default configureGenkit({
  plugins: [
    pinecone([
      {
        indexId: 'pdf-chat',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
    ]),
  ],
 // ...
});
```

The plugin requires that you set the PINECONE_API_KEY environment variable with your Pinecone API Key.

Note that you need to configure the plugin with the embedder by passing in a reference.

You can then create retriever and indexer references like so

```js
import {
  pineconeIndexerRef,
  pineconeRetrieverRef,
} from '@genkit-ai/plugin-pinecone';

export const tomAndJerryFactsRetriever = pineconeRetrieverRef({
  indexId: 'pdf-chat'
});
export const tomAndJerryFactsIndexer = pineconeIndexerRef({
  indexId: 'pdf-chat'
});
```

#### pgvector

```js
import {
  TextDocumentSchema,
  defineRetriever,
  retrieve,
} from '@genkit-ai/ai/retrievers';
import { z } from 'zod';
import postgres from 'postgres';
import { embed } from '@genkit-ai/ai/embedders';
import { textembeddingGecko } from '@genkit-ai/plugin-vertex-ai';
import { toSql } from 'pgvector';

const sql = postgres({ ssl: false, database: 'recaps' });

const sqlRetriever = defineRetriever(
  {
    provider: 'custom',
    retrieverId: 'sql',
    customOptionsType: z.any(),
    documentType: TextDocumentSchema,
    queryType: z.object({
      show: z.string(),
      question: z.string(),
    }),
  },
  async (input) => {
    const embedding = await embed({
      embedder: textembeddingGecko,
      input: input.question,
    });
    const results = await sql`
      SELECT episode_id, season_number, chunk as content
        FROM embeddings
        WHERE show_id = ${input.show}
        ORDER BY embedding <#> ${toSql(embedding)} LIMIT 5
      `;
    return results.map((row) => {
      const { content, ...metadata } = row;
      return { content, metadata };
    });
  }
);
```

and here's how to use the above retriever in a flow:

```js
// Simple flow to use the sqlRetriever
export const askQuestionsOnGoT = flow(
  {
    name: 'askQuestionsOnGoT',
    input: z.string(),
    output: z.string(),
  },
  async (inputQuestion) => {
    const docs = await retrieve({
      retriever: sqlRetriever,
      query: {
        show: "Game of Thrones",
        question: inputQuestion,
      }
    });
    console.log(docs);

    // Continue with using retrieved docs 
    // in RAG prompts.
    ... 
  }
);
```

### Write your own retrievers

It's also possible to create your own retriever. This is useful if your documents are managed in a document store that is not currently supported in Genkit (eg: MySQL, Google Drive, etc.). The Genkit SDK provides a flexible `defineRetriever` method that lets you provide custom code for fetching documents. You can also define custom retrievers that build on top of existing retrievers in Genkit and apply advanced RAG techniques (ex. reranking or prompt extensions) on top.

```javascript
import {
  CommonRetrieverOptionsSchema,
  TextDocumentSchema,
  defineRetriever,
  retrieve,
} from "@genkit-ai/ai/retrievers";
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

## Chunking

Genkit does not currently provide built-in chunking libraries, however there are open source libraries available that are compatible with Genkit.

```js
// npm install llm-chunk
import { chunk } from 'llm-chunk';

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;
```

here's how you can use the chunking library with Genkit:

```js
export const indexPdf = flow(
  {
    name: 'indexPdf',
    input: z.string().describe('PDF file path'),
    output: z.void(),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () => 
      extractTextFromPdf(filePath)
    );

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const transformedDocs: TextDocument[] = chunks.map((text) => {
      return { content: text, metadata: { filePath } };
    });

    await index({
      indexer: pdfChatIndexer,
      docs: transformedDocs,
    });
  }
);
```