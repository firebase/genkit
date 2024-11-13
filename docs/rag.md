# Retrieval-augmented generation (RAG)

Firebase Genkit provides abstractions that help you build retrieval-augmented
generation (RAG) flows, as well as plugins that provide integrations with
related tools.

## What is RAG?

Retrieval-augmented generation is a technique used to incorporate external
sources of information into an LLM’s responses. It's important to be able to do
so because, while LLMs are typically trained on a broad body of material,
practical use of LLMs often requires specific domain knowledge (for example, you
might want to use an LLM to answer customers' questions about your company’s
products).

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

*   It can be more cost-effective because you don't have to retrain the model.
*   You can continuously update your data source and the LLM can immediately
    make use of the updated information.
*   You now have the potential to cite references in your LLM's responses.

On the other hand, using RAG naturally means longer prompts, and some LLM API
services charge for each input token you send. Ultimately, you must evaluate the
cost tradeoffs for your applications.

RAG is a very broad area and there are many different techniques used to achieve
the best quality RAG. The core Genkit framework offers three main abstractions
to help you do RAG:

*   Indexers: add documents to an "index".
*   Embedders: transforms documents into a vector representation
*   Retrievers: retrieve documents from an "index", given a query.

These definitions are broad on purpose because Genkit is un-opinionated about
what an "index" is or how exactly documents are retrieved from it. Genkit only
provides a `Document` format and everything else is defined by the retriever or
indexer implementation provider.

### Indexers

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

1. Split up large documents into smaller documents so that only relevant
   portions are used to augment your prompts – "chunking". This is necessary
   because many LLMs have a limited context window, making it impractical to
   include entire documents with a prompt.

    Genkit doesn't provide built-in chunking libraries; however, there are open
    source libraries available that are compatible with Genkit.

2. Generate embeddings for each chunk. Depending on the database you're using,
   you might explicitly do this with an embedding generation model, or you might
   use the embedding generator provided by the database.
3. Add the text chunk and its index to the database.

You might run your ingestion flow infrequently or only once if you are working
with a stable source of data. On the other hand, if you are working with data
that frequently changes, you might continuously run the ingestion flow (for
example, in a Cloud Firestore trigger, whenever a document is updated).

### Embedders

An embedder is a function that takes content (text, images, audio, etc.) and
creates a numeric vector that encodes the semantic meaning of the original
content. As mentioned above, embedders are leveraged as part of the process of
indexing, however, they can also be used independently to create embeddings
without an index.

### Retrievers

A retriever is a concept that encapsulates logic related to any kind of document
retrieval. The most popular retrieval cases typically include retrieval from
vector stores, however, in Genkit a retriever can be any function that returns
data.

To create a retriever, you can use one of the provided implementations or create
your own.

## Supported indexers, retrievers, and embedders

Genkit provides indexer and retriever support through its plugin system. The
following plugins are officially supported:

*   [Cloud Firestore vector store](plugins/firebase.md)
*   [Vertex AI Vector Search](plugins/vertex-ai.md)
*   [Chroma DB](plugins/chroma.md) vector database
*   [Pinecone](plugins/pinecone.md) cloud vector database

In addition, Genkit supports the following vector stores through predefined code
templates, which you can customize for your database configuration and schema:

- PostgreSQL with [`pgvector`](templates/pgvector.md)

Embedding model support is provided through the following plugins:

| Plugin                    | Models               |
| ------------------------- | -------------------- |
| [Google Generative AI][1] | Gecko text embedding |
| [Google Vertex AI][2]     | Gecko text embedding |

[1]: plugins/google-genai.md
[2]: plugins/vertex-ai.md

## Defining a RAG Flow

The following examples show how you could ingest a collection of restaurant menu
PDF documents into a vector database and retrieve them for use in a flow that
determines what food items are available.

### Install dependencies for processing PDFs

```posix-terminal
npm install llm-chunk pdf-parse @genkit-ai/dev-local-vectorstore

npm i -D --save @types/pdf-parse
```

### Add a local vector store to your configuration

