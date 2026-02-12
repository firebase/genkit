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

describe('filesystem middleware image support', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await fs.mkdtemp(
      path.join(os.tmpdir(), 'genkit-filesystem-test-')
    );
    await fs.writeFile(path.join(tempDir, 'image.png'), 'fake image content');
    await fs.writeFile(path.join(tempDir, 'unknown.xyz'), 'unknown content');
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

  it('reads an image file as media', async () => {
    const ai = genkit({});
    const pm = createToolModel(ai, 'read_file', { filePath: 'image.png' });
    const result = (await ai.generate({
      model: pm,
      prompt: 'test',
      use: [filesystem({ rootDirectory: tempDir })],
    })) as any;

    const toolMsg = result.messages.find((m: any) => m.role === 'tool');
    assert.ok(toolMsg);
    assert.match(toolMsg.content[0].toolResponse.output, /read successfully/);

    const userMsg = result.messages.find(
      (m: any) => m.role === 'user' && m.content.some((c: any) => c.media)
    );
    assert.ok(userMsg);
    const mediaPart = userMsg.content.find((c: any) => c.media);
    assert.ok(mediaPart);
    assert.strictEqual(mediaPart.media.contentType, 'image/png');
    assert.ok(mediaPart.media.url.startsWith('data:image/png;base64,'));
  });

  it('reads unknown file as text', async () => {
    const ai = genkit({});
    const pm = createToolModel(ai, 'read_file', { filePath: 'unknown.xyz' });
    const result = (await ai.generate({
      model: pm,
      prompt: 'test',
      use: [filesystem({ rootDirectory: tempDir })],
    })) as any;

    const userMsg = result.messages.find(
      (m: any) =>
        m.role === 'user' &&
        m.content.some((c: any) => c.text && c.text.includes('<read_file'))
    );
    assert.ok(userMsg);
    assert.ok(userMsg.content[0].text.includes('unknown content'));
    // Should NOT have media
    assert.ok(!userMsg.content.some((c: any) => c.media));
  });
});
