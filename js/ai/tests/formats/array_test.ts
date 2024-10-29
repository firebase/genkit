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
import { arrayFormatter } from '../../src/formats/array.js';
import { GenerateResponse } from '../../src/generate.js';
import { GenerateResponseChunk } from '../../src/generate/chunk.js';
import { GenerateResponseChunkData } from '../../src/model.js';

describe('arrayFormat', () => {
  const streamingTests = [
    {
      desc: 'emits complete array items as they arrive',
      chunks: [
        {
          text: '[{"id": 1,',
          want: [],
        },
        {
          text: '"name": "first"}',
          want: [{ id: 1, name: 'first' }],
        },
        {
          text: ', {"id": 2, "name": "second"}]',
          want: [{ id: 2, name: 'second' }],
        },
      ],
    },
    {
      desc: 'handles single item arrays',
      chunks: [
        {
          text: '[{"id": 1, "name": "single"}]',
          want: [{ id: 1, name: 'single' }],
        },
      ],
    },
    {
      desc: 'handles preamble with code fence',
      chunks: [
        {
          text: 'Here is the array you requested:\n\n```json\n[',
          want: [],
        },
        {
          text: '{"id": 1, "name": "item"}]\n```',
          want: [{ id: 1, name: 'item' }],
        },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = arrayFormatter.handler({ messages: [] });
      const chunks: GenerateResponseChunkData[] = [];
      let lastCursor = 0;

      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          content: [{ text: chunk.text }],
        };
        chunks.push(newChunk);

        const result = parser.parseChunk!(
          new GenerateResponseChunk(newChunk, chunks),
          lastCursor
        );

        assert.deepStrictEqual(result.output, chunk.want);
        lastCursor = result.cursor!;
      }
    });
  }

  const responseTests = [
    {
      desc: 'parses complete array response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '[{"id": 1, "name": "test"}]' }],
        },
      }),
      want: [{ id: 1, name: 'test' }],
    },
    {
      desc: 'parses empty array',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '[]' }],
        },
      }),
      want: [],
    },
    {
      desc: 'parses array with preamble and code fence',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [
            { text: 'Here is the array:\n\n```json\n[{"id": 1}]\n```' },
          ],
        },
      }),
      want: [{ id: 1 }],
    },
  ];

  for (const rt of responseTests) {
    it(rt.desc, () => {
      const parser = arrayFormatter.handler({ messages: [] });
      assert.deepStrictEqual(parser.parseResponse(rt.response), rt.want);
    });
  }

  const errorTests = [
    {
      desc: 'throws error for non-array schema type',
      request: {
        messages: [],
        output: {
          schema: { type: 'string' },
        },
      },
      wantError: /Must supply an 'array' schema type/,
    },
    {
      desc: 'throws error for object schema type',
      request: {
        messages: [],
        output: {
          schema: { type: 'object' },
        },
      },
      wantError: /Must supply an 'array' schema type/,
    },
  ];

  for (const et of errorTests) {
    it(et.desc, () => {
      assert.throws(() => {
        arrayFormatter.handler(et.request);
      }, et.wantError);
    });
  }
});
