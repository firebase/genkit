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

import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { Genkit, genkit } from '../src/genkit';
import { defineEchoModel } from './helpers';

describe('formats', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = genkit({});
    defineEchoModel(ai);
  });

  it('lets you define and use a custom output format', async () => {
    ai.defineFormat(
      {
        name: 'banana',
        format: 'banana',
      },
      (schema) => {
        let instructions: string | undefined;

        if (schema) {
          instructions = `Output should be in banana format`;
        }

        return {
          parseChunk: (chunk) => {
            return `banana: ${chunk.content[0].text}`;
          },

          parseMessage: (message) => {
            return `banana: ${message.content[0].text}`;
          },

          instructions,
        };
      }
    );

    const { output } = await ai.generate({
      model: 'echoModel',
      prompt: 'hi',
      output: { format: 'banana' },
    });

    assert.strictEqual(output, 'banana: Echo: hi');

    const { response, stream } = await ai.generateStream({
      model: 'echoModel',
      prompt: 'hi',
      output: { format: 'banana' },
    });
    const chunks: string[] = [];
    for await (const chunk of stream) {
      chunks.push(`${chunk.output}`);
    }
    assert.deepStrictEqual(chunks, ['banana: 3', 'banana: 2', 'banana: 1']);
    assert.strictEqual((await response).output, 'banana: Echo: hi');
  });
});
