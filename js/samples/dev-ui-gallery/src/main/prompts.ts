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

import { definePrompt, prompt } from '@genkit-ai/dotprompt';
import { defineFlow } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/googleai';
import * as z from 'zod';
import { HelloSchema } from '../common/types.js';
import '../genkit.config.js';

//
// Prompt defined in code, subsequently loaded into a flow, plus an additional variant.
//

const promptName = 'codeDefinedPrompt';
const template = 'Say hello to {{name}} in the voice of a {{persona}}.';

export const codeDefinedPrompt = definePrompt(
  {
    name: promptName,
    model: geminiPro,
    input: {
      schema: HelloSchema,
    },
    output: {
      format: 'text',
    },
  },
  template
);

export const codeDefinedPromptVariant = definePrompt(
  {
    name: promptName,
    variant: 'jsonOutput',
    model: geminiPro,
    input: {
      schema: HelloSchema,
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
    name: 'codeDefinedPromptFlow',
    inputSchema: HelloSchema,
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (input, streamingCallback) => {
    const codeDefinedPrompt = await prompt('codeDefinedPrompt');
    const response = await codeDefinedPrompt.generate({
      input: input,
    });

    return response.text();
  }
);

//
// Dotprompt file - text output
//

prompt('dotprompt-hello').then((prompt) => {
  defineFlow(
    {
      name: 'dotPromptFlow',
      inputSchema: HelloSchema,
      outputSchema: z.string(),
    },
    async (input) => (await prompt.generate({ input: input })).text()
  );
});

//
// Dotprompt file - variant, text output
//

prompt('dotprompt-hello', { variant: 'variant' }).then((prompt) => {
  defineFlow(
    {
      name: 'dotPromptVariantFlow',
      inputSchema: HelloSchema,
      outputSchema: z.string(),
    },
    async (input) => (await prompt.generate({ input: input })).text()
  );
});

//
// Dotprompt file - json output
//

prompt('dotprompt-hello', { variant: 'json-output' }).then((prompt) => {
  defineFlow(
    {
      name: 'dotPromptJsonOutputFlow',
      inputSchema: HelloSchema,
      outputSchema: z.any(),
    },
    async (input) => (await prompt.generate({ input: input })).output()
  );
});

// TODO(michaeldoyle): showcase advanced capabilities of dotprompts
//   chat, multi-modal, tools, history, etc
