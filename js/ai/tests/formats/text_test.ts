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
import { textFormatter } from '../../src/formats/text.js';
import { GenerateResponseChunk } from '../../src/generate.js';
import { Message } from '../../src/message.js';
import { GenerateResponseChunkData, MessageData } from '../../src/model.js';

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
      const parser = textFormatter.handler();
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

        assert.strictEqual(result, chunk.want);
      }
    });
  }

  const messageTests = [
    {
      desc: 'parses complete text response',
      message: {
        role: 'model',
        content: [{ text: 'Hello world' }],
      },
      want: 'Hello world',
    },
    {
      desc: 'handles empty response',
      message: {
        role: 'model',
        content: [{ text: '' }],
      },
      want: '',
    },
  ];

  for (const rt of messageTests) {
    it(rt.desc, () => {
      const parser = textFormatter.handler();
      assert.strictEqual(
        parser.parseMessage(new Message(rt.message as MessageData)),
        rt.want
      );
    });
  }
});
