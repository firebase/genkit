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
import { z } from '../src/index';
import { SessionData, SessionStore } from '../src/session';
import { defineEchoModel, TestMemorySessionStore } from './helpers';

describe('session', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
    });
    defineEchoModel(ai);
  });

  it('maintains history in the session', async () => {
    const session = ai.chat();
    let response = await session.send('hi');

    assert.strictEqual(response.text(), 'Echo: hi; config: {}');

    response = await session.send('bye');

    assert.strictEqual(
      response.text(),
      'Echo: hi,Echo: hi,; config: {},bye; config: {}'
    );
    assert.deepStrictEqual(response.toHistory(), [
      {
        content: [
          {
            text: 'hi',
          },
        ],
        role: 'user',
      },
      {
        content: [
          {
            text: 'Echo: hi',
          },
          {
            text: '; config: {}',
          },
        ],
        role: 'model',
      },
      {
        content: [
          {
            text: 'bye',
          },
        ],
        role: 'user',
      },
      {
        content: [
          {
            text: 'Echo: hi,Echo: hi,; config: {},bye',
          },
          {
            text: '; config: {}',
          },
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
    assert.deepStrictEqual((await response).toHistory(), [
      {
        content: [
          {
            text: 'hi',
          },
        ],
        role: 'user',
      },
      {
        content: [
          {
            text: 'Echo: hi',
          },
          {
            text: '; config: {}',
          },
        ],
        role: 'model',
      },
      {
        content: [
          {
            text: 'bye',
          },
        ],
        role: 'user',
      },
      {
        content: [
          {
            text: 'Echo: hi,Echo: hi,; config: {},bye',
          },
          {
            text: '; config: {}',
          },
        ],
        role: 'model',
      },
    ]);
  });

  it('stores state and messages in the store', async () => {
    const store = new TestMemorySessionStore();
    const session = ai.chat({ store });
    await session.send('hi');
    await session.send('bye');

    const state = await store.get(session.id);

    assert.deepStrictEqual(state?.messages, [
      {
        content: [
          {
            text: 'hi',
          },
        ],
        role: 'user',
      },
      {
        content: [
          {
            text: 'Echo: hi',
          },
          {
            text: '; config: {}',
          },
        ],
        role: 'model',
      },
      {
        content: [
          {
            text: 'bye',
          },
        ],
        role: 'user',
      },
      {
        content: [
          {
            text: 'Echo: hi,Echo: hi,; config: {},bye',
          },
          {
            text: '; config: {}',
          },
        ],
        role: 'model',
      },
    ]);
  });
});
