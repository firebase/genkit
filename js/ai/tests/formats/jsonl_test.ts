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
import { jsonlParser } from '../../src/formats/jsonl.js';
import { GenerateResponse, GenerateResponseChunk } from '../../src/generate.js';
import { GenerateResponseChunkData } from '../../src/model.js';

describe('jsonlFormat', () => {
  const streamingTests = [
    {
      desc: 'emits complete JSON objects as they arrive',
      chunks: [
        {
          text: '{"id": 1, "name": "first"}\n',
          want: [{ id: 1, name: 'first' }],
        },
        {
          text: '{"id": 2, "name": "second"}\n{"id": 3',
          want: [{ id: 2, name: 'second' }],
        },
        {
          text: ', "name": "third"}\n',
          want: [{ id: 3, name: 'third' }],
        },
      ],
    },
    {
      desc: 'handles single object',
      chunks: [
        {
          text: '{"id": 1, "name": "single"}\n',
          want: [{ id: 1, name: 'single' }],
        },
      ],
    },
    {
      desc: 'handles preamble with code fence',
      chunks: [
        {
          text: 'Here are the objects:\n\n```\n',
          want: [],
        },
        {
          text: '{"id": 1, "name": "item"}\n```',
          want: [{ id: 1, name: 'item' }],
        },
      ],
    },
    {
      desc: 'ignores non-object lines',
      chunks: [
        {
          text: 'First object:\n{"id": 1}\nSecond object:\n{"id": 2}\n',
          want: [{ id: 1 }, { id: 2 }],
        },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = jsonlParser({ messages: [] });
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
      desc: 'parses complete JSONL response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '{"id": 1, "name": "test"}\n{"id": 2}\n' }],
        },
      }),
      want: [{ id: 1, name: 'test' }, { id: 2 }],
    },
    {
      desc: 'handles empty response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '' }],
        },
      }),
      want: [],
    },
    {
      desc: 'parses JSONL with preamble and code fence',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [
            {
              text: 'Here are the objects:\n\n```\n{"id": 1}\n{"id": 2}\n```',
            },
          ],
        },
      }),
      want: [{ id: 1 }, { id: 2 }],
    },
  ];

  for (const rt of responseTests) {
    it(rt.desc, () => {
      const parser = jsonlParser({ messages: [] });
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
      desc: 'throws error for array schema with non-object items',
      request: {
        messages: [],
        output: {
          schema: { type: 'array', items: { type: 'string' } },
        },
      },
      wantError: /Must supply an 'array' schema type containing 'object' items/,
    },
  ];

  for (const et of errorTests) {
    it(et.desc, () => {
      assert.throws(() => {
        jsonlParser(et.request);
      }, et.wantError);
    });
  }
});