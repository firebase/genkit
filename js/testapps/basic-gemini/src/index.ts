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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { generate, genkit, z } from 'genkit';
import { lotr } from './content';
const ai = genkit({
  plugins: [googleAI()],
});

export const lotrFlow = ai.defineFlow(
  {
    name: 'lotrFlow',
    inputSchema: z.object({
      preprocess: z.string().optional(),
      query: z.string().optional(),
    }),
    outputSchema: z.string(),
  },
  async ({ preprocess, query }) => {
    const extractQuotesResponse = await generate({
      history: [
        // CachedContent can not be used with GenerateContent request setting system_instruction, tools or tool_config.
        // {
        //   role: 'system',
        //   content: [
        //     {
        //       text: "You are an literature expert, and your job is to answer the user's query based on the text provided.",
        //     },
        //   ],
        // },
        {
          role: 'user',
          content: [{ text: lotr }],
        },
        {
          role: 'model',
          content: [
            {
              text:
                preprocess ||
                'This is the first three chapters of Lord of the Rings. Can I help in any way?',
            },
          ],
          // @ts-ignore
          contextCache: true,
        },
      ],
      config: {
        version: 'gemini-1.5-flash-001',
        // @ts-ignore
        useContextCache: true,
      },
      model: gemini15Flash,
      prompt: `Extract all the quotes by Gandalf to Frodo into a list.`,
    });

    const history = extractQuotesResponse.toHistory();

    return extractQuotesResponse.text();

    // // set contextCache to true for the last message in the history
    // // @ts-ignore
    // history[history.length - 1].contextCache = true;

    // const llmResponse = await generate({
    //   history,
    //   config: {
    //     version: 'gemini-1.5-flash-001',
    //     // @ts-ignore
    //     useContextCache: true,
    //   },
    //   model: gemini15Flash,
    //   // prompt: query,
    //   prompt: query || `What was the first thing Gandalf says to Frodo?`,
    // });

    // const response = llmResponse.text();

    // return response;
  }
);
