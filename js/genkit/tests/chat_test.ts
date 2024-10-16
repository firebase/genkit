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

describe('session', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
    });
    defineEchoModel(ai);
  });

  it('maintains history in the session', async () => {
    const session = await ai.chat();
    let response = await session.send('hi');

    assert.strictEqual(response.text(), 'Echo: hi; config: {}');

    response = await session.send('bye');

    assert.strictEqual(
      response.text(),
      'Echo: hi,Echo: hi,; config: {},bye; config: {}'
    );
    assert.deepStrictEqual(response.messages, [
      { content: [{ text: 'hi' }], role: 'user' },
      {
        content: [{ text: 'Echo: hi' }, { text: '; config: {}' }],
        role: 'model',
      },
      { content: [{ text: 'bye' }], role: 'user' },
      {
        content: [
          { text: 'Echo: hi,Echo: hi,; config: {},bye' },
          { text: '; config: {}' },
        ],
        role: 'model',
      },
    ]);
  });

  it('maintains history in the session with streaming', async () => {
    const session = await ai.chat();
    let { response, stream } = await session.sendStream('hi');

    let chunks: string[] = [];
    for await (const chunk of stream) {
      chunks.push(chunk.text());
    }
    assert.strictEqual((await response).text(), 'Echo: hi; config: {}');
    assert.deepStrictEqual(chunks, ['3', '2', '1']);

    ({ response, stream } = await session.sendStream('bye'));

    chunks = [];
    for await (const chunk of stream) {
      chunks.push(chunk.text());
    }

    assert.deepStrictEqual(chunks, ['3', '2', '1']);
    assert.strictEqual(
      (await response).text(),
      'Echo: hi,Echo: hi,; config: {},bye; config: {}'
    );
    assert.deepStrictEqual((await response).messages, [
      { content: [{ text: 'hi' }], role: 'user' },
      {
        content: [{ text: 'Echo: hi' }, { text: '; config: {}' }],
        role: 'model',
      },
      { content: [{ text: 'bye' }], role: 'user' },
      {
        content: [
          { text: 'Echo: hi,Echo: hi,; config: {},bye' },
          { text: '; config: {}' },
        ],
        role: 'model',
      },
    ]);
  });

  it('can init a session with a prompt', async () => {
    const prompt = ai.definePrompt({ name: 'hi' }, 'hi {{ name }}');
    const session = await ai.chat(
      await prompt.render({
        input: { name: 'Genkit' },
        config: { temperature: 11 },
      })
    );
    const response = await session.send('hi');

    assert.strictEqual(
      response.text(),
      'Echo: hi Genkit,hi; config: {"temperature":11}'
    );
  });

  it('can send a prompt session to a session', async () => {
    const prompt = ai.definePrompt(
      { name: 'hi', config: { version: 'abc' } },
      'hi {{ name }}'
    );
    const session = await ai.chat();
    const response = await session.send(
      await prompt.render({
        input: { name: 'Genkit' },
        config: { temperature: 11 },
      })
    );

    assert.strictEqual(
      response.text(),
      'Echo: hi Genkit; config: {"version":"abc","temperature":11}'
    );
  });
});
