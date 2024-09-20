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

import { genkit, run } from '@genkit-ai/core';
import { firebase } from '@genkit-ai/firebase';
import * as z from 'zod';

const ai = genkit({
  plugins: [firebase()],
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
  flowServer: {
    runInEnv: 'all',
  },
});

/**
 * To run this flow;
 *   genkit flow:run basic "\"hello\""
 */
export const basic = ai.defineFlow({ name: 'basic' }, async (subject) => {
  const foo = await run('call-llm', async () => {
    return `subject: ${subject}`;
  });

  return await run('call-llm1', async () => {
    return `foo: ${foo}`;
  });
});

export const parent = ai.defineFlow(
  { name: 'parent', outputSchema: z.string() },
  async () => {
    return JSON.stringify(await basic('foo'));
  }
);

// genkit flow:run streamy 5 -s
export const streamy = ai.defineStreamingFlow(
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
export const streamyThrowy = ai.defineStreamingFlow(
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
export const throwy = ai.defineFlow(
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
export const throwy2 = ai.defineFlow(
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

export const flowMultiStepCaughtError = ai.defineFlow(
  { name: 'flowMultiStepCaughtError' },
  async (input) => {
    let i = 1;

    const result1 = await run('step1', async () => {
      return `${input} ${i++},`;
    });

    let result2 = '';
    try {
      result2 = await run('step2', async () => {
        if (result1) {
          throw new Error('Got an error!');
        }
        return `${result1} ${i++},`;
      });
    } catch (e) {}

    return await run('step3', async () => {
      return `${result2} ${i++}`;
    });
  }
);

export const multiSteps = ai.defineFlow(
  { name: 'multiSteps', inputSchema: z.string(), outputSchema: z.number() },
  async (input) => {
    const out1 = await run('step1', async () => {
      return `Hello, ${input}! step 1`;
    });
    await run('step1', async () => {
      return `Hello2222, ${input}! step 1`;
    });
    const out2 = await run('step2', out1, async () => {
      return out1 + ' Faf ';
    });
    const out3 = await run('step3-array', async () => {
      return [out2, out2];
    });
    const out4 = await run('step4-num', async () => {
      return out3.join('-()-');
    });
    return 42;
  }
);

export const largeSteps = ai.defineFlow({ name: 'largeSteps' }, async () => {
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
