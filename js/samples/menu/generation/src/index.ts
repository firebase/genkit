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
import { generate } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow } from '@genkit-ai/flow';
import { geminiPro, geminiProVision, googleAI } from '@genkit-ai/googleai';
import fs from 'fs';
import path from 'path';
import * as z from 'zod';

configureGenkit({
  plugins: [googleAI()],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

const menuQAFlow = defineFlow(
  {
    name: 'menuQAFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await generate({
      model: geminiPro,
      prompt: `Our menu today includes burgers, spinach, and cod.
      Tell me if ${subject} can be found on the menu`,
      config: {
        temperature: 1,
      },
    });

    return llmResponse.text();
  }
);

const readMenuFlow = defineFlow(
  {
    name: 'readMenuFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const imageDataUrl = await inlineDataUrl('menu.jpeg', 'image/jpeg');
    const llmResponse = await generate({
      model: geminiProVision,
      prompt: [
        { text: `This is our menu today: ` },
        { media: { url: imageDataUrl, contentType: 'image/jpeg' } },
        { text: `Tell me if ${subject} can be found on the menu` },
      ],
      config: {
        temperature: 1,
      },
    });

    return llmResponse.text();
  }
);

// Helper to read a local file and inline it as a data url
async function inlineDataUrl(
  imageFilename: string,
  contentType: string
): Promise<string> {
  const filePath = path.join('./data', imageFilename);
  const imageData = fs.readFileSync(filePath);
  return `data:${contentType};base64,${imageData.toString('base64')}`;
}
