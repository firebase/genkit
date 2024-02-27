import { prompt, promptTemplate } from '@google-genkit/ai';
import { retrieve, TextDocument, index } from '@google-genkit/ai/retrievers';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, runFlow } from '@google-genkit/flow';
import {
  pineconeRetrieverRef,
  pineconeIndexerRef,
} from '@google-genkit/providers/pinecone';
import * as z from 'zod';
import config from './genkit.conf';
import { generate } from '@google-genkit/ai/generate';
import { geminiPro } from '@google-genkit/plugin-vertex-ai';
import {
  chromaRetrieverRef,
  chromaIndexerRef,
} from '@google-genkit/providers/chroma';

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
export const askQuestionsAboutSpongebobFlow = flow(
  {
    name: 'askQuestionsAboutSpongebobFlow',
    input: z.string(),
    output: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: spongeBobFactsRetriever,
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
      indexer: spongeBobFactsIndexer,
      docs: transformedDocs,
    });
  }
);

async function main() {
  const tjIndexingOp = await runFlow(indexSpongebobDocumentsFlow, [
    'SpongeBob has a pet snail',
  ]);
  console.log('Operation', tjIndexingOp);

  const tjOp = await runFlow(
    askQuestionsAboutSpongebobFlow,
    "Who is spongebob's pet?"
  );
  console.log('Operation', tjOp);
}

main().catch(console.error);
