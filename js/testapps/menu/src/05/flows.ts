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

import fs from 'fs';
import { defineFlow, z } from 'genkit';
import path from 'path';
import {
  AnswerOutputSchema,
  MenuQuestionInputSchema,
  TextMenuQuestionInputSchema,
} from '../types.js';
import { s05_readMenuPrompt, s05_textMenuPrompt } from './prompts.js';

// Define a flow that takes an image, passes it to Gemini Vision Pro,
// and extracts all of the text from the photo of the menu.
// Note that this example uses a hard-coded image file, as image input
// is not currently available in the Development UI runners.

export const s05_readMenuFlow = defineFlow(
  {
    name: 's05_readMenuFlow',
    inputSchema: z.void(), // input is data/menu.jpeg
    outputSchema: z.object({ menuText: z.string() }),
  },
  async (unused) => {
    const imageDataUrl = await inlineDataUrl('menu.jpeg', 'image/jpeg');
    const response = await s05_readMenuPrompt.generate({
      input: {
        imageUrl: imageDataUrl,
      },
    });
    return { menuText: response.text() };
  }
);

// Define a flow which generates a response to the question.
// Just returns the llm's text response to the question.

export const s05_textMenuQuestionFlow = defineFlow(
  {
    name: 's05_textMenuQuestion',
    inputSchema: TextMenuQuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input) => {
    const response = await s05_textMenuPrompt.generate({
      input: {
        menuText: input.menuText,
        question: input.question,
      },
    });
    return { answer: response.text() };
  }
);

// Define a third composite flow which chains the first two flows

export const s05_visionMenuQuestionFlow = defineFlow(
  {
    name: 's05_visionMenuQuestion',
    inputSchema: MenuQuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input) => {
    // Run the first flow to read the menu image.
    const menuResult = await s05_readMenuFlow();

    // Pass the text of the menu and the question to the second flow
    // and return the answer as this output.
    return s05_textMenuQuestionFlow({
      question: input.question,
      menuText: menuResult.menuText,
    });
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
