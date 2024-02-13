import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run, runFlow } from '@google-genkit/flow';
import * as z from 'zod';

initializeGenkit();

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string(), local: true },
  async (subject) => {
    const foo = await run('call-llm', async () => {
      return `subject: ${subject}`;
    });
    return await run('call-llm', async () => {
      return `foo: ${foo}`;
    });
  }
);

async function main() {
  const op = await runFlow(jokeFlow, 'subj');
  console.log(op);
}

main();
