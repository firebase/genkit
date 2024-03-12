import { promptTemplate } from '@genkit-ai/ai';
import { generate } from '@genkit-ai/ai/generate';
import { initializeGenkit } from '@genkit-ai/common/config';
import { durableFlow, interrupt, run } from '@genkit-ai/flow/experimental';
import { geminiPro } from '@genkit-ai/plugin-google-genai';
import * as z from 'zod';
import config from './genkit.conf';

// To run this sample use the following sample commands:
//   genkit flow:run jokeFlow "\"apple\""
//   genkit flow:resume jokeFlow FLOW_ID_FROM_PREV_COMMAND "\{\"approved\":true}"

initializeGenkit(config);

export const jokeFlow = durableFlow(
  {
    name: 'jokeFlow',
    input: z.string(),
    output: z.string(),
  },
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
