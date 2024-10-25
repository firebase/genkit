import { GenkitError } from '@genkit-ai/core';
import assert from 'node:assert';
import { describe, it } from 'node:test';
import { enumParser } from '../../src/formats/enum.js';
import { GenerateResponse } from '../../src/generate.js';

describe('enumFormat', () => {
  const responseTests = [
    {
      desc: 'parses simple string response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: 'value1' }],
        },
      }),
      want: 'value1',
    },
    {
      desc: 'trims whitespace from response',
      response: new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '  value2  \n' }],
        },
      }),
      want: 'value2',
    },
  ];

  for (const rt of responseTests) {
    it(rt.desc, () => {
      const parser = enumParser({
        messages: [],
        output: { schema: { type: 'string' } },
      });
      assert.strictEqual(parser.parseResponse(rt.response), rt.want);
    });
  }

  it('throws error for invalid schema type', () => {
    assert.throws(
      () => {
        enumParser({ messages: [], output: { schema: { type: 'number' } } });
      },
      (err: GenkitError) => {
        return (
          err.status === 'INVALID_ARGUMENT' &&
          err.message.includes(
            `Must supply a 'string' or 'enum' schema type when using the enum parser format.`
          )
        );
      }
    );
  });

  it('includes enum values in instructions when provided', () => {
    const enumValues = ['option1', 'option2', 'option3'];
    const parser = enumParser({
      messages: [],
      output: { schema: { type: 'enum', enum: enumValues } },
    });

    assert.match(
      parser.instructions as string,
      /Output should be ONLY one of the following enum values/
    );
    for (const value of enumValues) {
      assert.match(parser.instructions as string, new RegExp(value));
    }
  });

  it('has no instructions when no enum values provided', () => {
    const parser = enumParser({
      messages: [],
      output: { schema: { type: 'string' } },
    });
    assert.strictEqual(parser.instructions, false);
  });
});
