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
import { textFormatter } from '../../src/formats/text.js';
import { GenerateResponse, GenerateResponseChunk } from '../../src/generate.js';
import { GenerateResponseChunkData } from '../../src/model.js';

describe('textFormat', () => {
  const streamingTests = [
    {
      desc: 'emits text chunks as they arrive',
      chunks: [
        {
          text: 'Hello',
          want: 'Hello',
        },
        {
          text: ' world',
          want: ' world',
        },
      ],
    },
    {
      desc: 'handles empty chunks',
      chunks: [
        {
          text: '',
          want: '',
        },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = textFormatter.handler({ messages: [] });
      const chunks: GenerateResponseChunkData[] = [];

      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          content: [{ text: chunk.text }],
        };

        const result = parser.parseChunk!(
          new GenerateResponseChunk(newChunk, { previousChunks: chunks })
        );
        chunks.push(newChunk);

        assert.strictEqual(result, chunk.want);
      }
    });
  }

  const responseTests = [
    {
      desc: 'parses complete text response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: 'Hello world' }],
        },
      }),
      want: 'Hello world',
    },
    {
      desc: 'handles empty response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '' }],
        },
      }),
      want: '',
    },
  ];

  for (const rt of responseTests) {
    it(rt.desc, () => {
      const parser = textFormatter.handler({ messages: [] });
      assert.strictEqual(parser.parseResponse(rt.response), rt.want);
    });
  }
});
