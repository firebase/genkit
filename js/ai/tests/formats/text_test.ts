import assert from 'node:assert';
import { describe, it } from 'node:test';
import { textParser } from '../../src/formats/text.js';
import { GenerateResponse, GenerateResponseChunk } from '../../src/generate.js';
import { GenerateResponseChunkData } from '../../src/model.js';

describe('textFormat', () => {
  const streamingTests = [
    {
      desc: 'emits each chunk as it comes',
      chunks: [
        { text: 'this is', want: ['this is'] },
        { text: ' a two-chunk response', want: [' a two-chunk response'] },
      ],
    },
  ];

  for (const st of streamingTests) {
    it(st.desc, () => {
      const parser = textParser({ messages: [] });
      const chunks: GenerateResponseChunkData[] = [];
      let lastEmitted: string[] = [];
      for (const chunk of st.chunks) {
        const newChunk: GenerateResponseChunkData = {
          content: [{ text: chunk.text }],
        };
        chunks.push(newChunk);

        lastEmitted = [];
        const emit = (chunk: string) => {
          lastEmitted.push(chunk);
        };
        parser.parseChunk!(new GenerateResponseChunk(newChunk, chunks), emit);

        assert.deepStrictEqual(lastEmitted, chunk.want);
      }
    });
  }

  const responseTests = [
    {
      desc: 'it returns the concatenated text',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: 'chunk one.' }, { text: 'chunk two.' }],
        },
      }),
      want: 'chunk one.chunk two.',
    },
  ];

  for (const rt of responseTests) {
    it(rt.desc, () => {
      const parser = textParser({ messages: [] });
      assert.deepStrictEqual(parser.parseResponse(rt.response), rt.want);
    });
  }
});
