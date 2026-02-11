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
import { filesystem } from '../src/filesystem.js';

describe('filesystem middleware', () => {
  let tempDir: string;
  let fakeGenerateAPI: any = {};

  beforeEach(async () => {
    tempDir = await fs.mkdtemp(
      path.join(os.tmpdir(), 'genkit-filesystem-test-')
    );
    await fs.mkdir(path.join(tempDir, 'sub'));
    await fs.writeFile(path.join(tempDir, 'file1.txt'), 'hello world');
    await fs.writeFile(path.join(tempDir, 'sub', 'file2.txt'), 'sub file');
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

  it('fails if rootDirectory is not provided', () => {
    assert.throws(
      () => filesystem.instantiate({} as any, fakeGenerateAPI),
      /requires a rootDirectory option/
    );
  });

  it('injects tools', () => {
    const mw = filesystem.instantiate(
      { rootDirectory: tempDir },
      fakeGenerateAPI
    );
    assert.ok(mw.tools);
    assert.strictEqual(mw.tools.length, 2);
    assert.strictEqual(mw.tools[0].__action.name, 'list_files');
    assert.strictEqual(mw.tools[1].__action.name, 'read_file');
  });

  describe('list_files', () => {
    it('lists files in root directory', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'list_files', { dirPath: '' });
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const toolMsg = result.messages.find((m: any) => m.role === 'tool');
      assert.ok(toolMsg);
      const output = toolMsg.content[0].toolResponse.output;
      assert.ok(
        output.find((r: any) => r.path === 'file1.txt' && !r.isDirectory)
      );
      assert.ok(output.find((r: any) => r.path === 'sub' && r.isDirectory));
      assert.ok(
        !output.find((r: any) => r.path === path.join('sub', 'file2.txt'))
      );
    });

    it('lists files recursively', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'list_files', {
        dirPath: '',
        recursive: true,
      });
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const toolMsg = result.messages.find((m: any) => m.role === 'tool');
      assert.ok(toolMsg);
      const output = toolMsg.content[0].toolResponse.output;
      assert.ok(
        output.find((r: any) => r.path === 'file1.txt' && !r.isDirectory)
      );
      assert.ok(output.find((r: any) => r.path === 'sub' && r.isDirectory));
      assert.ok(
        output.find(
          (r: any) => r.path === path.join('sub', 'file2.txt') && !r.isDirectory
        )
      );
    });

    it('rejects listing outside root directory', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'list_files', { dirPath: '../' });

      // The middleware catches errors and injects user message.
      // So verify that user message contains access denied error.
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const userMsg = result.messages.find(
        (m: any) =>
          m.role === 'user' && m.content[0].text.includes('Access denied')
      );
      assert.ok(userMsg);
    });
  });

  describe('read_file', () => {
    it('reads a file in root directory', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'read_file', { filePath: 'file1.txt' });
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const toolMsg = result.messages.find((m: any) => m.role === 'tool');
      assert.ok(toolMsg);
      assert.match(toolMsg.content[0].toolResponse.output, /read successfully/);

      const userMsg = result.messages.find(
        (m: any) =>
          m.role === 'user' && m.content[0].text.includes('<read_file')
      );
      assert.ok(userMsg);
      assert.ok(userMsg.content[0].text.includes('hello world'));
    });

    it('reads a file in sub directory', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'read_file', {
        filePath: 'sub/file2.txt',
      });
      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const toolMsg = result.messages.find((m: any) => m.role === 'tool');
      assert.ok(toolMsg);
      assert.match(toolMsg.content[0].toolResponse.output, /read successfully/);

      const userMsg = result.messages.find(
        (m: any) =>
          m.role === 'user' && m.content[0].text.includes('<read_file')
      );
      assert.ok(userMsg);
      assert.ok(userMsg.content[0].text.includes('sub file'));
    });

    it('rejects reading outside root directory', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'read_file', {
        filePath: '../etc/passwd',
      });

      const result = (await ai.generate({
        model: pm,
        prompt: 'test',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const userMsg = result.messages.find(
        (m: any) =>
          m.role === 'user' && m.content[0].text.includes('Access denied')
      );
      assert.ok(userMsg);
    });
  });

  describe('robustness', () => {
    it('should handle tool errors gracefully by injecting user message', async () => {
      const ai = genkit({});
      const pm = createToolModel(ai, 'read_file', { filePath: 'nonexistent' });

      const result = (await ai.generate({
        model: pm,
        prompt: 'start',
        use: [filesystem({ rootDirectory: tempDir })],
      })) as any;

      const messages = result.messages;
      const lastModelIndex = messages.findLastIndex(
        (m: any) => m.role === 'model' && m.content[0].toolRequest
      );
      const injectedUserIndex = messages.findIndex(
        (m: any) =>
          m.role === 'user' &&
          m.content[0].text.includes("Tool 'read_file' failed")
      );

      assert.ok(
        injectedUserIndex > lastModelIndex,
        'User message should appear after tool request'
      );

      const userMsg = messages[injectedUserIndex];
      assert.match(
        userMsg.content[0].text,
        /Tool 'read_file' failed: .*ENOENT.*/,
        'Error message should contain underlying error details'
      );

      const roles = messages.map((m: any) => m.role);
      assert.deepStrictEqual(roles, ['user', 'model', 'user', 'model']);

      const toolMsg = messages.find((m: any) => m.role === 'tool');
      assert.strictEqual(
        toolMsg,
        undefined,
        'Tool message should not be present'
      );
    });
  });
});
