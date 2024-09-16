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

import { generate } from '@genkit-ai/ai';
import { retrieve } from '@genkit-ai/ai/retriever';
import { defineFirestoreRetriever } from '@genkit-ai/firebase';
import { defineFlow, run } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/googleai';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { readFile } from 'fs/promises';
import { chunk } from 'llm-chunk';
import path from 'path';

import pdf from 'pdf-parse';

import { embed } from '@genkit-ai/ai/embedder';
import { textEmbeddingGecko } from '@genkit-ai/vertexai';
import { FieldValue } from '@google-cloud/firestore';
import * as z from 'zod';

const app = initializeApp();
let firestore = getFirestore(app);

// There's a race condition in initializing the Firestore singleton.
// To avoid that, explicitly create an instance using the service account
// from the environment variable.
if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
  console.log(`Using service account credentials.`);
  const serviceAccountCreds = JSON.parse(
    process.env.GCLOUD_SERVICE_ACCOUNT_CREDS
  );
  const authOptions = { credentials: serviceAccountCreds };
  firestore.settings(authOptions);
}

function ragTemplate({
  context,
  question,
}: {
  context: string;
  question: string;
}) {
  return `Use the following pieces of context to answer the question at the end.
 If you don't know the answer, just say that you don't know, don't try to make up an answer.

${context}
Question: ${question}
Helpful Answer:`;
}

export const pdfChatRetrieverFirebase = defineFirestoreRetriever({
  name: 'pdfChatRetrieverFirebase',
  firestore,
  collection: 'pdf-qa',
  contentField: 'facts',
  vectorField: 'embedding',
  embedder: textEmbeddingGecko,
  distanceMeasure: 'COSINE',
});

// Define a simple RAG flow, we will evaluate this flow
export const pdfQAFirebase = defineFlow(
  {
    name: 'pdfQAFirebase',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: pdfChatRetrieverFirebase,
      query,
      options: { limit: 3 },
    });
    console.log(docs);

    const augmentedPrompt = ragTemplate({
      question: query,
      context: docs.map((d) => d.text()).join('\n\n'),
    });
    const llmResponse = await generate({
      model: geminiPro,
      prompt: augmentedPrompt,
    });
    return llmResponse.text();
  }
);

// Firebase index config for pdfQA flow
const indexConfig = {
  collection: 'pdf-qa',
  contentField: 'facts',
  vectorField: 'embedding',
  embedder: textEmbeddingGecko,
};

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

// Define a flow to index documents into the "vector store"
// genkit flow:run indexPdf '"./docs/sfspca-cat-adoption-handbook-2023.pdf"'
export const indexPdfFirebase = defineFlow(
  {
    name: 'indexPdfFirestore',
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

    // Add chunks to the index.
    await run('index-chunks', async () => indexToFirestore(chunks));
  }
);

async function indexToFirestore(data: string[]) {
  for (const text of data) {
    const embedding = await embed({
      embedder: indexConfig.embedder,
      content: text,
    });
    await firestore.collection(indexConfig.collection).add({
      [indexConfig.vectorField]: FieldValue.vector(embedding),
      [indexConfig.contentField]: text,
    });
    // await firestore.collection(indexConfig.collection).add({ 'a': 'b' });
  }
}

async function extractTextFromPdf(filePath: string) {
  const pdfFile = path.resolve(filePath);
  const dataBuffer = await readFile(pdfFile);
  const data = await pdf(dataBuffer);
  return data.text;
}
