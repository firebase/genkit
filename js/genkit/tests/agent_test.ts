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

import { Session } from '@genkit-ai/ai/session';
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

  it('maintains chat history and session state for chat agents', async () => {
    const testAgent = ai.defineChatAgent({
      name: 'testAgent',
      description: 'does test things',
      instructions: 'do test things',
      tools: ['rootAgent'],
    });

    const rootAgent = ai.defineChatAgent({
      name: 'rootAgent',
      description: 'does root things',
      tools: [testAgent],
      instructions: 'do root things',
    });

    const session = ai.createSession();
    const chat = session.chat(rootAgent, { model: 'programmableModel' });

    let reqCounter = 0;
    pm.handleResponse = async (req, sc) => {
      reqCounter++;
      return {
        message: {
          role: 'model',
          content: [
            // transfer back to root agent on 2nd message
            reqCounter === 2
              ? {
                  toolRequest: {
                    name: 'testAgent',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : // transfer back to root agent on 5th
                reqCounter === 5
                ? {
                    toolRequest: {
                      name: 'rootAgent',
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

    assertSessionStateDeepEquals(session, {
      state: {
        __agentState: {
          main: {
            threadName: 'main',
            parentThreadName: 'main',
            agentName: 'rootAgent',
            agentInput: undefined,
          },
          main__rootAgent: {
            threadName: 'main',
            parentThreadName: 'main',
            agentName: 'rootAgent',
            agentInput: undefined,
          },
        },
      },
      threads: {
        main__rootAgent: [
          {
            role: 'system',
            content: [{ text: 'do root things' }],
            metadata: { preamble: true },
          },
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
        ],
      },
    });

    response = await chat.send('b');
    assert.strictEqual(response.text, 'transferred to testAgent');

    assertSessionStateDeepEquals(session, {
      state: {
        __agentState: {
          main: {
            agentName: 'testAgent',
            agentInput: {},
            parentThreadName: 'main',
          },
          main__testAgent: {
            agentName: 'testAgent',
            agentInput: {},
            parentThreadName: 'main',
          },
        },
      },
      threads: {
        main: [
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
          { role: 'user', content: [{ text: 'b' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'testAgent', input: {}, ref: 'ref123' } },
            ],
          },
        ],
        main__testAgent: [
          {
            role: 'system',
            content: [{ text: 'do test things' }],
            metadata: { preamble: true },
          },
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
          { role: 'user', content: [{ text: 'b' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'testAgent', input: {}, ref: 'ref123' } },
            ],
          },
          { role: 'user', content: [{ text: 'transferred to testAgent' }] },
          { role: 'model', content: [{ text: 'transferred to testAgent' }] },
        ],
      },
    });

    response = await chat.send('c');
    assert.strictEqual(response.text, 'c');
    response = await chat.send('d');
    assert.strictEqual(response.text, 'transferred to rootAgent');

    assertSessionStateDeepEquals(session, {
      state: {
        __agentState: {
          main: {
            agentName: 'rootAgent',
            agentInput: {},
            parentThreadName: 'main',
          },
          main__rootAgent: {
            agentName: 'rootAgent',
            agentInput: {},
            parentThreadName: 'main',
          },
        },
      },
      threads: {
        // Main thread.
        main: [
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
          { role: 'user', content: [{ text: 'b' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'testAgent', input: {}, ref: 'ref123' } },
            ],
          },
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
          { role: 'user', content: [{ text: 'b' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'testAgent', input: {}, ref: 'ref123' } },
            ],
          },
          { role: 'user', content: [{ text: 'transferred to testAgent' }] },
          { role: 'model', content: [{ text: 'transferred to testAgent' }] },
          { role: 'user', content: [{ text: 'c' }] },
          { role: 'model', content: [{ text: 'c' }] },
          { role: 'user', content: [{ text: 'd' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'rootAgent', input: {}, ref: 'ref123' } },
            ],
          },
        ],
        main__rootAgent: [
          {
            role: 'system',
            content: [{ text: 'do root things' }],
            metadata: { preamble: true },
          },
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
          { role: 'user', content: [{ text: 'b' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'testAgent', input: {}, ref: 'ref123' } },
            ],
          },
          { role: 'user', content: [{ text: 'a' }] },
          { role: 'model', content: [{ text: 'a' }] },
          { role: 'user', content: [{ text: 'b' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'testAgent', input: {}, ref: 'ref123' } },
            ],
          },
          { role: 'user', content: [{ text: 'transferred to testAgent' }] },
          { role: 'model', content: [{ text: 'transferred to testAgent' }] },
          { role: 'user', content: [{ text: 'c' }] },
          { role: 'model', content: [{ text: 'c' }] },
          { role: 'user', content: [{ text: 'd' }] },
          {
            role: 'model',
            content: [
              { toolRequest: { name: 'rootAgent', input: {}, ref: 'ref123' } },
            ],
          },
          { role: 'user', content: [{ text: 'transferred to rootAgent' }] },
          { role: 'model', content: [{ text: 'transferred to rootAgent' }] },
        ],
      },
    });
  });
});

function assertSessionStateDeepEquals(session: Session, want: any) {
  let sessionState = { ...session.toJSON() } as any;
  delete sessionState.id;

  console.log('assertSessionStateDeepEquals', JSON.stringify(sessionState));
  assert.deepStrictEqual(sessionState, want);
}
