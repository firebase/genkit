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

import assert from 'node:assert';
import { afterEach, beforeEach, describe, it } from 'node:test';
import process from 'process';
import {
  API_KEY_FALSE_ERROR,
  MISSING_API_KEY_ERROR,
  calculateApiKey,
  checkApiKey,
  getApiKeyFromEnvVar,
} from '../../src/googleai/utils.js'; // Assuming the file is named utils.ts

describe('API Key Utils', () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    // Save original process.env
    originalEnv = { ...process.env };
  });

  afterEach(() => {
    // Restore original process.env
    process.env = originalEnv;
  });

  // Helper to clear specific env vars
  const clearEnvVars = () => {
    delete process.env.GEMINI_API_KEY;
    delete process.env.GOOGLE_API_KEY;
    delete process.env.GOOGLE_GENAI_API_KEY;
  };

  describe('getApiKeyFromEnvVar', () => {
    it('returns GEMINI_API_KEY if set (priority 1)', () => {
      clearEnvVars();
      process.env.GEMINI_API_KEY = 'gemini_key';
      process.env.GOOGLE_API_KEY = 'google_key';
      process.env.GOOGLE_GENAI_API_KEY = 'genai_key';
      assert.strictEqual(getApiKeyFromEnvVar(), 'gemini_key');
    });

    it('returns GOOGLE_API_KEY if GEMINI_API_KEY is not set (priority 2)', () => {
      clearEnvVars();
      process.env.GOOGLE_API_KEY = 'google_key';
      process.env.GOOGLE_GENAI_API_KEY = 'genai_key';
      assert.strictEqual(getApiKeyFromEnvVar(), 'google_key');
    });

    it('returns GOOGLE_GENAI_API_KEY if others are not set (priority 3)', () => {
      clearEnvVars();
      process.env.GOOGLE_GENAI_API_KEY = 'genai_key';
      assert.strictEqual(getApiKeyFromEnvVar(), 'genai_key');
    });

    it('returns undefined if no relevant env vars are set', () => {
      clearEnvVars();
      assert.strictEqual(getApiKeyFromEnvVar(), undefined);
    });
  });

  describe('checkApiKey', () => {
    beforeEach(() => {
      clearEnvVars();
    });

    it('returns apiKey1 if it is a non-empty string', () => {
      assert.strictEqual(checkApiKey('test_key'), 'test_key');
    });

    it('returns env var key if apiKey1 is undefined', () => {
      process.env.GOOGLE_API_KEY = 'env_key';
      assert.strictEqual(checkApiKey(undefined), 'env_key');
    });

    it('returns env var key if apiKey1 is an empty string', () => {
      process.env.GOOGLE_API_KEY = 'env_key';
      assert.strictEqual(checkApiKey(''), 'env_key');
    });

    it('returns undefined if apiKey1 is false', () => {
      process.env.GOOGLE_API_KEY = 'env_key'; // Should not be used
      assert.strictEqual(checkApiKey(false), undefined);
    });

    it('throws MISSING_API_KEY_ERROR if apiKey1 is undefined and no env var set', () => {
      assert.throws(() => checkApiKey(undefined), MISSING_API_KEY_ERROR);
    });

    it('throws MISSING_API_KEY_ERROR if apiKey1 is empty string and no env var set', () => {
      assert.throws(() => checkApiKey(''), MISSING_API_KEY_ERROR);
    });

    it('does not throw if apiKey1 is false, even with no env var', () => {
      assert.doesNotThrow(() => checkApiKey(false));
      assert.strictEqual(checkApiKey(false), undefined);
    });
  });

  describe('calculateApiKey', () => {
    beforeEach(() => {
      clearEnvVars();
    });

    it('returns apiKey2 if provided, ignoring apiKey1 and env', () => {
      process.env.GOOGLE_API_KEY = 'env_key';
      assert.strictEqual(calculateApiKey('api1_key', 'api2_key'), 'api2_key');
      assert.strictEqual(calculateApiKey(undefined, 'api2_key'), 'api2_key');
      assert.strictEqual(calculateApiKey(false, 'api2_key'), 'api2_key');
    });

    it('returns apiKey1 if apiKey2 is undefined', () => {
      assert.strictEqual(calculateApiKey('api1_key', undefined), 'api1_key');
    });

    it('returns env var key if apiKey1 and apiKey2 are undefined', () => {
      process.env.GOOGLE_API_KEY = 'env_key';
      assert.strictEqual(calculateApiKey(undefined, undefined), 'env_key');
    });

    it('throws API_KEY_FALSE_ERROR if apiKey1 is false and apiKey2 is undefined', () => {
      assert.throws(
        () => calculateApiKey(false, undefined),
        API_KEY_FALSE_ERROR
      );
    });

    it('throws MISSING_API_KEY_ERROR if apiKey1 and apiKey2 are undefined and no env var', () => {
      assert.throws(
        () => calculateApiKey(undefined, undefined),
        MISSING_API_KEY_ERROR
      );
    });

    it('throws MISSING_API_KEY_ERROR if apiKey1 is empty, apiKey2 is undefined, and no env var', () => {
      assert.throws(
        () => calculateApiKey('', undefined),
        MISSING_API_KEY_ERROR
      );
    });

    it('returns env var if apiKey1 is empty and apiKey2 is undefined', () => {
      process.env.GOOGLE_API_KEY = 'env_key';
      assert.strictEqual(calculateApiKey('', undefined), 'env_key');
    });
  });
});
