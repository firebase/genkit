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

import { definePrompt } from '@genkit-ai/dotprompt';
import { geminiPro } from '@genkit-ai/vertexai';
import { MenuQuestionInputSchema } from '../types';
import { menuTool } from './tools';

export const s02_dataMenuPrompt = definePrompt(
  {
    name: 's02_dataMenu',
    model: geminiPro,
    input: { schema: MenuQuestionInputSchema },
    output: { format: 'text' },
    tools: [menuTool],
  },
  `
You are acting as a helpful AI assistant named "Walt" that can answer 
questions about the food available on the menu at Walt's Burgers. 

Answer this customer's question, in a concise and helpful manner,
as long as it is about food on the menu or something harmless like sports.

Question:
{{question}} ?
`
);
