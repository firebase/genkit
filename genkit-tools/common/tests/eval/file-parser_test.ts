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

import {
  createErrorResult,
  createParseError,
  createSuccessResult,
  validateRequiredFields,
  type ParseError,
  type ParseResult,
} from '../../src/eval/file-parser';
import type { EvalResult } from '../../src/types/eval';

describe('file-parser', () => {
  describe('validateRequiredFields', () => {
    it('should return empty array when all required fields are present', () => {
      const result = {
        testCaseId: 'test-1',
        input: { query: 'hello' },
        output: { response: 'hi' },
        traceIds: [],
      };

      const missing = validateRequiredFields(result);
      expect(missing).toEqual([]);
    });

    it('should return missing field names when required fields are absent', () => {
      const result = {
        testCaseId: 'test-1',
        input: { query: 'hello' },
        // output is missing
        traceIds: [],
      };

      const missing = validateRequiredFields(result);
      expect(missing).toEqual(['output']);
    });

    it('should check multiple missing fields', () => {
      const result = {
        // testCaseId is missing
        // input is missing
        output: { response: 'hi' },
        traceIds: [],
      };

      const missing = validateRequiredFields(result);
      expect(missing).toContain('testCaseId');
      expect(missing).toContain('input');
      expect(missing.length).toBe(2);
    });

    it('should support custom required fields', () => {
      const result = {
        testCaseId: 'test-1',
        input: { query: 'hello' },
        output: { response: 'hi' },
        // reference is missing
      };

      const missing = validateRequiredFields(result, [
        'testCaseId',
        'input',
        'output',
        'reference',
      ]);
      expect(missing).toEqual(['reference']);
    });

    it('should treat undefined as missing but not null', () => {
      const result = {
        testCaseId: 'test-1',
        input: null,
        output: { response: 'hi' },
      };

      const missing = validateRequiredFields(result);
      expect(missing).toEqual([]);
    });
  });

  describe('createParseError', () => {
    it('should create error with message only', () => {
      const error = createParseError('Invalid file format');

      expect(error.message).toBe('Invalid file format');
      expect(error.details).toBeUndefined();
      expect(error.missingFields).toBeUndefined();
    });

    it('should create error with message and details', () => {
      const error = createParseError(
        'Invalid JSON',
        'Unexpected token at line 5'
      );

      expect(error.message).toBe('Invalid JSON');
      expect(error.details).toBe('Unexpected token at line 5');
      expect(error.missingFields).toBeUndefined();
    });

    it('should create error with missing fields', () => {
      const error = createParseError('Missing required fields', undefined, [
        'testCaseId',
        'input',
      ]);

      expect(error.message).toBe('Missing required fields');
      expect(error.details).toBeUndefined();
      expect(error.missingFields).toEqual(['testCaseId', 'input']);
    });

    it('should create error with all parameters', () => {
      const error = createParseError('Validation failed', 'Row 3 is invalid', [
        'output',
      ]);

      expect(error.message).toBe('Validation failed');
      expect(error.details).toBe('Row 3 is invalid');
      expect(error.missingFields).toEqual(['output']);
    });
  });

  describe('createSuccessResult', () => {
    it('should create success result with data only', () => {
      const data: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const result = createSuccessResult(data);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(data);
      expect(result.metadata).toBeUndefined();
      expect(result.error).toBeUndefined();
    });

    it('should create success result with data and metadata', () => {
      const data: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];
      const metadata = {
        evalRunId: 'run-123',
        createdAt: '2024-01-15T10:30:00Z',
        actionRef: 'myAction',
      };

      const result = createSuccessResult(data, metadata);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(data);
      expect(result.metadata).toEqual(metadata);
      expect(result.error).toBeUndefined();
    });

    it('should handle empty data array', () => {
      const data: EvalResult[] = [];

      const result = createSuccessResult(data);

      expect(result.success).toBe(true);
      expect(result.data).toEqual([]);
      expect(result.metadata).toBeUndefined();
    });
  });

  describe('createErrorResult', () => {
    it('should create error result', () => {
      const error: ParseError = {
        message: 'File is empty',
        details: 'No data found in file',
      };

      const result = createErrorResult(error);

      expect(result.success).toBe(false);
      expect(result.error).toEqual(error);
      expect(result.data).toBeUndefined();
      expect(result.metadata).toBeUndefined();
    });

    it('should create error result with missing fields', () => {
      const error: ParseError = {
        message: 'Invalid data',
        missingFields: ['testCaseId', 'output'],
      };

      const result = createErrorResult(error);

      expect(result.success).toBe(false);
      expect(result.error).toEqual(error);
      expect(result.error?.missingFields).toEqual(['testCaseId', 'output']);
    });
  });

  describe('ParseResult type checking', () => {
    it('should allow success result with data', () => {
      const result: ParseResult = {
        success: true,
        data: [
          {
            testCaseId: 'test-1',
            input: {},
            output: {},
            traceIds: [],
          },
        ],
      };

      expect(result.success).toBe(true);
    });

    it('should allow error result', () => {
      const result: ParseResult = {
        success: false,
        error: {
          message: 'Error occurred',
        },
      };

      expect(result.success).toBe(false);
    });
  });
});
