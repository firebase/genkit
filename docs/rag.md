# Retrieval-augmented generation (RAG)

Genkit provides abstractions that help you build retrieval-augmented generation
(RAG) flows, as well as plugins that provide integrations with related tools.

Retrieval-augmented generation is a technique used to incorporate external
sources of information into an LLM’s responses. It's important to be able to do
so because, while LLMs are typically trained on a broad body of
material, practical use of LLMs often requires specific domain knowledge (for
example, you might want to use an LLM to answer customers' questions about your
company’s products).

One solution is to fine-tune the model using more specific data. However, this
can be expensive both in terms of compute cost and in terms of the effort needed
to prepare adequate training data.

In contrast, RAG works by incorporating external data sources into a prompt at
the time it's passed to the model. For example, you could imagine the prompt,
"What is Bart's relationship to Lisa?" might be expanded ("augmented") by
prepending some relevant information, resulting in the prompt, "Homer and
Marge's children are named Bart, Lisa, and Maggie. What is Bart's relationship
to Lisa?"

This approach has several advantages:

- It can be more cost effective because you don't have to retrain the model.
- You can continuously update your data source and the LLM can immediately make
  use of the updated information.
- You now have the potential to cite references in your LLM's responses.

On the other hand, using RAG naturally means longer prompts, and some LLM API
services charge for each input token you send. Ultimately, you must evaluate the
cost tradeoffs for your applications.

RAG is a very broad area and there are many different techniques used to achieve
the best quality RAG. The core Genkit framework offers two main abstractions to
help you do RAG:

- Indexers: add documents to an "index".
- Retrievers: retrieve documents from an "index", given a query.

These definitions are broad on purpose because Genkit is un-opinionated about
what an "index" is or how exactly documents are retrieved from it. Genkit only
provides a `Document` format and everything else is defined by the retriever or
indexer implementation provider.

## Indexers

The index is responsible for keeping track of your documents in such a way that
you can quickly retrieve relevant documents given a specific query. This is most
often accomplished using a vector database, which indexes your documents using
multidimensional vectors called embeddings. A text embedding (opaquely)
represents the concepts expressed by a passage of text; these are generated
using special-purpose ML models. By indexing text using its embedding, a vector
database is able to cluster conceptually related text and retrieve documents
related to a novel string of text (the query).

Before you can retrieve documents for the purpose of generation, you need to
ingest them into your document index. A typical ingestion flow does the
following:

1.  Split up large documents into smaller documents so that only relevant
    portions are used to augment your prompts – “chunking”. This is necessary
    because many LLMs have a limited context window, making it impractical to
    include entire documents with a prompt.

    Genkit doesn't provide built-in chunking libraries; however, there are open
    source libraries available that are compatible with Genkit.

1.  Generate embeddings for each chunk. Depending on the database you're using,
    you might explicitly do this with an embedding generation model, or you
    might use the embedding generator provided by the database.

1.  Add the text chunk and its index to the database.

You might run your ingestion flow infrequently or only once if you are working
with a stable source of data. On the other hand, if you are working with data
that frequently changes, you might continuously run the ingestion flow (for
example, in a Cloud Firestore trigger, whenever a document is updated).

The following example shows how you could ingest a collection of PDF documents
into a vector database. It uses the local file-based vector similarity retriever
that Genkit provides out-of-the box for simple testing and prototyping (_do not
use in production_):

```ts
import { Document, index } from '@genkit-ai/ai/retriever';
import { defineFlow, run } from '@genkit-ai/flow';
import fs from 'fs';
import { chunk } from 'llm-chunk'; // npm install llm-chunk
import path from 'path';
import pdf from 'pdf-parse'; // npm i pdf-parse && npm i -D --save @types/pdf-parse
import z from 'zod';

import { configureGenkit } from '@genkit-ai/core/config';
import {
  devLocalIndexerRef,
  devLocalVectorstore,
} from '@genkit-ai/plugin-dev-local-vectorstore';
import { textEmbeddingGecko, vertexAI } from '@genkit-ai/plugin-vertex-ai';

configureGenkit({
  plugins: [
    // vertexAI provides the textEmbeddingGecko embedder
    vertexAI(),
    devLocalVectorstore([
      {
        indexName: 'spongebob-facts',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
});

export const pdfIndexer = devLocalIndexerRef('spongebob-facts');

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

export const indexPdf = defineFlow(
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

    const documents = chunks.map((text) => {
      return Document.fromText(text, { filePath });
    });

    await index({
      indexer: pdfIndexer,
      documents,
    });
  }
);

async function extractTextFromPdf(filePath: string) {
  const pdfFile = path.resolve(filePath);
  const dataBuffer = fs.readFileSync(pdfFile);
  const data = await pdf(dataBuffer);
  return data.text;
}
```

