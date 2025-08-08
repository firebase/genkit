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

import { describe, expect, it } from '@jest/globals';
import {
  BASE_RETRY_DELAY_MS,
  DEFAULT_BATCH_SIZE,
  DEFAULT_DATA_FIELD_NAME,
  DEFAULT_DATA_TYPE_FIELD_NAME,
  DEFAULT_EMBEDDING_FIELD_NAME,
  DEFAULT_METADATA_FIELD_NAME,
  JITTER_FACTOR,
  MAX_NUM_CANDIDATES,
  RETRY_ATTEMPTS,
} from '../../src/common/constants';

describe('constants', () => {
  describe('field name constants', () => {
    it('should have correct default field names', () => {
      expect(DEFAULT_DATA_FIELD_NAME).toBe('data');
      expect(DEFAULT_METADATA_FIELD_NAME).toBe('metadata');
      expect(DEFAULT_DATA_TYPE_FIELD_NAME).toBe('dataType');
      expect(DEFAULT_EMBEDDING_FIELD_NAME).toBe('embedding');
    });

    it('should have string values', () => {
      expect(typeof DEFAULT_DATA_FIELD_NAME).toBe('string');
      expect(typeof DEFAULT_METADATA_FIELD_NAME).toBe('string');
      expect(typeof DEFAULT_DATA_TYPE_FIELD_NAME).toBe('string');
      expect(typeof DEFAULT_EMBEDDING_FIELD_NAME).toBe('string');
    });

    it('should have non-empty values', () => {
      expect(DEFAULT_DATA_FIELD_NAME.length).toBeGreaterThan(0);
      expect(DEFAULT_METADATA_FIELD_NAME.length).toBeGreaterThan(0);
      expect(DEFAULT_DATA_TYPE_FIELD_NAME.length).toBeGreaterThan(0);
      expect(DEFAULT_EMBEDDING_FIELD_NAME.length).toBeGreaterThan(0);
    });
  });

  describe('batch size constant', () => {
    it('should have a positive integer value', () => {
      expect(DEFAULT_BATCH_SIZE).toBeGreaterThan(0);
      expect(Number.isInteger(DEFAULT_BATCH_SIZE)).toBe(true);
    });
  });

  describe('max candidates constant', () => {
    it('should have a positive integer value', () => {
      expect(MAX_NUM_CANDIDATES).toBeGreaterThan(0);
      expect(Number.isInteger(MAX_NUM_CANDIDATES)).toBe(true);
    });
  });

  describe('retry constants', () => {
    it('should have positive integer values', () => {
      expect(BASE_RETRY_DELAY_MS).toBeGreaterThan(0);
      expect(Number.isInteger(BASE_RETRY_DELAY_MS)).toBe(true);

      expect(RETRY_ATTEMPTS).toBeGreaterThan(-1);
      expect(Number.isInteger(RETRY_ATTEMPTS)).toBe(true);
    });

    it('should have jitter factor between 0 and 1', () => {
      expect(JITTER_FACTOR).toBeGreaterThan(0);
      expect(JITTER_FACTOR).toBeLessThanOrEqual(1);
      expect(typeof JITTER_FACTOR).toBe('number');
    });
  });

  describe('constant relationships', () => {
    it('should have consistent field name patterns', () => {
      const fieldNames = [
        DEFAULT_DATA_FIELD_NAME,
        DEFAULT_METADATA_FIELD_NAME,
        DEFAULT_DATA_TYPE_FIELD_NAME,
        DEFAULT_EMBEDDING_FIELD_NAME,
      ];

      fieldNames.forEach((fieldName) => {
        expect(fieldName).toMatch(/^[a-zA-Z_][a-zA-Z0-9_]*$/);
        expect(fieldName.length).toBeGreaterThan(0);
        expect(fieldName.length).toBeLessThan(100);
      });
    });

    it('should have unique field names', () => {
      const fieldNames = [
        DEFAULT_DATA_FIELD_NAME,
        DEFAULT_METADATA_FIELD_NAME,
        DEFAULT_DATA_TYPE_FIELD_NAME,
        DEFAULT_EMBEDDING_FIELD_NAME,
      ];

      const uniqueNames = new Set(fieldNames);
      expect(uniqueNames.size).toBe(fieldNames.length);
    });
  });
});
