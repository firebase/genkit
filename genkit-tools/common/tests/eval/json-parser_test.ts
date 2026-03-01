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

import { beforeEach, describe, expect, it } from '@jest/globals';
import * as fc from 'fast-check';
import { JsonParser } from '../../src/eval/json-parser';
import type { EvalMetric, EvalResult, EvalRun } from '../../src/types/eval';

// Polyfill for File API in Node.js test environment
class FilePolyfill {
  private content: string;
  public name: string;
  public type: string;

  constructor(parts: any[], name: string, options?: { type?: string }) {
    this.content = parts.join('');
    this.name = name;
    this.type = options?.type || '';
  }

  text(): Promise<string> {
    return Promise.resolve(this.content);
  }
}

// @ts-ignore - Override global File for tests
global.File = FilePolyfill as any;
global.FileReader = class FileReader {
  onload: ((event: any) => void) | null = null;
  onerror: (() => void) | null = null;
  result: string | ArrayBuffer | null = null;

  readAsText(file: any) {
    file.text().then((text: string) => {
      this.result = text;
      if (this.onload) {
        this.onload({ target: { result: text } });
      }
    });
  }
} as any;

describe('JsonParser', () => {
  let parser: JsonParser;

  beforeEach(() => {
    parser = new JsonParser();
  });

  describe('required field validation', () => {
    it('should accept evaluation results with all required fields', async () => {
      const validData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const file = createJsonFile(validData);
      const result = await parser.parse(file);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(validData);
      expect(result.error).toBeUndefined();
    });

    it('should reject evaluation results missing testCaseId', async () => {
      const invalidData = [
        {
          // testCaseId is missing
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const file = createJsonFile(invalidData);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('testCaseId');
      expect(result.error?.details).toContain('Result at index 0');
      expect(result.error?.details).toContain('testCaseId');
      expect(result.error?.missingFields).toEqual(['testCaseId']);
    });

    it('should reject evaluation results missing input', async () => {
      const invalidData = [
        {
          testCaseId: 'test-1',
          // input is missing
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const file = createJsonFile(invalidData);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('input');
      expect(result.error?.details).toContain('Result at index 0');
      expect(result.error?.details).toContain('input');
      expect(result.error?.missingFields).toEqual(['input']);
    });

    it('should reject evaluation results missing output', async () => {
      const invalidData = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          // output is missing
          traceIds: [],
        },
      ];

      const file = createJsonFile(invalidData);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('output');
      expect(result.error?.details).toContain('Result at index 0');
      expect(result.error?.details).toContain('output');
      expect(result.error?.missingFields).toEqual(['output']);
    });

    it('should list all missing required fields in error message', async () => {
      const invalidData = [
        {
          // testCaseId is missing
          // input is missing
          // output is missing
          traceIds: [],
        },
      ];

      const file = createJsonFile(invalidData);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('testCaseId');
      expect(result.error?.message).toContain('input');
      expect(result.error?.message).toContain('output');
      expect(result.error?.details).toContain('Result at index 0');
      expect(result.error?.details).toContain('testCaseId');
      expect(result.error?.details).toContain('input');
      expect(result.error?.details).toContain('output');
      expect(result.error?.missingFields).toContain('testCaseId');
      expect(result.error?.missingFields).toContain('input');
      expect(result.error?.missingFields).toContain('output');
      expect(result.error?.missingFields?.length).toBe(3);
    });

    it('should validate all results in array and report first invalid one', async () => {
      const mixedData = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
        {
          testCaseId: 'test-2',
          // input is missing
          output: { response: 'bye' },
          traceIds: [],
        },
        {
          testCaseId: 'test-3',
          input: { query: 'goodbye' },
          output: { response: 'bye' },
          traceIds: [],
        },
      ];

      const file = createJsonFile(mixedData);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('input');
      expect(result.error?.details).toContain('Result at index 1');
      expect(result.error?.missingFields).toEqual(['input']);
    });

    it('should accept null values as valid (not missing)', async () => {
      const dataWithNull: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: null,
          output: null,
          traceIds: [],
        },
      ];

      const file = createJsonFile(dataWithNull);
      const result = await parser.parse(file);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(dataWithNull);
    });

    it('should work with EvalRun wrapper structure', async () => {
      const evalRun: EvalRun = {
        key: {
          evalRunId: 'run-123',
          createdAt: '2024-01-15T10:30:00Z',
        },
        results: [
          {
            testCaseId: 'test-1',
            input: { query: 'hello' },
            output: { response: 'hi' },
            traceIds: [],
          },
        ],
      };

      const file = createJsonFile(evalRun);
      const result = await parser.parse(file);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(evalRun.results);
      expect(result.metadata).toEqual(evalRun.key);
    });

    it('should validate results within EvalRun wrapper', async () => {
      const evalRun = {
        key: {
          evalRunId: 'run-123',
          createdAt: '2024-01-15T10:30:00Z',
        },
        results: [
          {
            testCaseId: 'test-1',
            // input is missing
            output: { response: 'hi' },
            traceIds: [],
          },
        ],
      };

      const file = createJsonFile(evalRun);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('input');
      expect(result.error?.missingFields).toEqual(['input']);
    });
  });

  describe('other validation scenarios', () => {
    it('should reject empty file', async () => {
      const file = new File([''], 'test.json', { type: 'application/json' });
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('File contains no data');
    });

    it('should reject malformed JSON', async () => {
      const file = new File(['{ invalid json }'], 'test.json', {
        type: 'application/json',
      });
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Invalid JSON format');
    });

    it('should reject empty results array by default', async () => {
      const file = createJsonFile([]);
      const result = await parser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('no evaluation results');
    });

    it('should allow empty results array when configured', async () => {
      const file = createJsonFile([]);
      const result = await parser.parse(file, { allowEmpty: true });

      expect(result.success).toBe(true);
      expect(result.data).toEqual([]);
    });

    it('should skip validation when configured', async () => {
      const invalidData = [
        {
          // All required fields missing
          traceIds: [],
        },
      ];

      const file = createJsonFile(invalidData);
      const result = await parser.parse(file, {
        validateRequiredFields: false,
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual(invalidData);
    });

    it('should support custom required fields', async () => {
      const data = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          // reference is missing
          traceIds: [],
        },
      ];

      const file = createJsonFile(data);
      const result = await parser.parse(file, {
        requiredFields: ['testCaseId', 'input', 'output', 'reference'],
      });

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.message).toContain('reference');
      expect(result.error?.missingFields).toEqual(['reference']);
    });
  });
});

