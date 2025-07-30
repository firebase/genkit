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
import { z } from 'genkit';
import { describe, it } from 'node:test';
import { HarmBlockThreshold, HarmCategory } from '../../src/common/types';
import {
  toGeminiLabels,
  toGeminiSafetySettings,
} from '../../src/vertexai/converters';
import { SafetySettingsSchema } from '../../src/vertexai/gemini';

describe('Vertex AI Converters', () => {
  describe('toGeminiSafetySettings', () => {
    it('returns undefined for undefined input', () => {
      const result = toGeminiSafetySettings(undefined);
      assert.strictEqual(result, undefined);
    });

    it('returns an empty array for an empty array input', () => {
      const result = toGeminiSafetySettings([]);
      assert.deepStrictEqual(result, []);
    });

    it('converts genkit safety settings to Gemini safety settings', () => {
      const genkitSettings: z.infer<typeof SafetySettingsSchema>[] = [
        {
          category: 'HARM_CATEGORY_HATE_SPEECH',
          threshold: 'BLOCK_LOW_AND_ABOVE',
        },
        {
          category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
          threshold: 'BLOCK_NONE',
        },
      ];

      const expected = [
        {
          category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
          threshold: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        {
          category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
          threshold: HarmBlockThreshold.BLOCK_NONE,
        },
      ];

      const result = toGeminiSafetySettings(genkitSettings);
      assert.deepStrictEqual(result, expected);
    });
  });

  describe('toGeminiLabels', () => {
    it('returns undefined for undefined input', () => {
      const result = toGeminiLabels(undefined);
      assert.strictEqual(result, undefined);
    });

    it('returns undefined for an empty object input', () => {
      const result = toGeminiLabels({});
      assert.strictEqual(result, undefined);
    });

    it('converts an object with valid labels', () => {
      const labels = {
        env: 'production',
        'my-label': 'my-value',
      };
      const result = toGeminiLabels(labels);
      assert.deepStrictEqual(result, labels);
    });

    it('filters out empty string keys', () => {
      const labels = {
        env: 'dev',
        '': 'should-be-ignored',
        'valid-key': 'valid-value',
      };
      const expected = {
        env: 'dev',
        'valid-key': 'valid-value',
      };
      const result = toGeminiLabels(labels);
      assert.deepStrictEqual(result, expected);
    });

    it('returns undefined if all keys are empty strings', () => {
      const labels = {
        '': 'value1',
        ' ': 'value2', // This key is not empty string, so it will be kept
      };
      const expected = {
        ' ': 'value2',
      };
      const result = toGeminiLabels(labels);
      assert.deepStrictEqual(result, expected);
    });

    it('handles labels with empty values', () => {
      const labels = {
        key1: '',
        key2: 'value2',
      };
      const expected = {
        key1: '',
        key2: 'value2',
      };
      const result = toGeminiLabels(labels);
      assert.deepStrictEqual(result, expected);
    });
  });
});
