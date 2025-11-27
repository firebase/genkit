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
import { GenkitError, embedderRef, modelRef } from 'genkit';
import { GenerateRequest } from 'genkit/model';
import { describe, it } from 'node:test';
import { GenerateContentResponse } from '../../src/common/types.js';
import {
  TEST_ONLY,
  checkModelName,
  checkSupportedMimeType,
  cleanSchema,
  displayUrl,
  extractErrMsg,
  extractMedia,
  extractMimeType,
  extractText,
  extractVersion,
  modelName,
} from '../../src/common/utils.js';

const { aggregateResponses } = TEST_ONLY;

describe('Common Utils', () => {
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
  });

  describe('extractVersion', () => {
    it('should return version from modelRef if present', () => {
      const ref = modelRef({
        name: 'vertexai/gemini-1.5-pro',
        version: 'gemini-1.5-pro-001',
      });
      assert.strictEqual(extractVersion(ref), 'gemini-1.5-pro-001');
    });

    it('should extract version from name if version field is missing', () => {
      const ref = modelRef({ name: 'vertexai/gemini-2.5-flash' });
      assert.strictEqual(extractVersion(ref), 'gemini-2.5-flash');
    });

    it('should work with embedderRef', () => {
      const ref = embedderRef({ name: 'vertexai/text-embedding-004' });
      assert.strictEqual(extractVersion(ref), 'text-embedding-004');
    });
  });

  describe('modelName', () => {
    it('extracts model name from a full path', () => {
      assert.strictEqual(
        modelName('models/googleai/gemini-1.5-pro'),
        'gemini-1.5-pro'
      );
      assert.strictEqual(
        modelName('vertexai/gemini-2.5-flash'),
        'gemini-2.5-flash'
      );
      assert.strictEqual(modelName('model/foo'), 'foo');
      assert.strictEqual(modelName('embedders/bar'), 'bar');
      assert.strictEqual(modelName('background-model/baz'), 'baz');
    });

    it('returns the name if no known prefix is present', () => {
      assert.strictEqual(modelName('gemini-1.0-ultra'), 'gemini-1.0-ultra');
    });

    it('handles undefined input', () => {
      assert.strictEqual(modelName(undefined), undefined);
    });

    it('handles empty string input', () => {
      assert.strictEqual(modelName(''), '');
    });
  });

  describe('checkModelName', () => {
    it('extracts model name from a full path', () => {
      const name = 'models/vertexai/gemini-1.5-pro';
      assert.strictEqual(checkModelName(name), 'gemini-1.5-pro');
    });

    it('returns name if no prefix', () => {
      assert.strictEqual(checkModelName('foo-bar'), 'foo-bar');
    });

    it('throws an error for undefined input', () => {
      assert.throws(
        () => checkModelName(undefined),
        (err: any) => {
          assert.ok(err instanceof GenkitError, 'Expected GenkitError');
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
        (err: any) => {
          assert.ok(err instanceof GenkitError, 'Expected GenkitError');
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
      };
      assert.strictEqual(extractText(request), 'Tell me a joke.');
    });

    it('concatenates multiple text parts in the last message', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [{ text: 'Part 1. ' }, { text: 'Part 2.' }],
          },
        ],
      };
      assert.strictEqual(extractText(request), 'Part 1. Part 2.');
    });

    it('ignores non-text parts in the last message', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [
              { text: 'A ' },
              { media: { url: 'data:image/jpeg;base64,IMAGEDATA' } },
              { text: 'B' },
            ],
          },
        ],
      };
      assert.strictEqual(extractText(request), 'A B');
    });

    it('returns an empty string if there are no text parts in the last message', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [{ media: { url: 'data:image/jpeg;base64,IMAGEDATA' } }],
          },
        ],
      };
      assert.strictEqual(extractText(request), '');
    });

    it('returns an empty string if there are no messages', () => {
      const request: GenerateRequest = {
        messages: [],
      };
      assert.strictEqual(extractText(request), '');
    });
  });

  describe('extractMimeType', () => {
    it('extracts from data URL with base64', () => {
      assert.strictEqual(
        extractMimeType('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA...'),
        'image/png'
      );
      assert.strictEqual(
        extractMimeType('data:application/pdf;base64,JVBERi0xLjQKJ...'),
        'application/pdf'
      );
    });

    it('returns empty string for invalid data URL format', () => {
      assert.strictEqual(extractMimeType('data:image/png'), '');
      assert.strictEqual(extractMimeType('data:,text'), '');
    });

    it('extracts from known file extensions', () => {
      assert.strictEqual(extractMimeType('image.jpg'), 'image/jpeg');
      assert.strictEqual(extractMimeType('path/to/document.png'), 'image/png');
      assert.strictEqual(extractMimeType('video.mp4'), 'video/mp4');
    });

    it('returns empty string for unknown file extensions', () => {
      assert.strictEqual(extractMimeType('file.unknown'), '');
      assert.strictEqual(extractMimeType('archive.zip'), '');
    });

    it('returns empty string for URL without extension', () => {
      assert.strictEqual(extractMimeType('http://example.com/image'), '');
    });

    it('returns empty string for undefined or empty input', () => {
      assert.strictEqual(extractMimeType(undefined), '');
      assert.strictEqual(extractMimeType(''), '');
    });
  });

  describe('checkSupportedMimeType', () => {
    const supported = ['image/jpeg', 'image/png'];
    it('should not throw for supported mime types', () => {
      assert.doesNotThrow(() =>
        checkSupportedMimeType(
          { url: 'test.jpg', contentType: 'image/jpeg' },
          supported
        )
      );
      assert.doesNotThrow(() =>
        checkSupportedMimeType(
          { url: 'test.png', contentType: 'image/png' },
          supported
        )
      );
    });

    it('should throw GenkitError for unsupported mime types', () => {
      try {
        checkSupportedMimeType(
          { url: 'test.gif', contentType: 'image/gif' },
          supported
        );
        assert.fail('Should have thrown');
      } catch (e: any) {
        assert.ok(e instanceof GenkitError, 'Expected GenkitError');
        assert.strictEqual(e.status, 'INVALID_ARGUMENT');
        assert.ok(
          e.message.includes('Invalid mimeType for test.gif: "image/gif"')
        );
        assert.ok(
          e.message.includes('Supported mimeTypes: image/jpeg, image/png')
        );
      }
    });

    it('should throw GenkitError if contentType is missing', () => {
      try {
        checkSupportedMimeType({ url: 'test.jpg' }, supported);
        assert.fail('Should have thrown');
      } catch (e: any) {
        assert.ok(e instanceof GenkitError, 'Expected GenkitError');
        assert.strictEqual(e.status, 'INVALID_ARGUMENT');
        assert.ok(
          e.message.includes('Invalid mimeType for test.jpg: "undefined"')
        );
      }
    });
  });

  describe('displayUrl', () => {
    it('should return the full URL if short', () => {
      const url = 'http://example.com/short';
      assert.strictEqual(displayUrl(url), url);
    });

    it('should truncate long URLs', () => {
      const longUrl =
        'http://example.com/this/is/a/very/long/url/that/needs/truncation/to/fit';
      const expected = 'http://example.com/this/i...t/needs/truncation/to/fit';
      assert.strictEqual(displayUrl(longUrl), expected);
    });

    it('should handle URLs exactly at the limit', () => {
      const url = 'a'.repeat(50);
      assert.strictEqual(displayUrl(url), url);
    });
  });

  describe('extractMedia', () => {
    const imageMedia = {
      url: 'data:image/png;base64,IMAGEDATA',
      contentType: 'image/png',
    };
    const videoMedia = {
      url: 'data:video/mp4;base64,VIDEODATA',
      contentType: 'video/mp4',
    };

    it('extracts any media from the last message if no params', () => {
      const request: GenerateRequest = {
        messages: [
          { role: 'user', content: [{ text: 'A ' }, { media: imageMedia }] },
        ],
      };
      assert.deepStrictEqual(extractMedia(request, {}), imageMedia);
    });

    it('extracts media matching metadataType', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [
              { media: imageMedia, metadata: { type: 'image' } },
              { media: videoMedia, metadata: { type: 'video' } },
            ],
          },
        ],
      };
      assert.deepStrictEqual(
        extractMedia(request, { metadataType: 'video' }),
        videoMedia
      );
      assert.deepStrictEqual(
        extractMedia(request, { metadataType: 'image' }),
        imageMedia
      );
    });

    it('extracts media with no metadata type if isDefault is true', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [
              { media: imageMedia },
              { media: videoMedia, metadata: { type: 'video' } },
            ],
          },
        ],
      };
      assert.deepStrictEqual(
        extractMedia(request, { metadataType: 'image', isDefault: true }),
        imageMedia
      );
    });

    it('does not extract media with different metadataType even if isDefault is true', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [{ media: videoMedia, metadata: { type: 'video' } }],
          },
        ],
      };
      assert.strictEqual(
        extractMedia(request, { metadataType: 'image', isDefault: true }),
        undefined
      );
    });

    it('returns undefined if no media matches metadataType', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [{ media: imageMedia, metadata: { type: 'image' } }],
          },
        ],
      };
      assert.strictEqual(
        extractMedia(request, { metadataType: 'video' }),
        undefined
      );
    });

    it('infers contentType if missing', () => {
      const request: GenerateRequest = {
        messages: [
          {
            role: 'user',
            content: [{ media: { url: 'data:image/jpeg;base64,DATA' } }],
          },
        ],
      };
      const result = extractMedia(request, {});
      assert.deepStrictEqual(result, {
        url: 'data:image/jpeg;base64,DATA',
        contentType: 'image/jpeg',
      });
    });

    it('returns undefined if no media parts in the last message', () => {
      const request: GenerateRequest = {
        messages: [{ role: 'user', content: [{ text: 'No media' }] }],
      };
      assert.strictEqual(extractMedia(request, {}), undefined);
    });

    it('returns undefined for empty messages array', () => {
      const request: GenerateRequest = { messages: [] };
      assert.strictEqual(extractMedia(request, {}), undefined);
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

    it('converts type ["null", "boolean"] to "boolean"', () => {
      const schema = {
        type: 'object',
        properties: {
          isActive: { type: ['null', 'boolean'] },
        },
      };
      const cleaned = cleanSchema(schema);
      assert.deepStrictEqual(cleaned, {
        type: 'object',
        properties: {
          isActive: { type: 'boolean' },
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

  describe('aggregateResponses', () => {
    it('should aggregate streaming function call parts', () => {
      const responses: GenerateContentResponse[] = [
        {
          candidates: [
            {
              index: 0,
              content: {
                role: 'model',
                parts: [
                  {
                    functionCall: {
                      name: 'findFlights',
                      id: '1234',
                      willContinue: true,
                    },
                    thoughtSignature: 'thoughtSignature1234',
                  },
                ],
              },
            },
          ],
        },
        {
          candidates: [
            {
              index: 0,
              content: {
                role: 'model',
                parts: [
                  {
                    functionCall: {
                      willContinue: true,
                      partialArgs: [
                        {
                          jsonPath: '$.flights[0].departure_airport',
                          stringValue: 'SFO',
                        },
                      ],
                    },
                  },
                ],
              },
            },
          ],
        },
        {
          candidates: [
            {
              index: 0,
              content: {
                role: 'model',
                parts: [
                  {
                    functionCall: {
                      willContinue: true,
                      partialArgs: [
                        {
                          jsonPath: '$.flights[0].arrival_airport',
                          stringValue: 'JFK',
                        },
                      ],
                    },
                  },
                ],
              },
            },
          ],
        },
        {
          candidates: [
            {
              index: 0,
              content: {
                role: 'model',
                parts: [
                  {
                    functionCall: {
                      name: 'findFlights',
                    },
                  },
                ],
              },
            },
          ],
        },
      ];

      const aggregated = aggregateResponses(responses);

      const expected = {
        candidates: [
          {
            index: 0,
            content: {
              role: 'model',
              parts: [
                {
                  functionCall: {
                    name: 'findFlights',
                    id: '1234',
                    args: {
                      flights: [
                        {
                          departure_airport: 'SFO',
                          arrival_airport: 'JFK',
                        },
                      ],
                    },
                  },
                  thoughtSignature: 'thoughtSignature1234',
                },
              ],
            },
          },
        ],
      };

      assert.deepStrictEqual(aggregated, expected);
    });
  });
});
