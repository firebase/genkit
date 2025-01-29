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

import { Registry } from '@genkit-ai/core/registry';
import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import {
  GenerateAction,
  defineGenerateAction,
} from '../../src/generate/action.js';
import { GenerateResponseChunkData } from '../../src/model.js';
import { defineTool } from '../../src/tool.js';
import {
  ProgrammableModel,
  defineEchoModel,
  defineProgrammableModel,
} from '../helpers.js';

describe('generate', () => {
  let registry: Registry;
  let pm: ProgrammableModel;

  beforeEach(() => {
    registry = new Registry();
    defineGenerateAction(registry);
    defineEchoModel(registry);
    pm = defineProgrammableModel(registry);
  });

  it('registers the action', async () => {
    const action = await registry.lookupAction('/util/generate');
    assert.ok(action);
  });

  it('generate simple response', async () => {
    const action = (await registry.lookupAction(
      '/util/generate'
    )) as GenerateAction;

    const response = await action({
      model: 'echoModel',
      messages: [{ role: 'user', content: [{ text: 'hi' }] }],
      config: { temperature: 11 },
    });

    assert.deepStrictEqual(response, {
      custom: {},
      finishReason: 'stop',
      message: {
        role: 'model',
        content: [
          { text: 'Echo: hi' },
          { text: '; config: {"temperature":11}' },
        ],
      },
      request: {
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
        ],
        output: {},
        tools: [],
        config: {
          temperature: 11,
        },
        docs: undefined,
      },
      usage: {},
    });
  });

  it('should call tools', async () => {
    const action = (await registry.lookupAction(
      '/util/generate'
    )) as GenerateAction;

    defineTool(
      registry,
      { name: 'testTool', description: 'description' },
      async () => 'tool called'
    );

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
                    name: 'testTool',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : {
                  text: req.messages
                    .map((m) =>
                      m.content
                        .map(
                          (c) =>
                            c.text || JSON.stringify(c.toolResponse?.output)
                        )
                        .join()
                    )
                    .join(),
                },
          ],
        },
      };
    };

    const response = await action({
      model: 'programmableModel',
      messages: [{ role: 'user', content: [{ text: 'hi' }] }],
      tools: ['testTool'],
      config: { temperature: 11 },
    });

    assert.deepStrictEqual(response, {
      custom: {},
      finishReason: undefined,
      message: {
        role: 'model',
        content: [{ text: 'hi,,"tool called"' }],
      },
      request: {
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
          {
            content: [
              {
                toolRequest: {
                  input: {},
                  name: 'testTool',
                  ref: 'ref123',
                },
              },
            ],
            role: 'model',
          },
          {
            content: [
              {
                toolResponse: {
                  name: 'testTool',
                  output: 'tool called',
                  ref: 'ref123',
                },
              },
            ],
            role: 'tool',
          },
        ],
        output: {},
        tools: [
          {
            description: 'description',
            inputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            name: 'testTool',
            outputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        config: {
          temperature: 11,
        },
        docs: undefined,
      },
      usage: {},
    });
  });

  it('streams simple response', async () => {
    const action = (await registry.lookupAction(
      '/util/generate'
    )) as GenerateAction;

    const { output, stream } = action.stream({
      model: 'echoModel',
      messages: [{ role: 'user', content: [{ text: 'hi' }] }],
    });

    const chunks = [] as GenerateResponseChunkData[];
    for await (const chunk of stream) {
      chunks.push(chunk);
    }

    assert.deepStrictEqual(chunks, [
      {
        index: 0,
        role: 'model',
        content: [{ text: '3' }],
      },
      {
        index: 0,
        role: 'model',
        content: [{ text: '2' }],
      },
      {
        index: 0,
        role: 'model',
        content: [{ text: '1' }],
      },
    ]);

    assert.deepStrictEqual(await output, {
      custom: {},
      finishReason: 'stop',
      message: {
        role: 'model',
        content: [{ text: 'Echo: hi' }, { text: '; config: undefined' }],
      },
      request: {
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
        ],
        output: {},
        tools: [],
        config: undefined,
        docs: undefined,
      },
      usage: {},
    });
  });
});
