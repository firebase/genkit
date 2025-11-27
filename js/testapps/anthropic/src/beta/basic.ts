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

import { anthropic } from '@genkit-ai/anthropic';
import { genkit } from 'genkit';

const ai = genkit({
  plugins: [
    // Default all flows in this sample to the beta surface
    anthropic({ apiVersion: 'beta', cacheSystemPrompt: true }),
  ],
});

const betaHaiku = anthropic.model('claude-3-5-haiku', { apiVersion: 'beta' });
const betaSonnet = anthropic.model('claude-sonnet-4-5', { apiVersion: 'beta' });
const betaOpus41 = anthropic.model('claude-opus-4-1', { apiVersion: 'beta' });

ai.defineFlow('anthropic-beta-hello', async () => {
  const { text } = await ai.generate({
    model: betaHaiku,
    prompt:
      'You are Claude on the beta API. Provide a concise greeting that mentions that you are using the beta API.',
    config: { temperature: 0.6 },
  });

  return text;
});

ai.defineFlow('anthropic-beta-stream', async (_, { sendChunk }) => {
  const { stream } = ai.generateStream({
    model: betaSonnet,
    prompt: [
      {
        text: 'Outline two experimental capabilities unlocked by the Anthropic beta API.',
      },
    ],
    config: {
      apiVersion: 'beta',
      temperature: 0.4,
    },
  });

  const collected: string[] = [];
  for await (const chunk of stream) {
    if (chunk.text) {
      collected.push(chunk.text);
      sendChunk(chunk.text);
    }
  }

  return collected.join('');
});

ai.defineFlow('anthropic-beta-opus41', async () => {
  const { text } = await ai.generate({
    model: betaOpus41,
    prompt:
      'You are Claude Opus 4.1 on the beta API. Provide a brief greeting that confirms you are using the beta API.',
    config: { temperature: 0.6 },
  });

  return text;
});
