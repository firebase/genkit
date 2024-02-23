import { prompt, promptTemplate } from '@google-genkit/ai';
import { retrieve } from '@google-genkit/ai/retrievers';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, runFlow } from '@google-genkit/flow';
import { pineconeRef } from '@google-genkit/providers/pinecone';
import * as z from 'zod';
import config from './genkit.conf';
import { generate } from '@google-genkit/ai/generate';
import { geminiPro } from '@google-genkit/plugin-vertex-ai';
import { chromaRef } from '@google-genkit/providers/chroma';

initializeGenkit(config);

// Setup the models, embedders and "vector store"
export const tomAndJerryFacts = pineconeRef({
  indexId: 'tom-and-jerry',
  displayName: 'Tom and Jerry Collection',
});

export const spongeBobFacts = chromaRef({
  collectionName: 'spongebob_collection',
  displayName: 'Spongebob facts',
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
      retriever: tomAndJerryFacts,
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
      retriever: spongeBobFacts,
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

async function main() {
  const tjOp = await runFlow(
    askQuestionsAboutTomAndJerryFlow,
    'What are the other names of Tom?'
  );
  console.log('Operation', tjOp);

  const sbOp = await runFlow(
    askQuestionsAboutSpongebobFlow,
    "Who are SpongeBob's friends?"
  );
  console.log('Operation', sbOp);
}

main().catch(console.error);
