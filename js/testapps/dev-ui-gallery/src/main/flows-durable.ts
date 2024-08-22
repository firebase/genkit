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

import { prompt } from '@genkit/dotprompt';
import { run } from '@genkit/flow';
import {
  durableFlow,
  interrupt,
  scheduleFlow,
  sleep,
  waitFor,
} from '@genkit/flow/experimental';
import * as z from 'zod';
import { HelloSchema } from '../common/types.js';

//
// Durable flow - interrupts for approval
//

durableFlow(
  {
    name: 'durableFlowInterrupt',
    inputSchema: HelloSchema,
    outputSchema: z.string(),
  },
  async (input) => {
    const codeDefinedPrompt = await prompt('codeDefinedPrompt');

    const response = await codeDefinedPrompt.generate({
      input: input,
    });

    await run(
      'notify-reviewer',
      async () => await notifyReviewer(response.text())
    );

    const review = await interrupt(
      'review',
      z.object({ approved: z.boolean() })
    );

    if (review.approved) {
      return response.text();
    } else {
      return 'Sorry, content was not approved.';
    }
  }
);

async function notifyReviewer(llmResponse: string) {
  console.log('notifyReviewer', llmResponse);
}

//
// Durable flow - sleep
//

const durableFlowSleep = durableFlow(
  {
    name: 'durableFlowSleep',
    outputSchema: z.string(),
  },
  async () => {
    const step1 = await run('step1', async () => {
      return 'foo';
    });

    await sleep('sleeping', 10);

    const step2 = await run('step2', async () => {
      return 'bar';
    });

    return `${step1} ${step2}`;
  }
);

//
// Durable flow - wait
//

durableFlow(
  {
    name: 'durableFlowWaitFor',
    outputSchema: z.string(),
  },
  async () => {
    const flowOp = await run('step1', async () => {
      return await scheduleFlow(durableFlowSleep, undefined);
    });

    const [op] = await waitFor('step2', durableFlowSleep, [flowOp.name]);

    return await run('step3', async () => {
      return JSON.stringify(op.result);
    });
  }
);
