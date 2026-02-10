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
      const mw = filesystem.instantiate(
        { rootDirectory: tempDir },
        fakeGenerateAPI
      );
      const listFiles = mw.tools!.find((t) => t.__action.name === 'list_files');
      const { result } = await listFiles!.run(
        { dirPath: '', recursive: false },
        {} as any
      );
      assert.ok(result.includes('file1.txt'));
      assert.ok(result.includes('sub'));
      assert.ok(!result.includes(path.join('sub', 'file2.txt')));
    });

    it('lists files recursively', async () => {
      const mw = filesystem.instantiate(
        { rootDirectory: tempDir },
        fakeGenerateAPI
      );
      const listFiles = mw.tools!.find((t) => t.__action.name === 'list_files');
      const { result } = await listFiles!.run(
        { dirPath: '', recursive: true },
        {} as any
      );
      assert.ok(result.includes('file1.txt'));
      assert.ok(result.includes('sub'));
      assert.ok(result.includes(path.join('sub', 'file2.txt')));
    });

    it('rejects listing outside root directory', async () => {
      const mw = filesystem.instantiate(
        { rootDirectory: tempDir },
        fakeGenerateAPI
      );
      const listFiles = mw.tools!.find((t) => t.__action.name === 'list_files');
      await assert.rejects(
        listFiles!.run({ dirPath: '../', recursive: false }, {} as any),
        /Access denied/
      );
    });
  });

  describe('read_file', () => {
    it('reads a file in root directory', async () => {
      const mw = filesystem.instantiate(
        { rootDirectory: tempDir },
        fakeGenerateAPI
      );
      const readFile = mw.tools!.find((t) => t.__action.name === 'read_file');
      const { result } = await readFile!.run(
        { filePath: 'file1.txt' },
        {} as any
      );
      assert.strictEqual(result, 'hello world');
    });

    it('reads a file in sub directory', async () => {
      const mw = filesystem.instantiate(
        { rootDirectory: tempDir },
        fakeGenerateAPI
      );
      const readFile = mw.tools!.find((t) => t.__action.name === 'read_file');
      const { result } = await readFile!.run(
        { filePath: 'sub/file2.txt' },
        {} as any
      );
      assert.strictEqual(result, 'sub file');
    });

    it('rejects reading outside root directory', async () => {
      const mw = filesystem.instantiate(
        { rootDirectory: tempDir },
        fakeGenerateAPI
      );
      const readFile = mw.tools!.find((t) => t.__action.name === 'read_file');
      await assert.rejects(
        readFile!.run({ filePath: '../etc/passwd' }, {} as any),
        /Access denied/
      );
    });
  });
});
