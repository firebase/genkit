# Using LangChain with Genkit

## Installation

```posix-terminal
npm i --save genkitx-langchain
```

## Usage

You can use most LangChain chains or utilities in Genkit flows as is. The example below
uses LangChain retrievers, document loaders, and chain constructs to build a naive RAG sample.

```js
import { initializeGenkit } from '@genkit-ai/core';
import { defineFlow, run, startFlowsServer } from '@genkit-ai/flow';
import { GoogleVertexAIEmbeddings } from '@langchain/community/embeddings/googlevertexai';
import { GoogleVertexAI } from '@langchain/community/llms/googlevertexai';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { PromptTemplate } from '@langchain/core/prompts';
import {
  RunnablePassthrough,
  RunnableSequence,
} from '@langchain/core/runnables';
import { GenkitTracer } from 'genkitx-langchain';
import { PDFLoader } from 'langchain/document_loaders/fs/pdf';
import { formatDocumentsAsString } from 'langchain/util/document';
import { MemoryVectorStore } from 'langchain/vectorstores/memory';
import * as z from 'zod';

import config from './genkit.config';

initializeGenkit(config);

const vectorStore = new MemoryVectorStore(new GoogleVertexAIEmbeddings());
const model = new GoogleVertexAI();

export const indexPdf = defineFlow(
  { name: 'indexPdf', inputSchema: z.string(), outputSchema: z.void() },
  async (filePath) => {
    const docs = await run('load-pdf', async () => {
      return await new PDFLoader(filePath).load();
    });
    await run('index', async () => {
      vectorStore.addDocuments(docs);
    });
  }
);

const prompt =
  PromptTemplate.fromTemplate(`Answer the question based only on the following context:
{context}

Question: {question}`);
const retriever = vectorStore.asRetriever();

export const pdfQA = defineFlow(
  { name: 'pdfQA', inputSchema: z.string(), outputSchema: z.string() },
  async (question) => {
    const chain = RunnableSequence.from([
      {
        context: retriever.pipe(formatDocumentsAsString),
        question: new RunnablePassthrough(),
      },
      prompt,
      model,
      new StringOutputParser(),
    ]);

    return await chain.invoke(question, { callbacks: [new GenkitTracer()] });
  }
);

startFlowsServer();
```

Note that the example uses `GenkitTracer` provided by the `genkitx-langchain` plugin to instrument LangChain
chains with Genkit observability features. Now when you run the flow from Dev UI or in production,
you will be getting full visibility into the LangChain chains.

Also note that LangChain components are not interoperable with Genkit primitives (models,
documents, retrievers, etc.).

### Evaluators (Preview)

You can use [LangChain evaluators](https://js.langchain.com/docs/guides/evaluation/) with Genkit.
Configure which evaluators you want from the `langchain` plugin and then follow the standard
evaluation process:

```js
import { langchain } from 'genkitx-langchain';

configureGenkit({
  plugins: [
    langchain({
      evaluators: {
        judge: geminiPro,
        criteria: ['harmfulness', 'maliciousness'],
      },
    }),
  ],
});
```
