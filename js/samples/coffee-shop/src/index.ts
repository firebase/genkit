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

import { initializeGenkit } from '@genkit-ai/core/config';
import { definePrompt } from '@genkit-ai/dotprompt';
import { flow, runFlow } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

// This example generates greetings for a customer at our new AI-powered coffee shop,
// demonstrating how to use prompts in Genkit flows.

// A flow to greet a customer by name

const CustomerNameSchema = z.object({
  customerName: z.string(),
});

const simpleGreetingPrompt = definePrompt(
  {
    name: 'simpleGreeting',
    model: geminiPro,
    input: { schema: CustomerNameSchema },
    output: {
      format: 'text',
    },
  },
  `
You're a barista at a nice coffee shop.  
A regular customer named {{customerName}} enters.
Greet the customer in one sentence, and recommend a coffee drink.
`
);

export const simpleGreetingFlow = flow(
  { name: 'simpleGreeting', input: CustomerNameSchema, output: z.string() },
  async (input) =>
    (await simpleGreetingPrompt.generate({ input: input })).text()
);

// Another flow to recommend a drink based on the time of day and a previous order.
// This prompt uses multiple messages, alternating roles
// to make the response more conversational.

const CustomerTimeAndHistorySchema = z.object({
  customerName: z.string(),
  currentTime: z.string(),
  previousOrder: z.string(),
});

const greetingWithHistoryPrompt = definePrompt(
  {
    name: 'greetingWithHistory',
    model: geminiPro,
    input: { schema: CustomerTimeAndHistorySchema },
    output: {
      format: 'text',
    },
  },
  `
{{role "user"}}
Hi, my name is {{customerName}}. The time is {{currentTime}}. Who are you?

{{role "model"}}
I am Barb, a barista at this nice underwater-themed coffee shop called Krabby Kooffee.  
I know pretty much everything there is to know about coffee, 
and I can cheerfully recommend delicious coffee drinks to you based on whatever you like.

{{role "user"}} 
Great. Last time I had {{previousOrder}}.
I want you to greet me in one sentence, and recommend a drink.
`
);

export const greetingWithHistoryFlow = flow(
  {
    name: 'greetingWithHistory',
    input: CustomerTimeAndHistorySchema,
    output: z.string(),
  },
  async (input) =>
    (await greetingWithHistoryPrompt.generate({ input: input })).text()
);

// A flow to quickly test all the above flows
// Run on the CLI with `$ genkit flow:run testAllCoffeeFlows`
// View the trace in the dev ui to see the llm responses.

export const testAllCoffeeFlows = flow(
  {
    name: 'testAllCoffeeFlows',
    input: z.void(),
    output: z.object({
      pass: z.boolean(),
      error: z.string().optional(),
    }),
  },
  async () => {
    const test1 = runFlow(simpleGreetingFlow, { customerName: 'Sam' });
    const test2 = runFlow(greetingWithHistoryFlow, {
      customerName: 'Sam',
      currentTime: '09:45am',
      previousOrder: 'Caramel Macchiato',
    });

    return Promise.all([test1, test2])
      .then((unused) => {
        return { pass: true };
      })
      .catch((e: Error) => {
        return { pass: false, error: e.toString() };
      });
  }
);
