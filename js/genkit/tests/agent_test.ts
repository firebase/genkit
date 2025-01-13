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

describe.only('agents', () => {
  let ai: Genkit;
  let pm: ProgrammableModel;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
    });
    defineEchoModel(ai);
    pm = defineProgrammableModel(ai);
  });

  it('uses agent config for generate options', async () => {
    const testAgent = ai.defineChatAgent({
      name: 'testAgent',
      description: 'does test things',
      instructions: 'do test things',
      config: {
        temperature: 11,
      },
      toolChoice: 'required',
    });

    const chat = await ai.createSession().chat(testAgent);

    const response = await chat.send('hi');

    assert.strictEqual(
      response.text,
      'Echo: system: do test things,hi [toolChoice: required]; config: {"temperature":11}'
    );
  });

  it.only('initializes agent history using main thread history', async () => {
    const testAgent = ai.defineChatAgent({
      name: 'testAgent',
      description: 'does test things',
      instructions: 'do test things',
    });

    const rootAgent = ai.defineChatAgent({
      name: 'rootAgent',
      description: 'does root things',
      tools: [testAgent],
      instructions: 'do root things',
    });

    const session = ai.createSession();
    const chat = session.chat(rootAgent, { model: 'programmableModel' });

    // third response be tools call, the subsequent just echo the last message.
    let reqCounter = 0;
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [
            reqCounter++ === 2
              ? {
                  toolRequest: {
                    name: 'testAgent',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : req.messages.at(-1)!.content[0],
          ],
        },
      };
    };

    let response = await chat.send('a');
    assert.strictEqual(response.text, 'a');
    response = await chat.send('b');
    assert.strictEqual(response.text, 'b');
    response = await chat.send('c');
    assert.strictEqual(response.text, 'transferred to testAgent');
  });
});
