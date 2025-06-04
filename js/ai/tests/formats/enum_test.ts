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
import { enumFormatter } from '../../src/formats/enum.js';
import { Message } from '../../src/message.js';
import type { MessageData } from '../../src/model.js';

describe('enumFormat', () => {
  const messageTests = [
    {
      desc: 'parses simple enum value',
      message: {
        role: 'model',
        content: [{ text: 'VALUE1' }],
      },
      want: 'VALUE1',
    },
    {
      desc: 'trims whitespace',
      message: {
        role: 'model',
        content: [{ text: '  VALUE2\n' }],
      },
      want: 'VALUE2',
    },
  ];

  for (const rt of messageTests) {
    it(rt.desc, () => {
      const parser = enumFormatter.handler();
      assert.strictEqual(
        parser.parseMessage(new Message(rt.message as MessageData)),
        rt.want
      );
    });
  }

  const errorTests = [
    {
      desc: 'throws error for number schema type',
      schema: { type: 'number' },
      wantError: /Must supply a 'string' or 'enum' schema type/,
    },
    {
      desc: 'throws error for array schema type',
      schema: { type: 'array' },
      wantError: /Must supply a 'string' or 'enum' schema type/,
    },
  ];

  for (const et of errorTests) {
    it(et.desc, () => {
      assert.throws(() => {
        enumFormatter.handler(et.schema);
      }, et.wantError);
    });
  }
});
