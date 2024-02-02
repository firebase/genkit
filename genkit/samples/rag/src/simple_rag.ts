import * as z from 'zod';
import { flow, runFlow, useFirestoreStateStore } from '@google-genkit/flow';
import {
  retrieve,
  index,
  type TextDocument,
} from '@google-genkit/ai/retrievers';
import { configureNaiveFilestore } from '@google-genkit/providers/vectorstores';
import {
  enableTracingAndMetrics,
  useFirestoreTraceStore,
} from '@google-genkit/common/tracing';
import { configureVertexTextEmbedder } from '@google-genkit/providers/embedders';
import { getProjectId } from '@google-genkit/common';
import { configureVertexAiTextModel } from '@google-genkit/providers/llms';
import { prompt, promptTemplate } from '@google-genkit/ai';
import { generateText } from '@google-genkit/ai/text';

// Setup GenKit for using providers and observability
useFirestoreStateStore({ projectId: getProjectId() });
useFirestoreTraceStore({ projectId: getProjectId() });

enableTracingAndMetrics();

// Setup the models, embedders and "vector store"
const gemini = configureVertexAiTextModel({ modelName: 'gemini-pro' });
const vertexEmbedder = configureVertexTextEmbedder({
  projectId: getProjectId(),
  modelName: 'textembedding-gecko@001',
});
const spongebobFacts = configureNaiveFilestore({
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
export const askQuestionsAboutSpongebobFlow = flow(
  {
    name: 'askQuestionsAboutSpongebobFlow',
    input: z.string(),
    output: z.string(),
    local: true,
  },
  async (query) => {
    const docs = await retrieve({
      dataStore: spongebobFacts,
      query,
      options: { k: 3 },
    });

    const augmentedPrompt = await promptTemplate({
      template: prompt(ragTemplate),
      variables: {
        question: query,
        context: docs.map((d) => d.content).join('\n\n'),
      },
    });

    const llmResponse = await generateText({
      model: gemini,
      prompt: augmentedPrompt,
    });
    return llmResponse.completion;
  }
);

// Define a flow to index documents into the "vector store"
const indexDocumentsFlow = flow(
  {
    name: 'indexSpongebobFacts',
    input: z.array(z.string()),
    output: z.void(),
    local: true,
  },
  async (docs) => {
    const transformedDocs: TextDocument[] = docs.map((text) => {
      return {
        content: text,
        metadata: { type: 'tv', show: 'Spongebob' },
      };
    });
    await index({
      dataStore: spongebobFacts,
      docs: transformedDocs,
      options: {} /* options not yet defined */,
    });
  }
);

async function main() {
  // First let us ingest some docs into the naive filestore
  const docs = [
    "SpongeBob's primary job is working as the fry cook at the Krusty Krab, where he takes immense pride in making Krabby Patties.",
    'SpongeBob is known for his unwavering cheerfulness and optimism, no matter what challenges come his way. He always sees the best in every situation.',
    'SpongeBob is incredibly loyal to his friends, especially Patrick Star and Sandy Cheeks. He cherishes spending time with them and going on adventures.',
    'SpongeBob can be a little gullible and easily tricked, which sometimes leads him into trouble. But his innocence is also part of his charm.',
    'SpongeBob is a yellow sea sponge, which explains his absorbent abilities and his rectangular shape.',
  ];

  const indexOperation = await runFlow(indexDocumentsFlow, docs);
  console.log('Operation', indexOperation);
  console.log('Finished indexing documents!');

  const qaOperation = await runFlow(
    askQuestionsAboutSpongebobFlow,
    'Who is spongebob?'
  );
  console.log('Operation', qaOperation);
}

main();