```ts
import {
  devLocalIndexerRef,
  devLocalVectorstore,
} from '@genkit-ai/dev-local-vectorstore';
import { textEmbedding004, vertexAI } from '@genkit-ai/vertexai';
import { z, genkit } from 'genkit';

const ai = genkit({
  plugins: [
    // vertexAI provides the textEmbedding004 embedder
    vertexAI(),

    // the local vector store requires an embedder to translate from text to vector
    devLocalVectorstore([
      {
        indexName: 'menuQA',
        embedder: textEmbedding004,
      },
    ]),
  ],
});
```

### Define an Indexer

The following example shows how to create an indexer to ingest a collection of
PDF documents and store them in a local vector database.

It uses the local file-based vector similarity retriever that Genkit provides
out-of-the-box for simple testing and prototyping (_do not use in production_)

#### Create the indexer

```ts
export const menuPdfIndexer = devLocalIndexerRef('menuQA');
```

#### Create chunking config

This example uses the `llm-chunk` library which provides a simple text splitter
to break up documents into segments that can be vectorized.

The following definition configures the chunking function to guarantee a
document segment of between 1000 and 2000 characters, broken at the end of a
sentence, with an overlap between chunks of 100 characters.

```ts
const chunkingConfig = {
  minLength: 1000,
  maxLength: 2000,
  splitter: 'sentence',
  overlap: 100,
  delimiters: '',
} as any;
```