describe('Property-Based Tests', () => {
  let parser: JsonParser;

  beforeEach(() => {
    parser = new JsonParser();
  });

  /**
   * Feature: evaluation-results-import, Property 2: JSON Format Flexibility
   *
   * **Validates: Requirements 2.2, 2.3**
   *
   * For any valid JSON file containing either an EvalRun structure or a raw array
   * of EvalResult objects, the JSON parser should successfully extract the evaluation results.
   */
  it('Property 2: JSON Format Flexibility - should parse both EvalRun wrapper and raw array formats', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate random EvalResult arrays
        fc.array(generateEvalResult(), { minLength: 1, maxLength: 10 }),
        async (evalResults) => {
          // Test 1: Parse as raw array
          const rawArrayFile = createJsonFile(evalResults);
          const rawArrayResult = await parser.parse(rawArrayFile);

          expect(rawArrayResult.success).toBe(true);
          // Compare after JSON round-trip to account for undefined -> null conversion
          expect(rawArrayResult.data).toEqual(
            JSON.parse(JSON.stringify(evalResults))
          );
          expect(rawArrayResult.metadata).toBeUndefined();

          // Test 2: Parse as EvalRun wrapper
          const evalRun: EvalRun = {
            key: {
              evalRunId: fc.sample(fc.uuid(), 1)[0],
              createdAt: new Date().toISOString(),
              actionRef: fc.sample(
                fc.option(fc.string(), { nil: undefined }),
                1
              )[0],
              datasetId: fc.sample(
                fc.option(fc.string(), { nil: undefined }),
                1
              )[0],
            },
            results: evalResults,
          };

          const evalRunFile = createJsonFile(evalRun);
          const evalRunResult = await parser.parse(evalRunFile);

          expect(evalRunResult.success).toBe(true);
          // Compare after JSON round-trip to account for undefined -> null conversion
          expect(evalRunResult.data).toEqual(
            JSON.parse(JSON.stringify(evalResults))
          );
          // Metadata should match after JSON round-trip
          expect(evalRunResult.metadata).toEqual(
            JSON.parse(JSON.stringify(evalRun.key))
          );
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Feature: evaluation-results-import, Property 3: Required Field Validation
   *
   * **Validates: Requirements 2.5, 6.2**
   *
   * For any evaluation result in an uploaded file, if it is missing required fields
   * (testCaseId, input, or output), the parser should reject it and list the missing
   * field names in the error message.
   */
  it('Property 3: Required Field Validation - should reject results with missing required fields', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate evaluation results with at least one missing required field
        generateEvalResultWithMissingFields(),
        async ({ result, missingFields }) => {
          // Create a file with the invalid result
          const file = createJsonFile([result]);
          const parseResult = await parser.parse(file);

          // Parser should reject the result
          expect(parseResult.success).toBe(false);
          expect(parseResult.error).toBeDefined();

          // Error message should mention missing fields
          expect(parseResult.error?.message).toContain(
            'Missing required fields'
          );

          // Error message should list all missing fields
          missingFields.forEach((field) => {
            expect(parseResult.error?.message).toContain(field);
          });

          // missingFields array should contain all missing fields
          expect(parseResult.error?.missingFields).toBeDefined();
          expect(parseResult.error?.missingFields?.sort()).toEqual(
            missingFields.sort()
          );

          // Details should indicate which result has the issue
          expect(parseResult.error?.details).toContain('Result at index 0');
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Fast-check arbitrary generator for EvalMetric
 */
function generateEvalMetric(): fc.Arbitrary<EvalMetric> {
  return fc.record({
    evaluator: fc.string({ minLength: 1 }),
    scoreId: fc.option(fc.string(), { nil: undefined }),
    score: fc.option(
      fc.oneof(
        fc.double({ min: 0, max: 1, noNaN: true }),
        fc.string(),
        fc.boolean()
      ),
      { nil: undefined }
    ),
    status: fc.option(fc.constantFrom('UNKNOWN', 'PASS', 'FAIL'), {
      nil: undefined,
    }),
    rationale: fc.option(fc.string(), { nil: undefined }),
    error: fc.option(fc.string(), { nil: undefined }),
    traceId: fc.option(fc.uuid(), { nil: undefined }),
    spanId: fc.option(fc.uuid(), { nil: undefined }),
  });
}

/**
 * Fast-check arbitrary generator for EvalResult
 */
function generateEvalResult(): fc.Arbitrary<EvalResult> {
  return fc.record({
    testCaseId: fc.string({ minLength: 1 }),
    input: fc.oneof(fc.string(), fc.object(), fc.constant(null)),
    output: fc.oneof(fc.string(), fc.object(), fc.constant(null)),
    error: fc.option(fc.string(), { nil: undefined }),
    context: fc.option(fc.array(fc.anything()), { nil: undefined }),
    reference: fc.option(
      fc.oneof(fc.string(), fc.object(), fc.constant(null)),
      { nil: undefined }
    ),
    traceIds: fc.array(fc.uuid()),
    metrics: fc.option(fc.array(generateEvalMetric(), { maxLength: 5 }), {
      nil: undefined,
    }),
  });
}

/**
 * Fast-check arbitrary generator for EvalResult with missing required fields.
 * Generates an evaluation result that is missing at least one required field
 * (testCaseId, input, or output) and returns both the result and the list of
 * missing fields.
 */
function generateEvalResultWithMissingFields(): fc.Arbitrary<{
  result: any;
  missingFields: string[];
}> {
  return fc
    .record({
      // Generate which fields to omit (at least one)
      omitTestCaseId: fc.boolean(),
      omitInput: fc.boolean(),
      omitOutput: fc.boolean(),
      // Generate optional fields
      error: fc.option(fc.string(), { nil: undefined }),
      context: fc.option(fc.array(fc.anything()), { nil: undefined }),
      reference: fc.option(
        fc.oneof(fc.string(), fc.object(), fc.constant(null)),
        { nil: undefined }
      ),
      traceIds: fc.array(fc.uuid()),
      metrics: fc.option(fc.array(generateEvalMetric(), { maxLength: 5 }), {
        nil: undefined,
      }),
    })
    .filter(
      // Ensure at least one required field is omitted
      (config) => config.omitTestCaseId || config.omitInput || config.omitOutput
    )
    .map((config) => {
      const result: any = {};
      const missingFields: string[] = [];

      // Add or omit required fields based on configuration
      if (!config.omitTestCaseId) {
        result.testCaseId = fc.sample(fc.string({ minLength: 1 }), 1)[0];
      } else {
        missingFields.push('testCaseId');
      }

      if (!config.omitInput) {
        result.input = fc.sample(
          fc.oneof(fc.string(), fc.object(), fc.constant(null)),
          1
        )[0];
      } else {
        missingFields.push('input');
      }

      if (!config.omitOutput) {
        result.output = fc.sample(
          fc.oneof(fc.string(), fc.object(), fc.constant(null)),
          1
        )[0];
      } else {
        missingFields.push('output');
      }

      // Add optional fields
      if (config.error !== undefined) result.error = config.error;
      if (config.context !== undefined) result.context = config.context;
      if (config.reference !== undefined) result.reference = config.reference;
      result.traceIds = config.traceIds;
      if (config.metrics !== undefined) result.metrics = config.metrics;

      return { result, missingFields };
    });
}

/**
 * Helper function to create a File object from JSON data
 */
function createJsonFile(data: any): File {
  const json = JSON.stringify(data);
  return new File([json], 'test.json', { type: 'application/json' });
}
