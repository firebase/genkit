/**
 * Copyright 2025 Google LLC
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
import { ModelReference } from 'genkit';
import { describe, it } from 'node:test';
import { cleanSchema } from '../../src/common/utils';

// Mock ModelReference for testing nearestModelRef
const createMockModelRef = (
  name: string,
  version?: string
): ModelReference<any> => {
  return {
    name,
    info: { label: `Model ${name}`, supports: {} },
    config: { version },
    withConfig: function (newConfig) {
      // Return a new object to mimic immutability
      return {
        ...this,
        config: { ...this.config, ...newConfig },
      };
    },
  } as any;
};

describe('cleanSchema', () => {
  it('strips $schema and additionalProperties', () => {
    const schema = {
      type: 'object',
      properties: { name: { type: 'string' } },
      $schema: 'http://json-schema.org/draft-07/schema#',
      additionalProperties: false,
    };
    const cleaned = cleanSchema(schema);
    assert.deepStrictEqual(cleaned, {
      type: 'object',
      properties: { name: { type: 'string' } },
    });
  });

  it('handles nested objects', () => {
    const schema = {
      type: 'object',
      properties: {
        user: {
          type: 'object',
          properties: { id: { type: 'number' } },
          additionalProperties: true,
        },
      },
    };
    const cleaned = cleanSchema(schema);
    assert.deepStrictEqual(cleaned, {
      type: 'object',
      properties: {
        user: {
          type: 'object',
          properties: { id: { type: 'number' } },
        },
      },
    });
  });

  it('converts type ["string", "null"] to "string"', () => {
    const schema = {
      type: 'object',
      properties: {
        name: { type: ['string', 'null'] },
        age: { type: ['number', 'null'] },
      },
    };
    const cleaned = cleanSchema(schema);
    assert.deepStrictEqual(cleaned, {
      type: 'object',
      properties: {
        name: { type: 'string' },
        age: { type: 'number' },
      },
    });
  });

  it('converts type ["null", "string"] to "string"', () => {
    const schema = {
      type: 'object',
      properties: {
        name: { type: ['null', 'string'] },
      },
    };
    const cleaned = cleanSchema(schema);
    assert.deepStrictEqual(cleaned, {
      type: 'object',
      properties: {
        name: { type: 'string' },
      },
    });
  });

  it('leaves other properties untouched', () => {
    const schema = {
      type: 'string',
      description: 'A name',
      maxLength: 100,
    };
    const cleaned = cleanSchema(schema);
    assert.deepStrictEqual(cleaned, schema);
  });
});
