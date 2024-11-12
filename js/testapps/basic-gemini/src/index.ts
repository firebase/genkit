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

import { googleAI } from '@genkit-ai/googleai';
import { gemini15Flash, vertexAI } from '@genkit-ai/vertexai';
import { genkit, z } from 'genkit';

// Initialize Genkit with GoogleAI and VertexAI plugins
const ai = genkit({
  plugins: [googleAI(), vertexAI()],
});
console.log('Genkit initialized:', ai);

/**
 * @tool jokeSubjectGenerator
 * A tool to generate a subject for a joke based on input or return a default value.
 *
 * @param {string} subject - The initial subject or fallback.
 * @returns {string} The joke subject.
 *
 * @example
 * Input: "apple"
 * Output: "apple"
 */
const jokeSubjectGenerator = ai.defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'Generates a subject for a joke based on input',
  },
  async (subject: string = 'banana') => {
    return subject;
  }
);

/**
 * @flow jokeFlow
 * A flow to generate a joke subject using a Large Language Model.
 *
 * @flowDescription
 * This flow leverages the `jokeSubjectGenerator` tool to provide a subject
 * and constructs a joke using the `gemini15Flash` model from VertexAI.
 *
 * @returns {Promise<string>} Generated joke subject as a string.
 *
 * @example
 * Input: { jokeSubject: "apple" }
 * Output: "Generated joke about: apple"
 */
export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({
      jokeSubject: z.string().optional().default('banana'), // Accepts input from the UI
    }),
    outputSchema: z.string(), // Outputs a string
  },
  async (input) => {
    console.log('Flow execution started');

    // Use the provided joke subject or fallback to default
    const jokeSubject = await jokeSubjectGenerator(input.jokeSubject);
    console.log('Generated joke subject:', jokeSubject);

    // Generate response using the LLM model
    const llmResponse = await ai.generate({
      model: gemini15Flash,
      config: {
        temperature: 2, // Adjust model temperature to control creativity
      },
      tools: [jokeSubjectGenerator], // Tool used in the flow
      prompt: `Generate a joke about the following subject: ${jokeSubject}`,
    });

    console.log('LLM Response:', llmResponse.text); // Logs the response text from the model
    return llmResponse.text;
  }
);
