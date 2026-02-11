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
import * as fs from 'fs/promises';
import { genkit } from 'genkit';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as os from 'os';
import * as path from 'path';
import { skills } from '../src/skills.js';

describe('skills middleware', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'genkit-skills-test-'));
    // Create skill 1
    await fs.mkdir(path.join(tempDir, 'writer'));
    await fs.writeFile(
        path.join(tempDir, 'writer', 'SKILL.md'),
        `---
name: Writer
description: A creative writer skill.
---
You are a creative writer.`
    );
    // Create skill 2 (no description)
    await fs.mkdir(path.join(tempDir, 'coder'));
    await fs.writeFile(
        path.join(tempDir, 'coder', 'SKILL.md'),
        `---
name: Coder
---
You are a coder.`
    );
    // Create invalid skill (no SKILL.md)
    await fs.mkdir(path.join(tempDir, 'empty'));
  });

  afterEach(async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  function createToolModel(ai: any, toolName: string, input: any) {
    let turn = 0;
    return ai.defineModel(
      { name: `pm-${toolName}-${Math.random()}` },
      async () => {
        turn++;
        if (turn === 1) {
          return {
            message: {
              role: 'model',
              content: [{ toolRequest: { name: toolName, input } }],
            },
          };
        }
        return { message: { role: 'model', content: [{ text: 'done' }] } };
      }
    );
  }

  function createEchoModel(ai: any) {
    return ai.defineModel(
      { name: `pm-echo-${Math.random()}` },
      async (req: any) => {
        return {
          message: {
            role: 'model',
            content: [{ text: 'done' }],
          },
        };
      }
    );
  }

  it('injects system prompt with skills', async () => {
      const ai = genkit({});
      const pm = createEchoModel(ai);
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [skills({ skillsDirectory: tempDir })],
      })) as any;

      const systemMsg = result.messages.find((m: any) => m.role === 'system');
      assert.ok(systemMsg, 'System message should be injected');
      assert.ok(systemMsg.content[0].text.includes('<skills>'), 'Should contain <skills> tag');
      assert.ok(systemMsg.content[0].text.includes('Writer - A creative writer skill'), 'Should list Writer');
      assert.ok(systemMsg.content[0].text.includes('Coder'), 'Should list Coder');
      assert.ok(!systemMsg.content[0].text.includes('empty'), 'Should not list empty skill');
  });

  it('use_skill tool retrieves content', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'use_skill', { skillName: 'writer' });
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [skills({ skillsDirectory: tempDir })],
      })) as any;

      const toolMsg = result.messages.find((m: any) => m.role === 'tool');
      assert.ok(toolMsg, 'Tool execution should succeed');
      assert.match(toolMsg.content[0].toolResponse.output, /You are a creative writer/);
  });
});
