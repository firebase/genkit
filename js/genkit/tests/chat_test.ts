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
import {
  ProgrammableModel,
  defineEchoModel,
  defineProgrammableModel,
} from './helpers';

describe('chat', () => {
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

    assert.strictEqual(response.text, 'Echo: hi; config: {}');

    response = await session.send('bye');

    assert.strictEqual(
      response.text,
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
    const chat = ai.chat();
    let { response, stream } = await chat.sendStream('hi');

    let chunks: string[] = [];
    for await (const chunk of stream) {
      chunks.push(chunk.text);
    }
    assert.strictEqual((await response).text, 'Echo: hi; config: {}');
    assert.deepStrictEqual(chunks, ['3', '2', '1']);

    ({ response, stream } = await chat.sendStream('bye'));

    chunks = [];
    for await (const chunk of stream) {
      chunks.push(chunk.text);
    }

    assert.deepStrictEqual(chunks, ['3', '2', '1']);
    assert.strictEqual(
      (await response).text,
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
      response.text,
      'Echo: hi Genkit,hi; config: {"temperature":11}'
    );
  });

  it('can start chat from a prompt', async () => {
    const prompt = ai.definePrompt(
      { name: 'hi', config: { version: 'abc' } },
      'hi {{ name }} from template'
    );
    const session = await ai.chat({
      prompt,
      input: { name: 'Genkit' },
    });
    const response = await session.send('send it');

    assert.strictEqual(
      response.text,
      'Echo: hi Genkit from template,send it; config: {"version":"abc"}'
    );
  });

  it('can send a rendered prompt to chat', async () => {
    const prompt = ai.definePrompt(
      { name: 'hi', config: { version: 'abc' } },
      'hi {{ name }}'
    );
    const session = ai.chat();
    const response = await session.send(
      await prompt.render({
        input: { name: 'Genkit' },
        config: { temperature: 11 },
      })
    );

    assert.strictEqual(
      response.text,
      'Echo: hi Genkit; config: {"version":"abc","temperature":11}'
    );
  });
});

describe('preabmle', () => {
  let ai: Genkit;
  let pm: ProgrammableModel;

  beforeEach(() => {
    ai = genkit({
      model: 'programmableModel',
    });
    pm = defineProgrammableModel(ai);
  });

  it('swaps out preamble on prompt tool invocation', async () => {
    const agentB = ai.definePrompt(
      {
        name: 'agentB',
        config: { temperature: 1 },
        description: 'Agent B description',
        tools: ['agentA'],
      },
      '{{role "system"}} agent b'
    );

    const agentA = ai.definePrompt(
      {
        name: 'agentA',
        config: { temperature: 2 },
        description: 'Agent A description',
        tools: [agentB],
      },
      async () => {
        return {
          messages: [
            {
              role: 'system',
              content: [{ text: ' agent a' }],
            },
          ],
        };
      }
    );

    // simple hi, nothing interesting...
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [{ text: 'hi from agent a' }],
        },
      };
    };

    const session = ai.chat({
      prompt: agentA,
    });
    let { text } = await session.send('hi');
    assert.strictEqual(text, 'hi from agent a');
    assert.deepStrictEqual(pm.lastRequest, {
      config: {
        temperature: 2,
      },
      messages: [
        {
          content: [{ text: ' agent a' }],
          metadata: { preamble: true },
          role: 'system',
        },
        {
          content: [{ text: 'hi' }],
          role: 'user',
        },
      ],
      output: { format: 'text' },
      tools: [
        {
          name: 'agentB',
          description: 'Agent B description',
          inputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
    });

    // transfer to agent B...

    // first response be tools call, the subsequent just text response from agent b.
    let reqCounter = 0;
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [
            reqCounter++ === 0
              ? {
                  toolRequest: {
                    name: 'agentB',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : { text: 'hi from agent b' },
          ],
        },
      };
    };

    ({ text } = await session.send('pls transfer to b'));

    assert.deepStrictEqual(text, 'hi from agent b');
    assert.deepStrictEqual(pm.lastRequest, {
      config: {
        // TODO: figure out if config should be swapped out as well...
        temperature: 2,
      },
      messages: [
        {
          role: 'system',
          content: [{ text: ' agent b' }], // <--- NOTE: swapped out the preamble
          metadata: { preamble: true },
        },
        {
          role: 'user',
          content: [{ text: 'hi' }],
        },
        {
          role: 'model',
          content: [{ text: 'hi from agent a' }],
        },
        {
          role: 'user',
          content: [{ text: 'pls transfer to b' }],
        },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                input: {},
                name: 'agentB',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: 'agentB',
                output: 'transferred to agentB',
                ref: 'ref123',
              },
            },
          ],
        },
      ],
      output: { format: 'text' },
      tools: [
        {
          description: 'Agent A description',
          inputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          name: 'agentA',
          outputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
    });

    // transfer back to to agent A...

    // first response be tools call, the subsequent just text response from agent a.
    reqCounter = 0;
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [
            reqCounter++ === 0
              ? {
                  toolRequest: {
                    name: 'agentA',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : { text: 'hi from agent a' },
          ],
        },
      };
    };

    ({ text } = await session.send('pls transfer to a'));

    assert.deepStrictEqual(text, 'hi from agent a');
    assert.deepStrictEqual(pm.lastRequest, {
      config: {
        temperature: 2,
      },
      messages: [
        {
          role: 'system',
          content: [{ text: ' agent a' }], // <--- NOTE: swapped out the preamble
          metadata: { preamble: true },
        },
        {
          role: 'user',
          content: [{ text: 'hi' }],
        },
        {
          role: 'model',
          content: [{ text: 'hi from agent a' }],
        },
        {
          role: 'user',
          content: [{ text: 'pls transfer to b' }],
        },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                input: {},
                name: 'agentB',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: 'agentB',
                output: 'transferred to agentB',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'model',
          content: [{ text: 'hi from agent b' }],
        },
        {
          role: 'user',
          content: [{ text: 'pls transfer to a' }],
        },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                input: {},
                name: 'agentA',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: 'agentA',
                output: 'transferred to agentA',
                ref: 'ref123',
              },
            },
          ],
        },
      ],
      output: { format: 'text' },
      tools: [
        {
          description: 'Agent B description',
          inputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          name: 'agentB',
          outputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
    });
  });
});
