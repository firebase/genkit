/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { initializeGenkit } from '@genkit-ai/core';
import {
  defineFlow,
  run,
  runFlow,
  runMap,
  startFlowsServer,
} from '@genkit-ai/flow';
import {
  durableFlow,
  interrupt,
  scheduleFlow,
  sleep,
  waitFor,
} from '@genkit-ai/flow/experimental';
import * as z from 'zod';
import config from './genkit.config.js';

initializeGenkit(config);

/**
 * To run this flow;
 *   genkit flow:run basic "\"hello\""
 */
export const basic = defineFlow({ name: 'basic' }, async (subject) => {
  const foo = await run('call-llm', async () => {
    return `subject: ${subject}`;
  });

  return await run('call-llm1', async () => {
    return `foo: ${foo}`;
  });
});

export const parent = defineFlow(
  { name: 'parent', outputSchema: z.string() },
  async () => {
    return JSON.stringify(await runFlow(basic, 'foo'));
  }
);

/**
 * To run this flow;
 *   genkit flow:run simpleFanout
 */
export const simpleFanout = defineFlow(
  { name: 'simpleFanout', outputSchema: z.string() },
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
export const kitchensink = durableFlow(
  {
    name: 'kitchensink',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
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

/**
 * To run this flow;
 *   genkit flow:run sleepy
 */
export const sleepy = durableFlow(
  {
    name: 'sleepy',
    outputSchema: z.string(),
  },
  async () => {
    const before = await run('before', async () => {
      return 'foo';
    });

    await sleep('take-a-nap', 10);

    const after = await run('after', async () => {
      return 'bar';
    });

    return `${before} ${after}`;
  }
);

/**
 * To run this flow;
 *   genkit flow:run waity
 */
export const waity = durableFlow(
  {
    name: 'waity',
    outputSchema: z.string(),
  },
  async () => {
    const flowOp = await run('start-sub-flow', async () => {
      return await scheduleFlow(sleepy, undefined);
    });

    const [op] = await waitFor('wait-for-other-to-complete', sleepy, [
      flowOp.name,
    ]);

    return await run('after', async () => {
      return `unpack sleepy result: ${JSON.stringify(op.result)}`;
    });
  }
);

// genkit flow:run streamy 5 -s
export const streamy = defineFlow(
  {
    name: 'streamy',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: z.object({ count: z.number() }),
  },
  async (count, streamingCallback) => {
    let i = 0;
    if (streamingCallback) {
      for (; i < count; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        streamingCallback({ count: i });
      }
    }
    return `done: ${count}, streamed: ${i} times`;
  }
);

// genkit flow:run streamy 5 -s
export const streamyThrowy = defineFlow(
  {
    name: 'streamyThrowy',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: z.object({ count: z.number() }),
  },
  async (count, streamingCallback) => {
    let i = 0;
    if (streamingCallback) {
      for (; i < count; i++) {
        if (i == 3) {
          throw new Error('whoops');
        }
        await new Promise((r) => setTimeout(r, 1000));
        streamingCallback({ count: i });
      }
    }
    return `done: ${count}, streamed: ${i} times`;
  }
);

/**
 * To run this flow;
 *   genkit flow:run throwy "\"hello\""
 */
export const throwy = defineFlow(
  { name: 'throwy', inputSchema: z.string(), outputSchema: z.string() },
  async (subject) => {
    const foo = await run('call-llm', async () => {
      return `subject: ${subject}`;
    });
    if (subject) {
      throw new Error(subject);
    }
    return await run('call-llm', async () => {
      return `foo: ${foo}`;
    });
  }
);

/**
 * To run this flow;
 *   genkit flow:run throwy2 "\"hello\""
 */
export const throwy2 = defineFlow(
  { name: 'throwy2', inputSchema: z.string(), outputSchema: z.string() },
  async (subject) => {
    const foo = await run('call-llm', async () => {
      if (subject) {
        throw new Error(subject);
      }
      return `subject: ${subject}`;
    });
    return await run('call-llm', async () => {
      return `foo: ${foo}`;
    });
  }
);

export const largeSteps = defineFlow({ name: 'largeSteps' }, async () => {
  await run('large-step1', async () => {
    return generateString(100_000);
  });
  await run('large-step2', async () => {
    return generateString(800_000);
  });
  await run('large-step3', async () => {
    return generateString(900_000);
  });
  await run('large-step4', async () => {
    return generateString(999_000);
  });
  return 'something...';
});

const loremIpsum = [
  'lorem',
  'ipsum',
  'dolor',
  'sit',
  'amet',
  'consectetur',
  'adipiscing',
  'elit',
];
function generateString(length: number) {
  let str = '';
  while (str.length < length) {
    str += loremIpsum[Math.floor(Math.random() * loremIpsum.length)] + ' ';
  }
  return str.substring(0, length);
}

startFlowsServer();
