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

// [START imagen]
import { imagen3Fast, vertexAI } from '@genkit-ai/vertexai';
import parseDataURL from 'data-urls';
import { genkit } from 'genkit';

import { writeFile } from 'node:fs/promises';

const ai = genkit({
  plugins: [vertexAI({ location: 'us-central1' })],
});

(async () => {
  const { media } = await ai.generate({
    model: imagen3Fast,
    prompt: 'photo of a meal fit for a pirate',
    output: { format: 'media' },
  });

  if (media === null) throw new Error('No media generated.');

  const data = parseDataURL(media.url);
  if (data === null) throw new Error('Invalid "data:" URL.');

  await writeFile(`output.${data.mimeType.subtype}`, data.body);
})();
// [END imagen]
