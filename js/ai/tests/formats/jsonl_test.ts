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

import * as assert from 'assert';
import { describe, it } from 'node:test';
import { jsonlFormatter } from '../../src/formats/jsonl.js';
import { GenerateResponseChunk } from '../../src/generate.js';
import { Message } from '../../src/message.js';
import type {
  GenerateResponseChunkData,
  MessageData,
} from '../../src/model.js';

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
      const parser = jsonlFormatter.handler();
      const chunks: GenerateResponseChunkData[] = [];

      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          index: 0,
          role: 'model',
          content: [{ text: chunk.text }],
        };

        const result = parser.parseChunk!(
          new GenerateResponseChunk(newChunk, {
            index: 0,
            role: 'model',
            previousChunks: chunks,
          })
        );
        chunks.push(newChunk);

        assert.deepStrictEqual(result, chunk.want);
      }
    });
  }

  const messageTests = [
    {
      desc: 'parses complete JSONL response',
      message: {
        role: 'model',
        content: [{ text: '{"id": 1, "name": "test"}\n{"id": 2}\n' }],
      },
      want: [{ id: 1, name: 'test' }, { id: 2 }],
    },
    {
      desc: 'handles empty response',
      message: {
        role: 'model',
        content: [{ text: '' }],
      },
      want: [],
    },
    {
      desc: 'parses JSONL with preamble and code fence',
      message: {
        role: 'model',
        content: [
          {
            text: 'Here are the objects:\n\n```\n{"id": 1}\n{"id": 2}\n```',
          },
        ],
      },
      want: [{ id: 1 }, { id: 2 }],
    },
  ];

  for (const rt of messageTests) {
    it(rt.desc, () => {
      const parser = jsonlFormatter.handler();
      assert.deepStrictEqual(
        parser.parseMessage(new Message(rt.message as MessageData)),
        rt.want
      );
    });
  }

  const errorTests = [
    {
      desc: 'throws error for non-array schema type',
      schema: { type: 'string' },
      wantError: /Must supply an 'array' schema type/,
    },
    {
      desc: 'throws error for array schema with non-object items',
      schema: { type: 'array', items: { type: 'string' } },
      wantError: /Must supply an 'array' schema type containing 'object' items/,
    },
  ];

  for (const et of errorTests) {
    it(et.desc, () => {
      assert.throws(() => {
        jsonlFormatter.handler(et.schema);
      }, et.wantError);
    });
  }
});
