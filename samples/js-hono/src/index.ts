/**
 * Copyright 2025 Google LLC
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

import { googleAI } from '@genkit-ai/google-genai';
import { handleFlows, withFlowOptions } from '@genkit-ai/web';
import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import { genkit, UserFacingError, z } from 'genkit';
import type { ContextProvider } from 'genkit/context';

const ai = genkit({
  plugins: [googleAI()],
});

// Example: context provider for auth (require header: Authorization: Bearer open-sesame)
const authContextProvider: ContextProvider<{ userId: string }> = (req) => {
  const auth = req.headers['authorization'];
  if (auth !== 'Bearer open-sesame') {
    throw new UserFacingError(
      'PERMISSION_DENIED',
      'Invalid or missing Authorization header. Use: Bearer open-sesame'
    );
  }
  return { userId: 'authenticated-user' };
};

// Flows served over HTTP via @genkit-ai/web
const helloFlow = ai.defineFlow('hello', async (input: string) => {
  const { text } = await ai.generate({
    model: googleAI.model('gemini-2.0-flash'),
    prompt: `Say hello to: ${input}`,
  });
  return text;
});

const greetingFlow = ai.defineFlow(
  {
    name: 'greeting',
    inputSchema: z.object({ name: z.string() }),
  },
  async (input) => {
    const { text } = await ai.generate({
      model: googleAI.model('gemini-2.0-flash'),
      prompt: `Write a short greeting for someone named ${input.name}.`,
    });
    return text;
  }
);

const streamingFlow = ai.defineFlow(
  {
    name: 'streaming',
    inputSchema: z.object({ prompt: z.string() }),
  },
  async (input, { sendChunk }) => {
    const { stream } = ai.generateStream({
      model: googleAI.model('gemini-2.0-flash'),
      prompt: input.prompt,
    });
    let full = '';
    for await (const chunk of stream) {
      full += chunk.text ?? '';
      sendChunk(chunk.text ?? '');
    }
    return full;
  }
);

// Example: flow that uses context (auth), secured with withFlowOptions
const secureGreetingFlow = ai.defineFlow(
  {
    name: 'secureGreeting',
    inputSchema: z.object({ name: z.string() }),
  },
  async (input, { context }) => {
    const { text } = await ai.generate({
      model: googleAI.model('gemini-2.0-flash'),
      prompt: `Say a short greeting to ${input.name} (user ${context?.userId}).`,
    });
    return text?.trim() ?? '';
  }
);

const flows = [
  helloFlow,
  greetingFlow,
  streamingFlow,
  withFlowOptions(secureGreetingFlow, { contextProvider: authContextProvider }),
];

const app = new Hono();

app.get('/', (c) =>
  c.json({
    message: 'Genkit + Hono + @genkit-ai/web',
    flows: ['hello', 'greeting', 'streaming', 'secureGreeting'],
    usage: 'POST /api/<flowName> with body { "data": <input> }. secureGreeting requires header: Authorization: Bearer open-sesame',
  })
);

// Mount Genkit flows under /api - handleFlows routes by path
app.all('/api/*', async (c) => handleFlows(c.req.raw, flows, '/api'));

const port = Number(process.env.PORT) || 3780;
serve({ fetch: app.fetch, port }, (info) => {
  console.log(`Listening on http://localhost:${info.port}`);
  console.log(
    `Genkit flows: http://localhost:${info.port}/api/hello, /api/greeting, /api/streaming, /api/secureGreeting`
  );
});
