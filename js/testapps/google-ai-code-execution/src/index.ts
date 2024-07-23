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
import * as z from 'zod';
config();
// Import the Genkit core libraries and plugins.
import { generate } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { googleAI } from '@genkit-ai/googleai';

// Import models from the Google AI plugin. The Google AI API provides access to
// several generative models. Here, we import Gemini 1.5 Flash.
import { gemini15Flash } from '@genkit-ai/googleai';

// From the Firebase plugin, import the functions needed to deploy flows using
// Cloud Functions.
import { defineFlow } from '@genkit-ai/flow';

configureGenkit({
  plugins: [
    // Load the Firebase plugin, which provides integrations with several
    // Firebase services.
    // Load the Google AI plugin. You can optionally specify your API key
    // by passing in a config object; if you don't, the Google AI plugin uses
    // the value from the GOOGLE_GENAI_API_KEY environment variable, which is
    // the recommended practice.
    googleAI(),
  ],
  // Log debug output to tbe console.
  logLevel: 'debug',
  // Perform OpenTelemetry instrumentation and enable trace collection.
  enableTracingAndMetrics: true,
});

// Define a simple flow that prompts an LLM to generate menu suggestions.
export const menuSuggestionFlow = defineFlow(
  {
    name: 'menuSuggestionFlow',
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
    const llmResponse = await generate({
      model: gemini15Flash,
      prompt: prompt,
      config: {
        temperature: 1,
        codeExecution: true,
      },
    });

    const parts = llmResponse.candidates[0].message.content;

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