To run the flow:

```posix-terminal
npx genkit flow:run indexPdf "'../pdfs'"
```

## Retrievers

A retriever is a concept that encapsulates logic related to any kind of document
retrieval. The most popular retrieval cases typically include retrieval from
vector stores.

To create a retriever, you can use one of the provided implementations or
create your own.

The following example shows how you might use a retriever in a RAG flow. Like
the indexer example, this example uses Genkit's file-based vector retriever,
which you should not use in production.

```ts
import { configureGenkit } from '@genkit-ai/core/config';
import { defineFlow } from '@genkit-ai/flow';
import { generate } from '@genkit-ai/ai/generate';
import { retrieve } from '@genkit-ai/ai/retriever';
import { definePrompt } from '@genkit-ai/dotprompt';
import {
  devLocalRetrieverRef,
  devLocalVectorstore,
} from '@genkit-ai/plugin-dev-local-vectorstore';
import {
  geminiPro,
  textEmbeddingGecko,
  vertexAI,
} from '@genkit-ai/plugin-vertex-ai';
import * as z from 'zod';

configureGenkit({
  plugins: [
    vertexAI(),
    devLocalVectorstore([
      {
        indexName: 'spongebob-facts',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
});

export const spongeBobFactRetriever = devLocalRetrieverRef('spongebob-facts');

export const ragFlow = defineFlow(
  { name: 'ragFlow', input: z.string(), output: z.string() },
  async (input) => {
    const docs = await retrieve({
      retriever: spongeBobFactRetriever,
      query: input,
      options: { k: 3 },
    });
    const facts = docs.map((d) => d.text());

    const promptGenerator = definePrompt(
      {
        name: 'spongebob-facts',
        model: 'google-vertex/gemini-pro',
        input: {
          schema: z.object({
            facts: z.array(z.string()),
            question: z.string(),
          }),
        },
      },
      '{{#each people}}{{this}}\n\n{{/each}}\n{{question}}'
    );
    const prompt = await promptGenerator.generate({
      input: {
        facts,
        question: input,
      },
    });

    const llmResponse = await generate({
      model: geminiPro,
      prompt: prompt.text(),
    });

    const output = llmResponse.text();
    return output;
  }
);
```

### Retriever plugins

Genkit provides built-in plugins with retrievers for some popular vector stores:

#### Chroma DB

```js
import { chroma } from '@genkit-ai/plugin-chroma';

export default configureGenkit({
  plugins: [
    chroma([
      {
        collectionName: 'spongebob_collection',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
  ],
  // ...
});
```

You can then create retriever and indexer references like so:

```js
import { chromaIndexerRef, chromaRetrieverRef } from '@genkit-ai/plugin-chroma';

export const spongeBobFactsRetriever = chromaRetrieverRef({
  collectionName: 'spongebob_collection',
});
export const spongeBobFactsIndexer = chromaIndexerRef({
  collectionName: 'spongebob_collection',
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
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
  ],
  // ...
});
```

The plugin requires that you set the PINECONE_API_KEY environment variable with
your Pinecone API Key.

Note that you need to configure the plugin with the embedder by passing in a
reference.

You can then create retriever and indexer references like so:

```js
import {
  pineconeIndexerRef,
  pineconeRetrieverRef,
} from '@genkit-ai/plugin-pinecone';

export const tomAndJerryFactsRetriever = pineconeRetrieverRef({
  indexId: 'pdf-chat',
});
export const tomAndJerryFactsIndexer = pineconeIndexerRef({
  indexId: 'pdf-chat',
});
```

#### pgvector

