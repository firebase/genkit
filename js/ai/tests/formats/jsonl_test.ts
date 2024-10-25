import assert from 'node:assert';
import { describe, it } from 'node:test';
import { jsonlParser } from '../../src/formats/jsonl.js';
import { GenerateResponse, GenerateResponseChunk } from '../../src/generate.js';
import { GenerateResponseChunkData } from '../../src/model.js';

describe('jsonlFormat', () => {
  const streamingTests = [
    {
      desc: 'emits complete objects line by line',
      chunks: [
        {
          text: '{"id": 1}\n{"id"',
          want: [{ id: 1 }],
        },
        {
          text: ': 2}\n{"id": 3}',
          want: [{ id: 2 }, { id: 3 }],
        },
      ],
    },
    {
      desc: 'handles preamble with code fence',
      chunks: [
        {
          text: 'Here are the items:\n\n```jsonl\n{"id": 1',
          want: [],
        },
        {
          text: '}\n{"id": 2}\n```',
          want: [{ id: 1 }, { id: 2 }],
        },
      ],
    },
    {
      desc: 'ignores non-object lines',
      chunks: [
        {
          text: 'Starting output:\n{"id": 1}\nsome text\n{"id": 2}',
          want: [{ id: 1 }, { id: 2 }],
        },
      ],
    },
    {
      desc: 'handles objects with nested structures',
      chunks: [
        {
          text: '{"user": {"name": "test"}}\n{"data": ',
          want: [{ user: { name: 'test' } }],
        },
        {
          text: '{"values": [1,2]}}',
          want: [{ data: { values: [1, 2] } }],
        },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = jsonlParser({ messages: [] });
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
      desc: 'parses multiple objects',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '{"id": 1}\n{"id": 2}\n{"id": 3}' }],
        },
      }),
      want: [{ id: 1 }, { id: 2 }, { id: 3 }],
    },
    {
      desc: 'handles empty lines and non-object lines',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '\n{"id": 1}\nsome text\n{"id": 2}\n' }],
        },
      }),
      want: [{ id: 1 }, { id: 2 }],
    },
    {
      desc: 'parses with preamble and code fence',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [
            {
              text: 'Here are the items:\n\n```jsonl\n{"id": 1}\n{"id": 2}\n```',
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
          schema: {
            type: 'array',
            items: { type: 'string' },
          },
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

  it('includes schema in instructions when provided', () => {
    const schema = {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'number' },
        },
      },
    };
    const parser = jsonlParser({
      messages: [],
      output: { schema },
    });

    assert.match(
      parser.instructions as string,
      /Output should be JSONL format/
    );
    assert.match(
      parser.instructions as string,
      new RegExp(JSON.stringify(schema.items))
    );
  });

  it('has no instructions when no schema provided', () => {
    const parser = jsonlParser({ messages: [] });
    assert.strictEqual(parser.instructions, false);
  });
});
