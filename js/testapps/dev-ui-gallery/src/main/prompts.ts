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

import { gemini15Flash } from '@genkit-ai/googleai';
import { promptRef, z } from 'genkit';
import { HelloFullNameSchema, HelloSchema } from '../common/types.js';
import { ai } from '../genkit.js';

//
// Prompt defined in code, subsequently loaded into a flow, plus an additional variant.
//

const promptName = 'codeDefinedPrompt';
const template = 'Say hello to {{name}} in the voice of a {{persona}}.';

export const codeDefinedPrompt = ai.definePrompt(
  {
    name: promptName,
    model: gemini15Flash,
    input: {
      schema: HelloSchema,
      default: {
        persona: 'Space Pirate',
      },
    },
    output: {
      format: 'text',
    },
    config: {
      maxOutputTokens: 2048,
      temperature: 0.6,
      topK: 16,
      topP: 0.95,
      stopSequences: ['STAWP!'],
      safetySettings: [
        {
          category: 'HARM_CATEGORY_HATE_SPEECH',
          threshold: 'BLOCK_ONLY_HIGH',
        },
        {
          category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
          threshold: 'BLOCK_ONLY_HIGH',
        },
        {
          category: 'HARM_CATEGORY_HARASSMENT',
          threshold: 'BLOCK_ONLY_HIGH',
        },
        {
          category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
          threshold: 'BLOCK_ONLY_HIGH',
        },
      ],
    },
  },
  template
);

export const codeDefinedPromptVariant = ai.definePrompt(
  {
    name: promptName,
    variant: 'jsonOutput',
    model: gemini15Flash,
    input: {
      schema: HelloSchema,
      default: {
        persona: 'Sportscaster',
      },
    },
    output: {
      schema: z.object({
        greeting: z.string(),
      }),
      format: 'json',
    },
  },
  template
);

ai.defineStreamingFlow(
  {
    name: 'flowCodeDefinedPrompt',
    inputSchema: HelloSchema,
    outputSchema: z.string(),
  },
  async (input) => {
    const prompt = promptRef('codeDefinedPrompt');
    const response = await prompt.generate({
      input,
    });

    return response.text();
  }
);

//
// Dotprompt file - text output
//

ai.defineFlow(
  {
    name: 'flowDotPrompt',
    inputSchema: HelloSchema,
    outputSchema: z.string(),
  },
  async (input) => {
    const prompt = promptRef('hello');
    return (await prompt.generate({ input })).text();
  }
);

//
// Dotprompt file - variant, text output
//

ai.defineFlow(
  {
    name: 'flowDotPromptVariant',
    inputSchema: HelloFullNameSchema,
    outputSchema: z.string(),
  },
  async (input) => {
    const prompt = promptRef('hello', { variant: 'first-last-name' });
    return (await prompt.generate({ input })).text();
  }
);

//
// Dotprompt file - json output
//

ai.defineFlow(
  {
    name: 'flowDotPromptJsonOutput',
    inputSchema: HelloSchema,
    outputSchema: z.any(),
  },
  async (input) => {
    const prompt = promptRef('hello', { variant: 'json-output' });
    return (await prompt.generate({ input })).output();
  }
);

//
// Dotprompt file - system message
//

ai.defineFlow(
  {
    name: 'flowDotPromptSystemMessage',
    inputSchema: HelloSchema,
    outputSchema: z.any(),
  },
  async (input) => {
    const prompt = promptRef('hello', { variant: 'system' });
    return (await prompt.generate({ input })).text();
  }
);

//
// Dotprompt file - history
//

ai.defineFlow(
  {
    name: 'flowDotPromptHistory',
    inputSchema: HelloSchema,
    outputSchema: z.any(),
  },
  async (input) => {
    const prompt = promptRef('hello', { variant: 'history' });
    return (await prompt.generate({ input })).text();
  }
);

// TODO(michaeldoyle): showcase advanced capabilities of dotprompts
//   chat, multi-modal, tools, history, etc
