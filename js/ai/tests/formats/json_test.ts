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
import { jsonParser } from '../../src/formats/json.js';
import { GenerateResponse, GenerateResponseChunk } from '../../src/generate.js';
import { GenerateResponseChunkData } from '../../src/model.js';

describe('jsonFormat', () => {
  const streamingTests = [
    {
      desc: 'emits partial object as it streams',
      chunks: [
        {
          text: '{"name": "test',
          want: { name: 'test' },
        },
        {
          text: '", "value": 42}',
          want: { name: 'test', value: 42 },
        },
      ],
    },
    {
      desc: 'handles nested objects',
      chunks: [
        {
          text: '{"outer": {"inner": ',
          want: { outer: {} },
        },
        {
          text: '"value"}}',
          want: { outer: { inner: 'value' } },
        },
      ],
    },
    {
      desc: 'handles preamble with code fence',
      chunks: [
        {
          text: 'Here is the JSON:\n\n```json\n{"key": ',
          want: {},
        },
        {
          text: '"value"}\n```',
          want: { key: 'value' },
        },
      ],
    },
    {
      desc: 'handles arrays',
      chunks: [
        {
          text: '[{"id": 1}, {"id"',
          want: [{ id: 1 }, {}],
        },
        {
          text: ': 2}]',
          want: [{ id: 1 }, { id: 2 }],
        },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = jsonParser({ messages: [] });
      const chunks: GenerateResponseChunkData[] = [];
      let lastEmitted: any;
      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          content: [{ text: chunk.text }],
        };
        chunks.push(newChunk);

        lastEmitted = undefined;
        const emit = (value: any) => {
          lastEmitted = value;
        };
        parser.parseChunk!(new GenerateResponseChunk(newChunk, chunks), emit);

        assert.deepStrictEqual(lastEmitted, chunk.want);
      }
    });
  }

  const responseTests = [
    {
      desc: 'parses complete object response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '{"name": "test", "value": 42}' }],
        },
      }),
      want: { name: 'test', value: 42 },
    },
    {
      desc: 'parses array response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '[1, 2, 3]' }],
        },
      }),
      want: [1, 2, 3],
    },
    {
      desc: 'parses nested structures',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '{"outer": {"inner": [1, 2]}}' }],
        },
      }),
      want: { outer: { inner: [1, 2] } },
    },
    {
      desc: 'parses with preamble and code fence',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [
            { text: 'Here is the JSON:\n\n```json\n{"key": "value"}\n```' },
          ],
        },
      }),
      want: { key: 'value' },
    },
  ];

  for (const rt of responseTests) {
    it(rt.desc, () => {
      const parser = jsonParser({ messages: [] });
      assert.deepStrictEqual(parser.parseResponse(rt.response), rt.want);
    });
  }

  it('includes schema in instructions when provided', () => {
    const schema = {
      type: 'object',
      properties: {
        name: { type: 'string' },
      },
    };
    const parser = jsonParser({
      messages: [],
      output: { schema },
    });

    assert.match(
      parser.instructions as string,
      /Output should be in JSON format/
    );
    assert.match(
      parser.instructions as string,
      new RegExp(JSON.stringify(schema))
    );
  });

  it('has no instructions when no schema provided', () => {
    const parser = jsonParser({ messages: [] });
    assert.strictEqual(parser.instructions, false);
  });
});
