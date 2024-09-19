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

import { firebase } from '@genkit-ai/firebase';
import { googleAI } from '@genkit-ai/googleai';
import { vertexAI } from '@genkit-ai/vertexai';
import { GoogleVertexAIEmbeddings } from '@langchain/community/embeddings/googlevertexai';
import { GoogleVertexAI } from '@langchain/community/llms/googlevertexai';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { PromptTemplate } from '@langchain/core/prompts';
import {
  RunnablePassthrough,
  RunnableSequence,
} from '@langchain/core/runnables';
import { configureGenkit, defineFlow, run, startFlowsServer, z } from 'genkit';
import { GenkitTracer } from 'genkitx-langchain';
import { ollama } from 'genkitx-ollama';
import { PDFLoader } from 'langchain/document_loaders/fs/pdf';
import { formatDocumentsAsString } from 'langchain/util/document';
import { MemoryVectorStore } from 'langchain/vectorstores/memory';

configureGenkit({
  plugins: [
    firebase(),
    googleAI(),
    vertexAI(),
    ollama({
      models: [
        { name: 'llama2', type: 'generate' },
        { name: 'gemma', type: 'chat' },
      ],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

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
