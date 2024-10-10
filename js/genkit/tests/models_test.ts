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

describe('models', () => {
  describe('generate', () => {
    describe('default model', () => {
      let ai: Genkit;

      beforeEach(() => {
        ai = genkit({
          model: 'echoModel',
        });
        defineEchoModel(ai);
      });

      it('calls the default model', async () => {
        const response = await ai.generate({
          prompt: 'hi',
        });
        assert.strictEqual(response.text, 'Echo: hi; config: {}');
      });

      it('calls the default model with just a string prompt', async () => {
        const response = await ai.generate('hi');
        assert.strictEqual(response.text, 'Echo: hi; config: {}');
      });

      it('calls the default model with just parts prompt', async () => {
        const response = await ai.generate([{ text: 'hi' }]);
        assert.strictEqual(response.text, 'Echo: hi; config: {}');
      });

      it('calls the default model system', async () => {
        const response = await ai.generate({
          prompt: 'hi',
          system: 'talk like a pirate',
        });
        assert.strictEqual(
          response.text,
          'Echo: system: talk like a pirate,hi; config: {}'
        );
        assert.deepStrictEqual(response.request, {
          config: undefined,
          context: undefined,
          messages: [
            {
              role: 'system',
              content: [{ text: 'talk like a pirate' }],
            },
            {
              role: 'user',
              content: [{ text: 'hi' }],
            },
          ],
          output: {
            format: 'text',
          },
          tools: [],
        });
      });

      it('streams the default model', async () => {
        const { response, stream } = await ai.generateStream({
          prompt: 'hi',
        });

        const chunks: string[] = [];
        for await (const chunk of stream) {
          chunks.push(chunk.text);
        }
        assert.strictEqual((await response).text, 'Echo: hi; config: {}');
        assert.deepStrictEqual(chunks, ['3', '2', '1']);
      });
    });

    describe('default model', () => {
      let ai: Genkit;

      beforeEach(() => {
        ai = genkit({});
        defineEchoModel(ai);
      });

      it('calls the explicitly passed in model', async () => {
        const response = await ai.generate({
          model: 'echoModel',
          prompt: 'hi',
        });
        assert.strictEqual(response.text, 'Echo: hi; config: {}');
      });
    });
  });
});
