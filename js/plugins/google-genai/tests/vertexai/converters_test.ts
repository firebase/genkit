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
import { toGeminiSafetySettings } from '../../src/vertexai/converters';
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
});
