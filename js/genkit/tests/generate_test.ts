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
import { modelRef } from '../../ai/src/model';
import { Genkit, genkit } from '../src/genkit';
import { defineEchoModel, runAsync } from './helpers';

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
        config: {
          version: undefined,
        },
        docs: undefined,
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
        output: {},
        tools: [],
      });
    });

    it('streams the default model', async () => {
      const { response, stream } = await ai.generateStream('hi');

      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      assert.strictEqual((await response).text, 'Echo: hi; config: {}');
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });
  });

  describe('explicit model', () => {
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

    it('rejects on invalid model', async () => {
      const response = ai.generate({
        model: 'modelThatDoesNotExist',
        prompt: 'hi',
      });
      await assert.rejects(response, 'Model modelThatDoesNotExist not found');
    });
  });

  describe('streaming', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
    });

    it('rethrows errors', async () => {
      ai.defineModel(
        {
          name: 'blockingModel',
        },
        async (request, streamingCallback) => {
          if (streamingCallback) {
            await runAsync(() => {
              streamingCallback({
                content: [
                  {
                    text: '3',
                  },
                ],
              });
            });
            await runAsync(() => {
              streamingCallback({
                content: [
                  {
                    text: '2',
                  },
                ],
              });
            });
            await runAsync(() => {
              streamingCallback({
                content: [
                  {
                    text: '1',
                  },
                ],
              });
            });
          }
          return await runAsync(() => ({
            message: {
              role: 'model',
              content: [],
            },
            finishReason: 'blocked',
          }));
        }
      );

      assert.rejects(async () => {
        const { response, stream } = await ai.generateStream({
          prompt: 'hi',
          model: 'blockingModel',
        });
        for await (const chunk of stream) {
          // nothing
        }
        await response;
      });
    });
  });

  describe('config', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('takes config passed to generate', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        model: 'echoModel',
        config: {
          temperature: 11,
        },
      });
      assert.strictEqual(response.text, 'Echo: hi; config: {"temperature":11}');
    });

    it('merges config from the ref', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        model: modelRef({ name: 'echoModel' }).withConfig({
          version: 'abc',
        }),
        config: {
          temperature: 11,
        },
      });
      assert.strictEqual(
        response.text,
        'Echo: hi; config: {"version":"abc","temperature":11}'
      );
    });

    it('picks up the top-level version from the ref', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        model: modelRef({ name: 'echoModel' }).withVersion('bcd'),
        config: {
          temperature: 11,
        },
      });
      assert.strictEqual(
        response.text,
        'Echo: hi; config: {"version":"bcd","temperature":11}'
      );
    });
  });
});
