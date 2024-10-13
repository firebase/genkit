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
import { TestMemorySessionStore, defineEchoModel } from './helpers';

describe('environment', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
    });
    defineEchoModel(ai);
  });

  it('maintains history in the session', async () => {
    const env = await ai.defineEnvironment({
      name: 'agent',
      stateSchema: z.object({
        name: z.string(),
      }),
    });

    const session = await env.createSession({
      state: {
        name: 'banana',
      },
    });
    const chat = session.chat();
    let response = await chat.send('hi');

    assert.strictEqual(response.text(), 'Echo: hi; config: {}');

    response = await chat.send('bye');

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
    const env = await ai.defineEnvironment({
      name: 'agent',
      stateSchema: z.object({
        name: z.string(),
      }),
    });
    const session = await env.createSession();
    const chat = session.chat();

    let { response, stream } = await chat.sendStream('hi');

    let chunks: string[] = [];
    for await (const chunk of stream) {
      chunks.push(chunk.text());
    }
    assert.strictEqual((await response).text(), 'Echo: hi; config: {}');
    assert.deepStrictEqual(chunks, ['3', '2', '1']);

    ({ response, stream } = await chat.sendStream('bye'));

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
        role: 'model',
        content: [{ text: 'Echo: hi' }, { text: '; config: {}' }],
      },
      { content: [{ text: 'bye' }], role: 'user' },
      {
        role: 'model',
        content: [
          { text: 'Echo: hi,Echo: hi,; config: {},bye' },
          { text: '; config: {}' },
        ],
      },
    ]);
  });

  it('stores state and messages in the store', async () => {
    const store = new TestMemorySessionStore();
    const env = ai.defineEnvironment({
      name: 'agent',
      store,
      stateSchema: z.object({
        name: z.string(),
      }),
    });
    const session = await env.createSession({
      state: {
        name: 'Genkit',
      },
    });
    const initialState = await store.get(session.id);

    assert.deepStrictEqual(initialState, {
      state: {
        name: 'Genkit',
      },
      threads: {
        __main: [],
      },
    });

    const chat = session.chat();

    await chat.send('hi');
    await chat.send('bye');

    const state = await store.get(session.id);

    assert.deepStrictEqual(state?.threads, {
      __main: [
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
      ],
    });
  });
});
