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
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';
import { noAuth, onFlow } from '@genkit-ai/firebase/functions';
import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { defineSecret } from 'firebase-functions/params';
import { genkit, z } from 'genkit';

enableFirebaseTelemetry({
  metricExportIntervalMillis: 5_000, // Export frequently to support testing workflow
  metricExportTimeoutMillis: 5_000, // Value must be less than or equal to export interval
});

const googleAIapiKey = defineSecret('GOOGLE_GENAI_API_KEY');

const ai = genkit({
  plugins: [
    // Load the Google AI plugin. You can optionally specify your API key
    // by passing in a config object; if you don't, the Google AI plugin uses
    // the value from the GOOGLE_GENAI_API_KEY environment variable, which is
    // the recommended practice.
    googleAI(),
  ],
});

// Define a simple flow that prompts an LLM to generate menu suggestions.
export const menuSuggestionFlow = onFlow(
  ai,
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.object({ subject: z.string() }),
    outputSchema: z.string(),
    authPolicy: noAuth(), // Auth is controlled by Google Cloud IAM
    httpsOptions: {
      secrets: [googleAIapiKey],
      cors: '*',
    },
  },
  async (input) => {
    // Construct a request and send it to the model API.
    const prompt = `Suggest an item for the menu of a ${input.subject} themed restaurant`;
    const llmResponse = await ai.generate({
      model: gemini15Flash,
      prompt: prompt,
      config: {
        temperature: 1,
      },
    });

    // Handle the response from the model API. In this sample, we just
    // convert it to a string, but more complicated flows might coerce the
    // response into structured output or chain the response into another
    // LLM call, etc.
    return llmResponse.text;
  }
);
