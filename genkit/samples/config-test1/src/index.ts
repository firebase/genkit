import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, getFlowState, run, runFlow } from '@google-genkit/flow';
import { geminiPro } from '@google-genkit/providers/google-ai';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        prompt: `Tell me a joke about ${subject}`,
        model: geminiPro,
      });

      return llmResponse.text();
    });
  }
);

async function main() {
  const operation = await runFlow(jokeFlow, 'banana');
  console.log('Operation', operation);
  console.log('state', await getFlowState(jokeFlow, operation.name));
}

main().catch(console.error);
