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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

async function fn01() {
  const { text } = await ai.generate({
    model: gemini15Flash,
    prompt: [{ text: 'Invent a menu item for a pirate themed restaurant.' }],
  });
}

async function fn02() {
  const { text } = await ai.generate({
    model: 'googleai/gemini-1.5-flash-latest',
    prompt: [{ text: 'Invent a menu item for a pirate themed restaurant.' }],
  });
}

async function fn03() {
  const { text } = await ai.generate({
    prompt: [{ text: 'Invent a menu item for a pirate themed restaurant.' }],
    config: {
      maxOutputTokens: 400,
      stopSequences: ['<end>', '<fin>'],
      temperature: 1.2,
      topP: 0.4,
      topK: 50,
    },
  });
}

import { z } from 'genkit'; // Import Zod, re-exported by Genkit

async function fn04() {
  const MenuItemSchema = z.object({
    name: z.string(),
    description: z.string(),
    calories: z.number(),
    allergens: z.array(z.string()),
  });

  const { output } = await ai.generate({
    prompt: [{ text: 'Invent a menu item for a pirate themed restaurant.' }],
    output: { schema: MenuItemSchema },
  });

  if (output) {
    const { name, description, calories, allergens } = output;
  }
}

function fn05() {
  const MenuItemSchema = z.object({
    name: z.string(),
    description: z.string(),
    calories: z.coerce.number(),
    allergens: z.array(z.string()),
  });
}

async function fn06() {
  const { response, stream } = await ai.generateStream(
    'Suggest a complete menu for a pirate themed restaurant.'
  );

  for await (const chunk of stream) {
    console.log(chunk.text);
  }

  const completeText = (await response).text;
}

async function fn07() {
  const MenuItemSchema = z.object({
    name: z.string(),
    description: z.string(),
    calories: z.coerce.number(),
    allergens: z.array(z.string()),
  });

  const MenuSchema = z.object({
    starters: z.array(MenuItemSchema),
    mains: z.array(MenuItemSchema),
    desserts: z.array(MenuItemSchema),
  });

  const { response, stream } = await ai.generateStream({
    prompt: 'Suggest a complete menu for a pirate themed restaurant.',
    output: { schema: MenuSchema },
  });

  for await (const chunk of stream) {
    // `output` is an object representing the entire output so far.
    console.log(chunk.output);
  }

  // Get the completed output.
  const { output } = await response;
}

async function fn08() {
  const { text } = await ai.generate({
    prompt: [
      { media: { url: 'https://example.com/photo.jpg' } },
      { text: 'Compose a poem about this image.' },
    ],
  });
}

import { readFile } from 'node:fs/promises';

async function fn09() {
  const b64Data = await readFile('photo.jpg', { encoding: 'base64url' });
  const dataUrl = `data:image/jpeg;base64,${b64Data}`;

  const { text } = await ai.generate({
    prompt: [
      { media: { url: dataUrl } },
      { text: 'Compose a poem about this image.' },
    ],
  });
}
