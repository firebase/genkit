import { prompt, promptTemplate } from '@google-genkit/ai';
import {
  index,
  retrieve,
  type TextDocument,
} from '@google-genkit/ai/retrievers';
import { getProjectId } from '@google-genkit/common';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, runFlow } from '@google-genkit/flow';
import { configureVertexTextEmbedder } from '@google-genkit/providers/google-vertexai';
import { configurePinecone } from '@google-genkit/providers/pinecone';
import * as z from 'zod';
import config from './genkit.conf';
import { generate } from '@google-genkit/ai/generate';
import { geminiPro } from '@google-genkit/providers/vertex-ai';

initializeGenkit(config);

// Setup the models, embedders and "vector store"
const vertexEmbedder = configureVertexTextEmbedder({
  projectId: getProjectId(),
  modelName: 'textembedding-gecko@001',
});
const tomAndJerryFacts = configurePinecone({
  indexId: 'tom-and-jerry',
  apiKey: process.env['PINECONE_API_KEY'] ?? '',
  embedder: vertexEmbedder,
  embedderOptions: {
    temperature: 0,
    topP: 0,
    topK: 1,
  },
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
      retriever: await tomAndJerryFacts,
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

// Define a flow to index documents into the "vector store"
const indexDocumentsFlow = flow(
  {
    name: 'indexTomAndJerryFacts',
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
      indexer: await tomAndJerryFacts,
      docs: transformedDocs,
      options: {
        namespace: '',
      },
    });
  }
);

async function main() {
  // First let us ingest some docs into the doc store
  const docs = ['Tom and Jerry was produced by Hannah and Barbera.'];

  const indexOperation = await runFlow(indexDocumentsFlow, docs);
  console.log('Operation', indexOperation);
  console.log('Finished indexing documents!');

  const qaOperation = await runFlow(
    askQuestionsAboutTomAndJerryFlow,
    'Who produced Tom and Jerry?'
  );
  console.log('Operation', qaOperation);
}

main().catch(console.error);
