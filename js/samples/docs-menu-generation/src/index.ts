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

// This sample is referenced by the genkit docs. Changes should be made to
// both.
import { generate, generateStream } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import { geminiPro, geminiProVision, googleAI } from '@genkit-ai/googleai';
import * as z from 'zod';

configureGenkit({
  plugins: [googleAI()],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

export const menuStreamingSuggestionFlow = defineFlow(
  {
    name: 'menuStreamingSuggestionFlow',
    inputSchema: z.string(),
    outputSchema: z.void(),
  },
  async (subject) => {
    const { response, stream } = await generateStream({
      prompt: `Suggest many items for the menu of a ${subject} themed restaurant`,
      model: geminiPro,
      config: {
        temperature: 1,
      },
    });

    for await (let chunk of stream()) {
      for (let content of chunk.content) {
        console.log(content.text);
      }
    }

    // you can also await the full response
    console.log((await response()).text());
  }
);

export const menuHistoryFlow = defineFlow(
  {
    name: 'menuHistoryFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    // lets do few-shot examples: generate a few different generations, keep adding the history
    // before generating an item for the menu of a themed restaurant
    let response = await generate({
      prompt: `Create examples of delicious menu entrees`,
      model: geminiPro,
    });
    let history = response.toHistory();

    response = await generate({
      prompt: `Chicken is my favorite meat`,
      model: geminiPro,
      history,
    });
    history = response.toHistory();

    response = await generate({
      prompt: `Suggest an item for the menu of a ${subject} themed restaurant`,
      model: geminiPro,
      history,
    });
    return response.text();
  }
);

export const menuImageFlow = defineFlow(
  {
    name: 'menuImageFlow',
    inputSchema: z.object({ imageUrl: z.string(), subject: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    const visionResponse = await generate({
      model: geminiProVision,
      prompt: [
        {
          text: `Extract _all_ of the text, in order, 
          from the following image of a restaurant menu.`,
        },
        { media: { url: input.imageUrl, contentType: 'image/jpeg' } },
      ],
    });
    const imageDescription = visionResponse.text();

    const response = await generate({
      model: geminiPro,
      prompt: `Here is the text of today's menu: ${imageDescription} 
      Rename the items to match the restaurant's ${input.subject} theme.`,
    });

    return response.text();
  }
);

startFlowsServer();
