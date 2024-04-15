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

import { defineFlow, run, runFlow } from '@genkit-ai/flow';
import * as z from 'zod';

//
// Flow - simple
//

const singleStepFlow = defineFlow({ name: 'singleStepFlow' }, async (input) => {
  return await run('step1', async () => {
    return input;
  });
});

//
// Flow - multiStep
//

const multiStepFlow = defineFlow({ name: 'multiStepFlow' }, async (input) => {
  let i = 1;

  const result1 = await run('step1', async () => {
    return `${input} ${i++},`;
  });

  const result2 = await run('step2', async () => {
    return `${result1} ${i++},`;
  });

  return await run('step3', async () => {
    return `${result2} ${i++}`;
  });
});

//
// Flow - nested
//

defineFlow({ name: 'nestedFlow', outputSchema: z.string() }, async () => {
  return JSON.stringify(
    {
      firstResult: await runFlow(singleStepFlow, 'hello, world!'),
      secondResult: await runFlow(multiStepFlow, 'hello, world!'),
    },
    null,
    2
  );
});

//
// Flow - streaming
//

defineFlow(
  {
    name: 'streamingFlow',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: z.number(),
  },
  async (count, streamingCallback) => {
    let i = 1;
    if (streamingCallback) {
      for (; i <= count; i++) {
        await new Promise((r) => setTimeout(r, 500));
        streamingCallback(i);
      }
    }
    return `done: ${count}, streamed: ${i - 1} times`;
  }
);

// TODO(michaeldoyle) migrate the rest of flow-sample1 standard flows here
