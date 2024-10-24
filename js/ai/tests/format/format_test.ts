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
import { z } from 'zod';
import {
  FormatParser,
  defineFormat,
  getAvailableFormats,
  getFormatParser,
} from '../../src/format';
import {
  Candidate,
  GenerateOptions,
  GenerateResponse,
  GenerateResponseChunk,
} from '../../src/generate';

describe('format', () => {
  describe('getAvailableFormats()', () => {
    it('returns available formats', () => {
      const formats = getAvailableFormats();
      assert(formats.includes('text'));
      assert(formats.includes('json'));
    });
  });

  describe('defineFormat()', () => {
    it('adds a new format parser', () => {
      const customFormat: FormatParser<string> = {
        name: 'custom',
        parseResponse: () => 'custom response',
        parseChunk: () => 'custom chunk',
      };

      defineFormat(customFormat);
      const parser = getFormatParser('custom');
      assert.strictEqual(parser, customFormat);
    });
  });

  describe('getFormatParser()', () => {
    it('returns undefined for non-existent format', () => {
      const parser = getFormatParser('non-existent');
      assert.strictEqual(parser, undefined);
    });

    it('returns text format parser', () => {
      const parser = getFormatParser('text');
      assert.strictEqual(typeof parser?.parseResponse, 'function');
      assert.strictEqual(typeof parser?.parseChunk, 'function');
    });

    it('returns json format parser', () => {
      const parser = getFormatParser('json');
      assert.strictEqual(typeof parser?.parseResponse, 'function');
      assert.strictEqual(typeof parser?.parseChunk, 'function');
      assert.strictEqual(typeof parser?.instructions, 'function');
    });
  });

  describe('text format', () => {
    it('parses response correctly', () => {
      const textParser = getFormatParser('text');
      const mockResponse = {
        candidates: [
          new Candidate({
            message: { role: 'model', content: [{ text: 'Hello, world!' }] },
            index: 0,
            usage: {},
            finishReason: 'stop',
            custom: {},
          }),
        ],
      } as unknown as GenerateResponse;

      const result = textParser?.parseResponse(mockResponse);
      assert.strictEqual(result, 'Hello, world!');
    });

    it('parses chunk correctly', () => {
      const textParser = getFormatParser('text');
      const mockChunk = {
        accumulatedChunks: [
          { content: [{ text: 'Hello' }] },
          { content: [{ text: ', world!' }] },
        ],
      } as unknown as GenerateResponseChunk;

      const result = textParser!.parseChunk!(mockChunk);
      assert.strictEqual(result, 'Hello, world!');
    });
  });

  describe('json format', () => {
    it('parses response correctly', () => {
      const jsonParser = getFormatParser('json');
      const mockResponse = {
        candidates: [
          new Candidate({
            message: { role: 'model', content: [{ text: '{"key": "value"}' }] },
            index: 0,
            usage: {},
            finishReason: 'stop',
            custom: {},
          }),
        ],
      } as unknown as GenerateResponse;

      const result = jsonParser?.parseResponse(mockResponse);
      assert.deepStrictEqual(result, { key: 'value' });
    });

    it('parses chunk correctly', () => {
      const jsonParser = getFormatParser('json');
      const mockChunk = {
        accumulatedChunks: [
          { content: [{ text: '{"key":' }] },
          { content: [{ text: ' "value"}' }] },
        ],
      } as unknown as GenerateResponseChunk;

      const result = jsonParser!.parseChunk!(mockChunk);
      assert.deepStrictEqual(result, { key: 'value' });
    });

    it('generates instructions correctly', () => {
      const jsonParser = getFormatParser('json');
      const mockRequest: GenerateOptions = {
        prompt: 'Generate a JSON object',
        output: {
          schema: z.object({
            key: z.string(),
          }),
        },
      };

      const instructions = jsonParser!.instructions!(mockRequest);
      assert(
        instructions?.includes(
          'Output should be in JSON format with the following schema:'
        )
      );
      assert(
        instructions?.includes(
          '{"type":"object","properties":{"key":{"type":"string"}},"required":["key"],"additionalProperties":true,"$schema":"http://json-schema.org/draft-07/schema#"}'
        )
      );
    });
  });
});
