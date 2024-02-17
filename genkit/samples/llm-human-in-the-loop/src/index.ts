import { promptTemplate } from '@google-genkit/ai';
import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, interrupt, resumeFlow, run, runFlow } from '@google-genkit/flow';
import { geminiPro } from '@google-genkit/providers/google-ai';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (inputSubject) => {
    const prompt = await run(
      'make-prompt',
      async () =>
        await promptTemplate({
          template: 'Tell me a joke about {subject}',
          variables: { subject: inputSubject },
        })
    );

    const llmResponse = await run('run-llm', async () =>
      (await generate({ model: geminiPro, prompt: prompt.prompt })).text()
    );

    await run(
      'notify-hooman-approval-is-needed',
      async () => await notifyHooman(llmResponse)
    );

    const hoomanSaid = await interrupt(
      'approve-by-hooman',
      z.object({ approved: z.boolean() })
    );

    if (hoomanSaid.approved) {
      return llmResponse;
    } else {
      return 'Sorry, the llm generated something inappropriate, please try again.';
    }
  }
);

async function notifyHooman(llmResponse: string) {
  console.log('notifyHooman', llmResponse);
}

async function main() {
  const op = await runFlow(jokeFlow, 'spongebob');
  console.log('Interrupted operation', op);
  const resumeOp = await resumeFlow(jokeFlow, op.name, { approved: true });
  console.log('Final operation', resumeOp);
}

main().catch(console.error);
