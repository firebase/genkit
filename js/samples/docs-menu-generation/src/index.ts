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
import { MessageData } from '@genkit-ai/ai/model';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import { geminiPro, geminiProVision, googleAI } from '@genkit-ai/googleai';
import * as z from 'zod';
import { sampleMenuHistory } from './menuHistory';

configureGenkit({
  plugins: [googleAI()],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

export const menuSuggestionFlowStreaming = defineFlow(
  {
    name: 'menuSuggestionFlowStreaming',
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

    console.log((await response()).text());
  }
);

let historyMap: MessageData[] = sampleMenuHistory;
export const menuHistoryFlow = defineFlow(
  {
    name: 'menuHistoryFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    let history = historyMap;
    let response = await generate({
      prompt: `Suggest a menu item description for a ${subject} themed restaurant`,
      model: geminiPro,
      history,
    });
    historyMap = response.toHistory();
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
