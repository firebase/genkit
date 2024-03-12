import { prompt, promptTemplate } from '@genkit-ai/ai';
import { generate } from '@genkit-ai/ai/generate';
import { TextDocument, index, retrieve } from '@genkit-ai/ai/retrievers';
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

const ragTemplate = `Use the following pieces of context to answer the question at the end.
 If you don't know the answer, just say that you don't know, don't try to make up an answer.
 
{context}
Question: {question}
Helpful Answer:`;

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

    const augmentedPrompt = await promptTemplate({
      template: prompt(ragTemplate),
      variables: {
        question: query,
        context: docs.map((d) => d.content).join('\n\n'),
      },
    });
    const model = geminiPro;
    console.log(augmentedPrompt.prompt);
    const llmResponse = await generate({
      model,
      prompt: { text: augmentedPrompt.prompt },
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

    const augmentedPrompt = await promptTemplate({
      template: prompt(ragTemplate),
      variables: {
        question: query,
        context: docs.map((d) => d.content).join('\n\n'),
      },
    });
    const model = geminiPro;
    console.log(augmentedPrompt.prompt);
    const llmResponse = await generate({
      model,
      prompt: { text: augmentedPrompt.prompt },
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
    const transformedDocs: TextDocument[] = docs.map((text) => {
      return {
        content: text,
        metadata: { type: 'tv', show: 'Tom and Jerry' },
      };
    });
    await index({
      indexer: tomAndJerryFactsIndexer,
      docs: transformedDocs,
      options: {
        namespace: '',
      },
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
    const transformedDocs: TextDocument[] = docs.map((text) => {
      return {
        content: text,
        metadata: { type: 'tv', show: 'SpongeBob' },
      };
    });
    await index({
      indexer: nfsSpongeBobIndexer,
      docs: transformedDocs,
    });
  }
);
