/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { initializeGenkit } from '@genkit-ai/core';
import { defineFlow, run, startFlowsServer } from '@genkit-ai/flow';
import { GoogleVertexAIEmbeddings } from '@langchain/community/embeddings/googlevertexai';
import { GoogleVertexAI } from '@langchain/community/llms/googlevertexai';
import { PromptTemplate } from '@langchain/core/prompts';
import { GenkitTracer } from './callback.js';

import { TextLoader } from 'langchain/document_loaders/fs/text';

import { StringOutputParser } from '@langchain/core/output_parsers';
import { formatDocumentsAsString } from 'langchain/util/document';
import { MemoryVectorStore } from 'langchain/vectorstores/memory';

import * as z from 'zod';
import config from './genkit.config';

import {
  RunnablePassthrough,
  RunnableSequence,
} from '@langchain/core/runnables';

initializeGenkit(config);

const vectorStore = new MemoryVectorStore(new GoogleVertexAIEmbeddings());
const model = new GoogleVertexAI();

export const indexPdf = defineFlow(
  { name: 'indexPdf', inputSchema: z.string(), outputSchema: z.void() },
  async (filePath) => {
    const docs = await run('load-pdf', async () => {
      return await new TextLoader(filePath).load();
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
