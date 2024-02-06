import * as z from 'zod';
import {
  flow,
  runFlow,
  useFirestoreStateStore,
  run,
} from '@google-genkit/flow';
import { useGoogleAI, useOpenAI } from '@google-genkit/providers/models';
import { generate } from '@google-genkit/ai/generate';
import { getProjectId } from '@google-genkit/common';
import { setLogLevel } from '@google-genkit/common/logging';
import {
  enableTracingAndMetrics,
  useFirestoreTraceStore,
} from '@google-genkit/common/tracing';

setLogLevel('debug');

useFirestoreStateStore({ projectId: getProjectId() });
useFirestoreTraceStore({ projectId: getProjectId() });

enableTracingAndMetrics();

const googleAI = useGoogleAI();
const openAI = useOpenAI();

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string(), local: true },
  async (subject) => {
    return await run('call-llm', async () => {
      const model =
        Math.random() > 0.5
          ? googleAI.models.geminiPro
          : openAI.models.gpt4Turbo;
      const llmResponse = await generate({
        model,
        prompt: `Tell a joke about ${subject}.`,
      });

      return `From ${
        model.__action.metadata?.model.label
      }: ${llmResponse.text()}`;
    });
  }
);

async function main() {
  const operation = await runFlow(jokeFlow, 'banana');
  console.log('Operation', operation);
}

main();
