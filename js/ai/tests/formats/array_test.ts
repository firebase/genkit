import assert from 'node:assert';
import { describe, it } from 'node:test';
import { arrayParser } from '../../src/formats/array.js';
import { GenerateResponse, GenerateResponseChunk } from '../../src/generate.js';
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
      const parser = arrayParser({ messages: [] });
      const chunks: GenerateResponseChunkData[] = [];
      let lastEmitted: any[] = [];
      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          content: [{ text: chunk.text }],
        };
        chunks.push(newChunk);

        lastEmitted = [];
        const emit = (item: any) => {
          lastEmitted.push(item);
        };
        parser.parseChunk!(new GenerateResponseChunk(newChunk, chunks), emit);

        assert.deepStrictEqual(lastEmitted, chunk.want);
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
      const parser = arrayParser({ messages: [] });
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
        arrayParser(et.request);
      }, et.wantError);
    });
  }
});
