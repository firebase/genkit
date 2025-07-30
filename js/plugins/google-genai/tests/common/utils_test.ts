/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import * as assert from 'assert';
import { GenkitError } from 'genkit';
import { GenerateRequest } from 'genkit/model';
import { describe, it } from 'node:test';
import {
  checkModelName,
  cleanSchema,
  extractErrMsg,
  extractImagenImage,
  extractText,
  modelName,
} from '../../src/common/utils';

describe('extractErrMsg', () => {
  it('extracts message from an Error object', () => {
    const error = new Error('This is a test error.');
    assert.strictEqual(extractErrMsg(error), 'This is a test error.');
  });

  it('returns the string if error is a string', () => {
    const error = 'A simple string error.';
    assert.strictEqual(extractErrMsg(error), 'A simple string error.');
  });

  it('stringifies other error types', () => {
    const error = { code: 500, message: 'Object error' };
    assert.strictEqual(
      extractErrMsg(error),
      '{"code":500,"message":"Object error"}'
    );
  });

  it('provides a default message for unknown types', () => {
    // Note: The function returns undefined for an undefined input because
    // JSON.stringify(undefined) results in undefined.
    assert.strictEqual(extractErrMsg(undefined), undefined);
    assert.strictEqual(extractErrMsg(null), 'null');
  });
});

describe('modelName', () => {
  it('extracts model name from a full path', () => {
    const name = 'models/googleai/gemini-2.5-pro';
    assert.strictEqual(modelName(name), 'gemini-2.5-pro');
  });

  it('returns the name if no path is present', () => {
    const name = 'gemini-1.5-flash';
    assert.strictEqual(modelName(name), 'gemini-1.5-flash');
  });

  it('handles undefined input', () => {
    assert.strictEqual(modelName(undefined), undefined);
  });

  it('handles empty string input', () => {
    assert.strictEqual(modelName(''), '');
  });

  it('keeps prefixes like tunedModels', () => {
    assert.strictEqual(
      modelName('tunedModels/my-tuned-model'),
      'tunedModels/my-tuned-model'
    );
  });
});

describe('checkModelName', () => {
  it('extracts model name from a full path', () => {
    const name = 'models/vertexai/gemini-2.0-pro';
    assert.strictEqual(checkModelName(name), 'gemini-2.0-pro');
  });

  it('throws an error for undefined input', () => {
    assert.throws(
      () => checkModelName(undefined),
      (err: GenkitError) => {
        assert.strictEqual(err.status, 'INVALID_ARGUMENT');
        assert.strictEqual(
          err.message,
          'INVALID_ARGUMENT: Model name is required.'
        );
        return true;
      }
    );
  });

  it('throws an error for an empty string', () => {
    assert.throws(
      () => checkModelName(''),
      (err: GenkitError) => {
        assert.strictEqual(err.status, 'INVALID_ARGUMENT');
        assert.strictEqual(
          err.message,
          'INVALID_ARGUMENT: Model name is required.'
        );
        return true;
      }
    );
  });
});

describe('extractText', () => {
  it('extracts text from the last message', () => {
    const request: GenerateRequest = {
      messages: [
        { role: 'user', content: [{ text: 'Hello there.' }] },
        { role: 'model', content: [{ text: 'How can I help?' }] },
        { role: 'user', content: [{ text: 'Tell me a joke.' }] },
      ],
      config: {},
    };
    assert.strictEqual(extractText(request), 'Tell me a joke.');
  });

  it('concatenates multiple text parts', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [{ text: 'Part 1. ' }, { text: 'Part 2.' }],
        },
      ],
      config: {},
    };
    assert.strictEqual(extractText(request), 'Part 1. Part 2.');
  });

  it('returns an empty string if there are no text parts', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: 'data:image/jpeg;base64,IMAGEDATA',
                contentType: 'image/jpeg',
              },
            },
          ],
        },
      ],
      config: {},
    };
    assert.strictEqual(extractText(request), '');
  });

  it('returns an empty string if there are no messages', () => {
    const request: GenerateRequest = {
      messages: [],
      config: {},
    };
    assert.strictEqual(extractText(request), '');
  });
});

describe('extractImagenImage', () => {
  it('extracts a base64 encoded image', () => {
    const base64Image = '/9j/4AAQSkZJRg...';
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            { text: 'Create an image.' },
            {
              media: {
                url: `data:image/jpeg;base64,${base64Image}`,
                contentType: 'image/jpeg',
              },
            },
          ],
        },
      ],
      config: {},
    };
    const result = extractImagenImage(request);
    assert.deepStrictEqual(result, { bytesBase64Encoded: base64Image });
  });

  it('returns undefined if no image part exists', () => {
    const request: GenerateRequest = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      config: {},
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });

  it('returns undefined if the media part is not a base64 data URI', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: 'http://example.com/image.jpg',
                contentType: 'image/jpeg',
              },
            },
          ],
        },
      ],
      config: {},
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });

  it('ignores parts with metadata type not equal to "base"', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: 'data:image/png;base64,MASKDATA',
                contentType: 'image/png',
              },
              metadata: { type: 'mask' },
            },
          ],
        },
      ],
      config: {},
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });

  it('returns undefined for an empty message list', () => {
    const request: GenerateRequest = {
      messages: [],
      config: {},
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });
});

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