```js
import { embed } from '@genkit-ai/ai/embedder';
import { Document, defineRetriever, retrieve } from '@genkit-ai/ai/retriever';
import { defineFlow } from '@genkit-ai/flow';
import { textEmbeddingGecko } from '@genkit-ai/plugin-vertex-ai';
import { toSql } from 'pgvector';
import postgres from 'postgres';
import { z } from 'zod';

const sql = postgres({ ssl: false, database: 'recaps' });

const QueryOptions = z.object({
  show: z.string(),
  k: z.number().optional(),
});

const sqlRetriever = defineRetriever(
  {
    name: 'pgvector/myTable',
    configSchema: QueryOptions,
  },
  async (input, options) => {
    const embedding = await embed({
      embedder: textEmbeddingGecko,
      content: input,
    });
    const results = await sql`
      SELECT episode_id, season_number, chunk as content
        FROM embeddings
        WHERE show_id = ${options.show}
        ORDER BY embedding <#> ${toSql(embedding)} LIMIT ${options.k ?? 3}
      `;
    return {
      documents: results.map((row) => {
        const { content, ...metadata } = row;
        return Document.fromText(content, metadata);
      }),
    };
  }
);
```

And here's how to use the retriever in a flow:

```js
// Simple flow to use the sqlRetriever
export const askQuestionsOnGoT = defineFlow(
  {
    name: 'askQuestionsOnGoT',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (inputQuestion) => {
    const docs = await retrieve({
      retriever: sqlRetriever,
      query: inputQuestion,
      options: {
        show: 'Game of Thrones',
      },
    });
    console.log(docs);

    // Continue with using retrieved docs
    // in RAG prompts.
    //...
  }
);
```

### Write your own retrievers

It's also possible to create your own retriever. This is useful if your
documents are managed in a document store that is not supported in Genkit (eg:
MySQL, Google Drive, etc.). The Genkit SDK provides a flexible `defineRetriever`
method that lets you provide custom code for fetching documents. You can also
define custom retrievers that build on top of existing retrievers in Genkit and
apply advanced RAG techniques (such as reranking or prompt extensions) on top.

```javascript
import {
  CommonRetrieverOptionsSchema,
  defineRetriever,
  retrieve,
} from '@genkit-ai/ai/retriever';
import * as z from 'zod';

const MyAdvancedOptionsSchema = CommonRetrieverOptionsSchema.extend({
  preRerankK: z.number().max(1000),
});

const advancedRetriever = defineRetriever(
  {
    name: `custom/myAdvancedRetriever`,
    configSchema: MyAdvancedOptionsSchema,
  },
  async (input, options) => {
    const extendedPrompt = await extendPrompt(input);
    const docs = await retrieve({
      retriever: spongeBobFactsRetriever,
      query: extendedPrompt,
      options: { k: options.preRerankK || 10 },
    });
    const rerankedDocs = await rerank(docs);
    return rerankedDocs.slice(0, options.k || 3);
  }
);
```

(`extendPrompt` and `rerank` is something you would have to implement yourself,
not provided by the framework)

And then you can just swap out your retriever:

```javascript
const docs = await retrieve({
  retriever: advancedRetriever,
  query: 'Who is spongebob?',
  options: { preRerankK: 7, k: 3 },
});
```

## Chunking

Genkit does not provide built-in chunking libraries; however, there are
open source libraries available that are compatible with Genkit.

```js
import { Document, index } from '@genkit-ai/ai/retriever';
import { defineFlow, run } from '@genkit-ai/flow';
import { pineconeIndexerRef } from '@genkit-ai/plugin-pinecone';
import fs from 'fs';
import { chunk } from 'llm-chunk'; // npm install llm-chunk
import path from 'path';
import pdf from 'pdf-parse'; // npm i pdf-parse && npm i -D --save @types/pdf-parse
import z from 'zod';

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

export const pdfChatIndexer = pineconeIndexerRef({indexId: 'pdf-chat'});

export const indexPdf = defineFlow(
  {
    name: 'indexPdf',
    inputSchema: z.string().describe('PDF file path'),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () =>
      extractTextFromPdf(filePath)
    );

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const documents = chunks.map((text) => {
      return Document.fromText(text, { filePath });
    });

    await index({
      indexer: pdfChatIndexer,
      documents,
    });
  }
);

async function extractTextFromPdf(filePath: string) {
  const pdfFile = path.resolve(filePath)
  const dataBuffer = fs.readFileSync(pdfFile);
  const data = await pdf(dataBuffer)
  return data.text
}
```
