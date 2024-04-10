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

import { generate } from '@genkit-ai/ai';
import { defineFlow } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/vertexai';
import { AnswerOutputSchema, MenuQuestionInputSchema } from '../types';
import { s02_dataMenuPrompt } from './prompts';
import { menuTool } from './tools';

// Define a flow which generates a response from the prompt.
// The prompt uses a tool which will load the menu data,
// if the user asks a reasonable question about the menu.

export const s02_menuQuestionFlow = defineFlow(
  {
    name: 's02_menuQuestion',
    inputSchema: MenuQuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input) => {
    // Note, using generate() instead of Prompt.generate()
    // to work around a bug in tool usage.
    return generate({
      model: geminiPro,
      tools: [menuTool], // This tool includes the menu
      prompt: s02_dataMenuPrompt.renderText({ question: input.question }),
    }).then((response) => {
      return { answer: response.text() };
    });
  }
);
