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
import { jsonFormatter } from '../../src/formats/json.js';
import { GenerateResponseChunk } from '../../src/generate.js';
import { Message } from '../../src/message.js';
import { GenerateResponseChunkData, MessageData } from '../../src/model.js';

describe('jsonFormat', () => {
  const streamingTests = [
    {
      desc: 'parses complete JSON object',
      chunks: [
        {
          text: '{"id": 1, "name": "test"}',
          want: { id: 1, name: 'test' },
        },
      ],
    },
    {
      desc: 'handles partial JSON',
      chunks: [
        {
          text: '{"id": 1',
          want: { id: 1 },
        },
        {
          text: ', "name": "test"}',
          want: { id: 1, name: 'test' },
        },
      ],
    },
    {
      desc: 'handles preamble with code fence',
      chunks: [
        {
          text: 'Here is the JSON:\n\n```json\n',
          want: null,
        },
        {
          text: '{"id": 1}\n```',
          want: { id: 1 },
        },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = jsonFormatter.handler();
      const chunks: GenerateResponseChunkData[] = [];
      let lastCursor = '';

      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          content: [{ text: chunk.text }],
        };

        const result = parser.parseChunk!(
          new GenerateResponseChunk(newChunk, { previousChunks: [...chunks] }),
          lastCursor
        );
        chunks.push(newChunk);

        assert.deepStrictEqual(result, chunk.want);
      }
    });
  }

  const messageTests = [
    {
      desc: 'parses complete JSON response',
      message: {
        role: 'model',
        content: [{ text: '{"id": 1, "name": "test"}' }],
      },
      want: { id: 1, name: 'test' },
    },
    {
      desc: 'handles empty response',
      message: {
        role: 'model',
        content: [{ text: '' }],
      },
      want: null,
    },
    {
      desc: 'parses JSON with preamble and code fence',
      message: {
        role: 'model',
        content: [{ text: 'Here is the JSON:\n\n```json\n{"id": 1}\n```' }],
      },
      want: { id: 1 },
    },
  ];

  for (const rt of messageTests) {
    it(rt.desc, () => {
      const parser = jsonFormatter.handler();
      assert.deepStrictEqual(
        parser.parseMessage(new Message(rt.message as MessageData)),
        rt.want
      );
    });
  }
});
