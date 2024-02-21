import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run } from '@google-genkit/flow';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    const foo = await run('call-llm', async () => {
      return `subject: ${subject}`;
    });
    return await run('call-llm', async () => {
      return `foo: ${foo}`;
    });
  }
);