More chunking options for this library can be found in the [llm-chunk
documentation](https://www.npmjs.com/package/llm-chunk).

#### Define your indexer flow

```ts
import { Document } from 'genkit/retriever';
import { chunk } from 'llm-chunk';
import { readFile } from 'fs/promises';
import path from 'path';
import pdf from 'pdf-parse';

async function extractTextFromPdf(filePath: string) {
  const pdfFile = path.resolve(filePath);
  const dataBuffer = await readFile(pdfFile);
  const data = await pdf(dataBuffer);
  return data.text;
}

export const indexMenu = ai.defineFlow(
  {
    name: 'indexMenu',
    inputSchema: z.string().describe('PDF file path'),
    outputSchema: z.void(),
  },
  async (filePath: string) => {
    filePath = path.resolve(filePath);

    // Read the pdf.
    const pdfTxt = await run('extract-text', () =>
      extractTextFromPdf(filePath)
    );

    // Divide the pdf text into segments.
    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    // Convert chunks of text into documents to store in the index.
    const documents = chunks.map((text) => {
      return Document.fromText(text, { filePath });
    });

    // Add documents to the index.
    await ai.index({
      indexer: menuPdfIndexer,
      documents,
    });
  }
);
```

#### Run the indexer flow

```posix-terminal
genkit flow:run indexMenu "'menu.pdf'"
```

After running the `indexMenu` flow, the vector database will be seeded with
documents and ready to be used in Genkit flows with retrieval steps.

### Define a flow with retrieval

The following example shows how you might use a retriever in a RAG flow. Like
the indexer example, this example uses Genkit's file-based vector retriever,
which you should not use in production.

```ts
import { devLocalRetrieverRef } from '@genkit-ai/dev-local-vectorstore';

// Define the retriever reference
export const menuRetriever = devLocalRetrieverRef('menuQA');

export const menuQAFlow = ai.defineFlow(
  { name: 'menuQA', inputSchema: z.string(), outputSchema: z.string() },
  async (input: string) => {
    // retrieve relevant documents
    const docs = await ai.retrieve({
      retriever: menuRetriever,
      query: input,
      options: { k: 3 },
    });

    // generate a response
   const { text } = await ai.generate({
      prompt: `
You are acting as a helpful AI assistant that can answer 
questions about the food available on the menu at Genkit Grub Pub.

Use only the context provided to answer the question.
If you don't know, do not make up an answer.
Do not add or change items on the menu.

Question: ${input}`,
      docs,
    });

    return text;
  }
);
```

## Write your own indexers and retrievers

It's also possible to create your own retriever. This is useful if your
documents are managed in a document store that is not supported in Genkit (eg:
MySQL, Google Drive, etc.). The Genkit SDK provides flexible methods that let
you provide custom code for fetching documents. You can also define custom
retrievers that build on top of existing retrievers in Genkit and apply advanced
RAG techniques (such as reranking or prompt extensions) on top.

### Simple Retrievers

Simple retrievers let you easily convert existing code into retrievers:

```ts
import { z } from "genkit";
import { searchEmails } from "./db";

ai.defineSimpleRetriever(
  {
    name: "myDatabase",
    configSchema: z
      .object({
        limit: z.number().optional(),
      })
      .optional(),
    // we'll extract "message" from the returned email item
    content: "message",
    // and several keys to use as metadata
    metadata: ["from", "to", "subject"],
  },
  async (query, config) => {
    const result = await searchEmails(query.text, { limit: config.limit });
    return result.data.emails;
  }
);
```

### Custom Retrievers

```ts
import {
  CommonRetrieverOptionsSchema,
} from 'genkit/retriever';
import { z } from 'genkit';

export const menuRetriever = devLocalRetrieverRef('menuQA');

const advancedMenuRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  preRerankK: z.number().max(1000),
});

const advancedMenuRetriever = ai.defineRetriever(
  {
    name: `custom/advancedMenuRetriever`,
    configSchema: advancedMenuRetrieverOptionsSchema,
  },
  async (input, options) => {
    const extendedPrompt = await extendPrompt(input);
    const docs = await ai.retrieve({
      retriever: menuRetriever,
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

```ts
const docs = await ai.retrieve({
  retriever: advancedRetriever,
  query: input,
  options: { preRerankK: 7, k: 3 },
});
```

### Rerankers and Two-Stage Retrieval

A reranking model — also known as a cross-encoder — is a type of model that,
given a query and document, will output a similarity score. We use this score to
reorder the documents by relevance to our query. Reranker APIs take a list of
documents (for example the output of a retriever) and reorders the documents
based on their relevance to the query. This step can be useful for fine-tuning
the results and ensuring that the most pertinent information is used in the
prompt provided to a generative model.

#### Reranker Example

A reranker in Genkit is defined in a similar syntax to retrievers and indexers.
Here is an example using a reranker in Genkit. This flow reranks a set of
documents based on their relevance to the provided query using a predefined
Vertex AI reranker.

```ts
const FAKE_DOCUMENT_CONTENT = [
  'pythagorean theorem',
  'e=mc^2',
  'pi',
  'dinosaurs',
  'quantum mechanics',
  'pizza',
  'harry potter',
];

export const rerankFlow = ai.defineFlow(
  {
    name: 'rerankFlow',
    inputSchema: z.object({ query: z.string() }),
    outputSchema: z.array(
      z.object({
        text: z.string(),
        score: z.number(),
      })
    ),
  },
  async ({ query }) => {
    const documents = FAKE_DOCUMENT_CONTENT.map((text) =>
       ({ content: text })
    );

    const rerankedDocuments = await ai.rerank({
      reranker: 'vertexai/semantic-ranker-512',
      query:  ({ content: query }),
      documents,
    });

    return rerankedDocuments.map((doc) => ({
      text: doc.content,
      score: doc.metadata.score,
    }));
  }
);
```

This reranker uses the Vertex AI genkit plugin with `semantic-ranker-512` to
score and rank documents. The higher the score, the more relevant the document
is to the query.

#### Custom Rerankers

You can also define custom rerankers to suit your specific use case. This is
helpful when you need to rerank documents using your own custom logic or a
custom model. Here’s a simple example of defining a custom reranker:

```ts
export const customReranker = ai.defineReranker(
  {
    name: 'custom/reranker',
    configSchema: z.object({
      k: z.number().optional(),
    }),
  },
  async (query, documents, options) => {
    // Your custom reranking logic here
    const rerankedDocs = documents.map((doc) => {
      const score = Math.random(); // Assign random scores for demonstration
      return {
        ...doc,
        metadata: { ...doc.metadata, score },
      };
    });

    return rerankedDocs.sort((a, b) => b.metadata.score - a.metadata.score).slice(0, options.k || 3);
  }
);
```

Once defined, this custom reranker can be used just like any other reranker in
your RAG flows, giving you flexibility to implement advanced reranking
strategies.
