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
import { describe, it } from 'node:test';
import { GenerateResponseChunk } from '../../src/generate';
import { GenerateResponseChunkData } from '../../src/model';

describe('GenerateResponseChunk', () => {
  describe('#output()', () => {
    const testCases = [
      {
        should: 'parse ``` correctly',
        accumulatedChunksTexts: ['```'],
        correctJson: null,
      },
      {
        should: 'parse valid json correctly',
        accumulatedChunksTexts: [`{"foo":"bar"}`],
        correctJson: { foo: 'bar' },
      },
      {
        should: 'if json invalid, return null',
        accumulatedChunksTexts: [`invalid json`],
        correctJson: null,
      },
      {
        should: 'handle missing closing brace',
        accumulatedChunksTexts: [`{"foo":"bar"`],
        correctJson: { foo: 'bar' },
      },
      {
        should: 'handle missing closing bracket in nested object',
        accumulatedChunksTexts: [`{"foo": {"bar": "baz"`],
        correctJson: { foo: { bar: 'baz' } },
      },
      {
        should: 'handle multiple chunks',
        accumulatedChunksTexts: [`{"foo": {"bar"`, `: "baz`],
        correctJson: { foo: { bar: 'baz' } },
      },
      {
        should: 'handle multiple chunks with nested objects',
        accumulatedChunksTexts: [`\`\`\`json{"foo": {"bar"`, `: {"baz": "qux`],
        correctJson: { foo: { bar: { baz: 'qux' } } },
      },
      {
        should: 'handle array nested in object',
        accumulatedChunksTexts: [`{"foo": ["bar`],
        correctJson: { foo: ['bar'] },
      },
      {
        should: 'handle array nested in object with multiple chunks',
        accumulatedChunksTexts: [`\`\`\`json{"foo": {"bar"`, `: ["baz`],
        correctJson: { foo: { bar: ['baz'] } },
      },
    ];

    for (const test of testCases) {
      if (test.should) {
        it(test.should, () => {
          const accumulatedChunks: GenerateResponseChunkData[] =
            test.accumulatedChunksTexts.map((text, index) => ({
              index,
              content: [{ text }],
            }));

          const chunkData = accumulatedChunks[accumulatedChunks.length - 1];

          const responseChunk: GenerateResponseChunk =
            new GenerateResponseChunk(chunkData, accumulatedChunks);

          const output = responseChunk.output;

          assert.deepStrictEqual(output, test.correctJson);
        });
      }
    }
  });
});
