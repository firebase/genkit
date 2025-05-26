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

import { googleAI, vertexAI } from '@genkit-ai/google-genai';
//import { vertexAI as OrigVertex} from '@genkit-ai/vertexai'
import { genkit, z } from 'genkit';
//import { googleAI } from '@genkit-ai/googleai';

//const test = googleAI.model('gemini-2.5-pro-preview-tts');
// const test = googleAI.model('foo');
// console.log("DEBUGGG: model: " + JSON.stringify(test));
// console.dir(test);

const ai = genkit({
  plugins: [
    googleAI({ apiVersion: 'v1beta' }),
    vertexAI(),
    //OrigVertex()
  ],
});

const jokeSubjectGenerator = ai.defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'Can be called to generate a subject for a joke',
    inputSchema: z.void(),
    outputSchema: z.string(),
  },
  async () => {
    return 'banana';
  }
);

export const googleAIJokeFlow = ai.defineFlow(
  {
    name: 'googleAIJokeFlow',
    inputSchema: z.void(),
    outputSchema: z.any(),
  },
  async () => {
    const llmResponse = await ai.generate({
      model: 'googleai/gemini-2.0-flash',
      config: {
        temperature: 0.7,
        // if desired, model versions can be explicitly set
        //version: 'gemini-2.0-flash-001',
      },
      output: {
        schema: z.object({ jokeSubject: z.string() }),
      },
      tools: [jokeSubjectGenerator],
      prompt: `come up with a subject to joke about (using the function provided)`,
    });
    return await llmResponse.output;
  }
);

export const vertexAIJokeFlow = ai.defineFlow(
  {
    name: 'vertexAIJokeFlow',
    inputSchema: z.void(),
    outputSchema: z.any(),
  },
  async () => {
    const llmResponse = await ai.generate({
      model: 'vertexai/gemini-2.0-flash',
      config: {
        temperature: 0.7,
        // if desired, model versions can be explicitly set
        //version: 'gemini-2.0-flash-001',
      },
      output: {
        schema: z.object({ jokeSubject: z.string() }),
      },
      tools: [jokeSubjectGenerator],
      prompt: `come up with a subject to joke about (using the function provided)`,
    });
    return await llmResponse.output;
  }
);

export const googleAIJokeStreamFlow = ai.defineFlow(
  {
    name: 'googleAIJokeStreamFlow',
    inputSchema: z.void(),
    outputSchema: z.any(),
  },
  async () => {
    const llmResponse = await ai.generateStream({
      model: 'googleai/gemini-2.0-flash',
      config: {
        temperature: 0.7,
        // if desired, model versions can be explicitly set
        //version: 'gemini-2.0-flash-001',
      },
      output: {
        schema: z.object({ jokeSubject: z.string() }),
      },
      tools: [jokeSubjectGenerator],
      prompt: `come up with a subject to joke about (using the function provided)`,
    });
    return (await llmResponse.response).text;
  }
);

export const vertexAIjokeStreamFlow = ai.defineFlow(
  {
    name: 'vertexAIjokeStreamFlow',
    inputSchema: z.void(),
    outputSchema: z.any(),
  },
  async () => {
    const llmResponse = await ai.generateStream({
      model: 'vertexai/gemini-2.0-flash',
      config: {
        temperature: 0.7,
        // if desired, model versions can be explicitly set
        //version: 'gemini-2.0-flash-001',
      },
      output: {
        schema: z.object({ jokeSubject: z.string() }),
      },
      tools: [jokeSubjectGenerator],
      prompt: `come up with a subject to joke about (using the function provided)`,
    });
    return (await llmResponse.response).text;
  }
);
