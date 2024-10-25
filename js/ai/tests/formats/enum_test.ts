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
