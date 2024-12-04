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

import { vertexAI } from '@genkit-ai/vertexai';
import {
  codestral,
  mistralLarge,
  mistralNemo,
  vertexAIModelGarden,
} from '@genkit-ai/vertexai/modelgarden';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [
    vertexAI({
      location: 'europe-west4',
    }),
    vertexAIModelGarden({
      location: 'europe-west4',
      models: [mistralLarge, mistralNemo, codestral],
    }),
  ],
});

// Mistral Nemo for quick validation and analysis
export const analyzeCode = ai.defineFlow(
  {
    name: 'analyzeCode',
    inputSchema: z.object({
      code: z.string(),
    }),
    outputSchema: z.string(),
  },
  async ({ code }) => {
    const analysis = await ai.generate({
      model: mistralNemo,
      prompt: `Analyze this code for potential issues and suggest improvements:
              ${code}`,
    });

    return analysis.text;
  }
);

// Codestral for code generation
export const generateFunction = ai.defineFlow(
  {
    name: 'generateFunction',
    inputSchema: z.object({
      description: z.string(),
    }),
    outputSchema: z.string(),
  },
  async ({ description }) => {
    const result = await ai.generate({
      model: codestral,
      prompt: `Create a TypeScript function that ${description}. Include error handling and types.`,
    });

    return result.text;
  }
);

// Mistral Large for detailed explanations
export const explainConcept = ai.defineFlow(
  {
    name: 'explainConcept',
    inputSchema: z.object({
      concept: z.string(),
    }),
    outputSchema: z.object({
      explanation: z.string(),
      examples: z.array(z.string()),
    }),
  },
  async ({ concept }) => {
    const explanation = await ai.generate({
      model: mistralLarge,
      prompt: `Explain ${concept} in programming. Include practical examples.`,
      config: {
        version: 'mistral-large-2407',
        temperature: 0.7,
      },
      output: {
        schema: z.object({
          explanation: z.string(),
          examples: z.array(z.string()),
        }),
      },
    });

    return explanation.output || { explanation: '', examples: [] };
  }
);
