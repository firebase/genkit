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

import { Document, index, retrieve } from '@genkit-ai/ai/retriever';
import { defineFlow } from '@genkit-ai/flow';
import { chromaIndexerRef, chromaRetrieverRef } from '@genkit-ai/plugin-chroma';
import {
  devLocalIndexerRef,
  devLocalRetrieverRef,
} from '@genkit-ai/plugin-dev-local-vectorstore';
import {
  pineconeIndexerRef,
  pineconeRetrieverRef,
} from '@genkit-ai/plugin-pinecone';
import * as z from 'zod';
import { augmentedPrompt } from './prompt.js';

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

// Define a simple RAG flow, we will evaluate this flow
export const askQuestionsAboutTomAndJerryFlow = defineFlow(
  {
    name: 'askQuestionsAboutTomAndJerrybobFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: tomAndJerryFactsRetriever,
      query,
      options: { k: 3 },
    });
    return augmentedPrompt
      .generate({
        input: {
          question: query,
          context: docs.map((d) => d.text()),
        },
      })
      .then((r) => r.text());
  }
);

// Define a simple RAG flow, we will evaluate this flow
// genkit flow:run askQuestionsAboutSpongebobFlow '"What is Spongebob's pet's name?"'
export const askQuestionsAboutSpongebobFlow = defineFlow(
  {
    name: 'askQuestionsAboutSpongebobFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: nfsSpongeBobRetriever,
      query,
      options: { k: 3 },
    });
    return augmentedPrompt
      .generate({
        input: {
          question: query,
          context: docs.map((d) => d.text()),
        },
      })
      .then((r) => r.text());
  }
);

// Define a simple RAG flow, we will evaluate this flow
export const indexTomAndJerryDocumentsFlow = defineFlow(
  {
    name: 'indexTomAndJerryDocumentsFlow',
    inputSchema: z.array(z.string()),
    outputSchema: z.void(),
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
export const indexSpongebobDocumentsFlow = defineFlow(
  {
    name: 'indexSpongebobFacts',
    inputSchema: z.array(z.string()),
    outputSchema: z.void(),
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
