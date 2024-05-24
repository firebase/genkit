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

import { defineDotprompt, prompt } from '@genkit-ai/dotprompt';
import { defineFlow } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/googleai';
import * as z from 'zod';
import { HelloFullNameSchema, HelloSchema } from '../common/types.js';

//
// Prompt defined in code, subsequently loaded into a flow, plus an additional variant.
//

const promptName = 'codeDefinedPrompt';
const template = 'Say hello to {{name}} in the voice of a {{persona}}.';

export const codeDefinedPrompt = defineDotprompt(
  {
    name: promptName,
    model: geminiPro,
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
      custom: {
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
  },
  template
);

export const codeDefinedPromptVariant = defineDotprompt(
  {
    name: promptName,
    variant: 'jsonOutput',
    model: geminiPro,
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

defineFlow(
  {
    name: 'flowCodeDefinedPrompt',
    inputSchema: HelloSchema,
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (input) => {
    const codeDefinedPrompt = await prompt('codeDefinedPrompt');
    const response = await codeDefinedPrompt.generate({
      input,
    });

    return response.text();
  }
);

//
// Dotprompt file - text output
//

prompt('hello').then((prompt) => {
  defineFlow(
    {
      name: 'flowDotPrompt',
      inputSchema: HelloSchema,
      outputSchema: z.string(),
    },
    async (input) => (await prompt.generate({ input })).text()
  );
});

//
// Dotprompt file - variant, text output
//

prompt('hello', { variant: 'first-last-name' }).then((prompt) => {
  defineFlow(
    {
      name: 'flowDotPromptVariant',
      inputSchema: HelloFullNameSchema,
      outputSchema: z.string(),
    },
    async (input) => (await prompt.generate({ input })).text()
  );
});

//
// Dotprompt file - json output
//

prompt('hello', { variant: 'json-output' }).then((prompt) => {
  defineFlow(
    {
      name: 'flowDotPromptJsonOutput',
      inputSchema: HelloSchema,
      outputSchema: z.any(),
    },
    async (input) => (await prompt.generate({ input })).output()
  );
});

prompt('hello', { variant: 'system' }).then((prompt) => {
  defineFlow(
    {
      name: 'flowDotPromptSystemMessage',
      inputSchema: HelloSchema,
      outputSchema: z.any(),
    },
    async (input) => (await prompt.generate({ input })).output()
  );
});

prompt('hello', { variant: 'history' }).then((prompt) => {
  defineFlow(
    {
      name: 'flowDotPromptHistory',
      inputSchema: HelloSchema,
      outputSchema: z.any(),
    },
    async (input) => (await prompt.generate({ input })).output()
  );
});

// TODO(michaeldoyle): showcase advanced capabilities of dotprompts
//   chat, multi-modal, tools, history, etc
