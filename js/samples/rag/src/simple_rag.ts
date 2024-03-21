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

import { generate } from '@genkit-ai/ai/generate';
import { Document, index, retrieve } from '@genkit-ai/ai/retrievers';
import { initializeGenkit } from '@genkit-ai/common/config';
import { flow } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
import { chromaIndexerRef, chromaRetrieverRef } from '@genkit-ai/plugin-chroma';
import {
  devLocalRetrieverRef,
  devLocalIndexerRef,
} from '@genkit-ai/plugin-dev-local-vectorstore';
import {
  pineconeIndexerRef,
  pineconeRetrieverRef,
} from '@genkit-ai/plugin-pinecone';
import * as z from 'zod';
import config from './genkit.conf';
export * from './pdf_rag';

initializeGenkit(config);

// Setup the models, embedders and "vector store"
export const tomAndJerryFactsRetriever = pineconeRetrieverRef({
  indexId: 'tom-and-jerry',
  displayName: 'Tom and Jerry Retriever',
});

export const tomAndJerryFactsIndexer = pineconeIndexerRef({
  indexId: 'tom-and-jerry',
  displayName: 'Tom and Jerry Indexer',
});

export const spongeBobFactsRetriever = chromaRetrieverRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts retriever',
});

export const spongeBobFactsIndexer = chromaIndexerRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts indexer',
});

// Simple aliases for readability
export const nfsSpongeBobRetriever = devLocalRetrieverRef('spongebob-facts');

export const nfsSpongeBobIndexer = devLocalIndexerRef('spongebob-facts');

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

// Define a simple RAG flow, we will evaluate this flow
export const askQuestionsAboutTomAndJerryFlow = flow(
  {
    name: 'askQuestionsAboutTomAndJerrybobFlow',
    input: z.string(),
    output: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: tomAndJerryFactsRetriever,
      query,
      options: { k: 3 },
    });
    console.log(docs);

    const augmentedPrompt = ragTemplate({
      question: query,
      context: docs.map((d) => d.text()).join('\n\n'),
    });
    const model = geminiPro;
    console.log(augmentedPrompt);
    const llmResponse = await generate({
      model,
      prompt: { text: augmentedPrompt },
    });
    return llmResponse.text();
  }
);

// Define a simple RAG flow, we will evaluate this flow
// genkit flow:run askQuestionsAboutSpongebobFlow '"What is Spongebob's pet's name?"'
export const askQuestionsAboutSpongebobFlow = flow(
  {
    name: 'askQuestionsAboutSpongebobFlow',
    input: z.string(),
    output: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: nfsSpongeBobRetriever,
      query,
      options: { k: 3 },
    });
    console.log(docs);

    const augmentedPrompt = ragTemplate({
      question: query,
      context: docs.map((d) => d.text()).join('\n\n'),
    });
    const model = geminiPro;
    console.log(augmentedPrompt);
    const llmResponse = await generate({
      model,
      prompt: { text: augmentedPrompt },
    });
    return llmResponse.text();
  }
);

// Define a simple RAG flow, we will evaluate this flow
export const indexTomAndJerryDocumentsFlow = flow(
  {
    name: 'indexTomAndJerryDocumentsFlow',
    input: z.array(z.string()),
    output: z.void(),
  },
  async (docs) => {
    const documents = docs.map((text) => {
      return Document.fromText(text, { type: 'tv', show: 'Tom and Jerry' });
    });
    await index({
      indexer: tomAndJerryFactsIndexer,
      documents,
    });
  }
);

// Define a flow to index documents into the "vector store"
// genkit flow:run indexSpongebobFacts '["SpongeBob has a pet snail named Gary"]'
export const indexSpongebobDocumentsFlow = flow(
  {
    name: 'indexSpongebobFacts',
    input: z.array(z.string()),
    output: z.void(),
  },
  async (docs) => {
    const documents = docs.map((text) => {
      return Document.fromText(text, { type: 'tv', show: 'SpongeBob' });
    });
    await index({
      indexer: nfsSpongeBobIndexer,
      documents,
    });
  }
);
