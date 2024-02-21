import { initializeGenkit } from '@google-genkit/common/config';
import { flow, interrupt, run, runMap } from '@google-genkit/flow';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

/**
 * To run this flow;
 *   genkit flow:run basic "\"hello\""
 */
export const basic = flow(
  { name: 'basic', input: z.string(), output: z.string() },
  async (subject) => {
    const foo = await run('call-llm', async () => {
      return `subject: ${subject}`;
    });
    return await run('call-llm', async () => {
      return `foo: ${foo}`;
    });
  }
);

/**
 * To run this flow;
 *   genkit flow:run simpleFanout
 */
export const simpleFanout = flow(
  { name: 'simpleFanout', input: z.void(), output: z.string() },
  async () => {
    const fanValues = await run('fan-generator', async () => {
      return ['a', 'b', 'c', 'd'];
    });
    const remapped = await runMap('remap', fanValues, async (f) => {
      return 'foo-' + f;
    });

    return remapped.join(', ');
  }
);

/**
 * To run this flow;
 *   genkit flow:run kitchensink "\"hello\""
 *   genkit flow:resume kitchensink FLOW_ID "\"foo\""
 *   genkit flow:resume kitchensink FLOW_ID "\"bar\""
 *   genkit flow:resume kitchensink FLOW_ID "\"baz\""
 *   genkit flow:resume kitchensink FLOW_ID "\"aux\""
 *   genkit flow:resume kitchensink FLOW_ID "\"final\""
 */
export const kitchensink = flow(
  { name: 'kitchensink', input: z.string(), output: z.string() },
  async (i) => {
    const hello = await run('say-hello', async () => {
      return 'hello';
    });
    let fan = await run('fan-generator', async () => {
      return ['a', 'b', 'c', 'd'];
    });
    fan = await Promise.all(
      fan.map((f) =>
        run('remap', async () => {
          return 'z-' + f;
        })
      )
    );

    const fanResult: string[] = [];
    for (const foo of fan) {
      fanResult.push(
        await interrupt('fan', z.string(), async (input) => {
          return 'fanned-' + foo + '-' + input;
        })
      );
    }

    const something = await interrupt(
      'wait-for-human-input',
      z.string(),
      async (input) => {
        return (
          i +
          ' was the input, then ' +
          hello +
          ', then ' +
          fanResult.join(', ') +
          ', human said: ' +
          input
        );
      }
    );

    return something;
  }
);
