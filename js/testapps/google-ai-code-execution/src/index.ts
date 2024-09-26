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

import { config } from 'dotenv';
config();
// Import the Genkit core libraries and plugins.
import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
});

export const codeExecutionFlow = ai.defineFlow(
  {
    name: 'codeExecutionFlow',
    inputSchema: z.string(),
    outputSchema: z.object({
      executableCode: z.object({
        code: z.string(),
        language: z.string(),
      }),
      codeExecutionResult: z.object({
        outcome: z.string(),
        output: z.string(),
      }),
      text: z.string(),
    }),
  },
  async (task: string) => {
    // Construct a request and send it to the model API.
    const prompt = `Write and execute some code for ${task}`;
    const llmResponse = await ai.generate({
      model: gemini15Flash,
      prompt: prompt,
      config: {
        temperature: 1,
        codeExecution: true,
      },
    });

    const parts = llmResponse.message!.content;

    const executableCodePart = parts.find(
      (part) => part.custom && part.custom.executableCode
    );
    const codeExecutionResultPart = parts.find(
      (part) => part.custom && part.custom.codeExecutionResult
    );

    //  these are typed as any, because the custom part schema is loosely typed...
    const code = executableCodePart?.custom?.executableCode.code;
    const language = executableCodePart?.custom?.executableCode.language;

    const codeExecutionResult =
      codeExecutionResultPart?.custom?.codeExecutionResult;
    const outcome = codeExecutionResult.outcome;
    const output = codeExecutionResult.output;

    return {
      executableCode: {
        code,
        language,
      },
      codeExecutionResult: {
        outcome,
        output,
      },
      text: llmResponse.text(),
    };
  }
);
