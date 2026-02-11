/**
 * Copyright 2026 Google LLC
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

import * as assert from 'assert';
import { genkit, z } from 'genkit';
import { describe, it } from 'node:test';
import { toolApproval } from '../src/tool_approval.js';

describe('toolApproval middleware', () => {
  const ai = genkit({});

  const testTool = ai.defineTool(
    {
      name: 'testTool',
      description: 'A test tool',
      inputSchema: z.object({ val: z.string() }),
      outputSchema: z.string(),
    },
    async ({ val }) => `Result: ${val}`
  );

  const mockModel = ai.defineModel({ name: 'mockModel' }, async (req) => {
    const lastMsg = req.messages[req.messages.length - 1];
    if (lastMsg?.role === 'tool') {
      return {
        message: {
          role: 'model',
          content: [{ text: 'done' }],
        },
      };
    }
    // simulate model generating a tool request
    return {
      message: {
        role: 'model',
        content: [
          {
            toolRequest: {
              name: 'testTool',
              input: { val: 'test' },
            },
          },
        ],
      },
    };
  });

  it('allows approved tools', async () => {
    const result = await ai.generate({
      model: mockModel,
      tools: [testTool],
      prompt: 'run tool',
      use: [toolApproval({ approved: ['testTool'] })],
    });

    const toolMsg = result.messages.find((m) => m.role === 'tool');
    assert.ok(toolMsg, 'Tool should have been executed');
    const output = toolMsg.content[0].toolResponse?.output;
    assert.match(output as string, /Result: test/);
  });

  it('interrupts unapproved tools', async () => {
    const result = await ai.generate({
      model: mockModel,
      tools: [testTool],
      prompt: 'run tool',
      use: [toolApproval({ approved: [] })],
    });

    assert.strictEqual(result.finishReason, 'interrupted');
    const interrupt = result.interrupts[0];
    assert.ok(interrupt, 'Should have interrupt metadata');
    assert.strictEqual(interrupt.toolRequest?.name, 'testTool');
  });

  it('allows unapproved tools if approval metadata is present', async () => {
    // First run to get interrupt
    const result1 = await ai.generate({
      model: mockModel,
      tools: [testTool],
      prompt: 'run tool',
      use: [toolApproval({ approved: [] })],
    });

    assert.strictEqual(result1.finishReason, 'interrupted');
    const interrupt = result1.interrupts[0];
    assert.ok(interrupt);

    if (!interrupt.metadata) interrupt.metadata = {};
    interrupt.metadata['tool-approved'] = true;

    // Resume with approval
    const result2 = await ai.generate({
      model: mockModel,
      tools: [testTool],
      messages: result1.messages,
      use: [toolApproval({ approved: [] })],
      resume: {
        restart: [interrupt],
      },
    });

    const toolMsg = result2.messages.find((m) => m.role === 'tool');
    assert.ok(toolMsg, 'Tool should have been executed after approval');
    const output = toolMsg.content[0].toolResponse?.output;
    assert.match(output as string, /Result: test/);
  });
});
