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

import { googleAI } from '@genkit-ai/google-genai';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
});

// This example generates greetings for a customer at our new AI-powered coffee shop.
// We use inline prompts (template literals) instead of definePrompt() so the app
// runs on Workers, where definePrompt/Handlebars are not supported.

const CustomerNameSchema = z.object({
  customerName: z.string(),
});

export const simpleGreetingFlow = ai.defineFlow(
  {
    name: 'simpleGreeting',
    inputSchema: CustomerNameSchema,
    outputSchema: z.string(),
  },
  async (input) => {
    const prompt = `You're a barista at a nice coffee shop.
A regular customer named ${input.customerName} enters.
Greet the customer in one sentence, and recommend a coffee drink.`;
    const { text } = await ai.generate({
      prompt,
      model: googleAI.model('gemini-2.5-flash'),
    });
    return text ?? '';
  }
);

// Another flow to recommend a drink based on the time of day and a previous order.

const CustomerTimeAndHistorySchema = z.object({
  customerName: z.string(),
  currentTime: z.string(),
  previousOrder: z.string(),
});

export const greetingWithHistoryFlow = ai.defineFlow(
  {
    name: 'greetingWithHistory',
    inputSchema: CustomerTimeAndHistorySchema,
    outputSchema: z.string(),
  },
  async (input) => {
    const prompt = `You are Barb, a barista at a nice underwater-themed coffee shop called Krabby Kooffee.
You know pretty much everything there is to know about coffee and can cheerfully recommend drinks.

The customer says: Hi, my name is ${input.customerName}. The time is ${input.currentTime}. Who are you?
You reply as Barb introducing yourself.

The customer says: Great. Last time I had ${input.previousOrder}. I want you to greet me in one sentence, and recommend a drink.

Reply now with your one-sentence greeting and drink recommendation.`;
    const { text } = await ai.generate({
      prompt,
      model: googleAI.model('gemini-2.5-flash'),
    });
    return text ?? '';
  }
);

// A flow to quickly test all the above flows
// Run on the CLI with `$ genkit flow:run testAllCoffeeFlows`
// View the trace in the Developer UI to see the llm responses.

export const testAllCoffeeFlows = ai.defineFlow(
  {
    name: 'testAllCoffeeFlows',
    outputSchema: z.object({
      pass: z.boolean(),
      error: z.string().optional(),
    }),
  },
  async () => {
    const test1 = simpleGreetingFlow({ customerName: 'Sam' });
    const test2 = greetingWithHistoryFlow({
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
