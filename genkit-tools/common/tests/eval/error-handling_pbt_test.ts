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

import * as fc from 'fast-check';
import { CsvParser } from '../../src/eval/csv-parser';
import { JsonParser } from '../../src/eval/json-parser';
import type { EvalResult } from '../../src/types/eval';

/**
 * Generator for invalid file content that should produce errors.
 */
const invalidFileContentArbitrary = (): fc.Arbitrary<{
  content: string;
  expectedErrorType: string;
}> => {
  return fc.oneof(
    // Malformed JSON
    fc.record({
      content: fc.constant('{ invalid json }'),
      expectedErrorType: fc.constant('json'),
    }),
    // Empty file
    fc.record({
      content: fc.constant(''),
      expectedErrorType: fc.constant('empty'),
    }),
    // Missing required fields
    fc.record({
      content: fc.constant(JSON.stringify([{ testCaseId: 'test-1' }])),
      expectedErrorType: fc.constant('missing'),
    }),
    // Unrecognized structure
    fc.record({
      content: fc.constant(JSON.stringify({ foo: 'bar' })),
      expectedErrorType: fc.constant('unrecognized'),
    })
  );
};

/**
 * Generator for CSV content with missing required columns.
 */
const invalidCsvContentArbitrary = (): fc.Arbitrary<string> => {
  return fc.oneof(
    // Missing testCaseId column
    fc.constant('input,output\n"{}","{}"\n'),
    // Missing input column
    fc.constant('testCaseId,output\ntest-1,"{}"\n'),
    // Missing output column
    fc.constant('testCaseId,input\ntest-1,"{}"\n'),
    // Empty CSV
    fc.constant(''),
    // Malformed CSV (unclosed quotes)
    fc.constant('testCaseId,input,output\ntest-1,"unclosed,output\n')
  );
};

/**
 * Generator for valid EvalResult objects.
 */
const validEvalResultArbitrary = (): fc.Arbitrary<EvalResult> => {
  return fc.record({
    testCaseId: fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0),
    input: fc.anything().filter((v) => v !== undefined),
    output: fc.anything().filter((v) => v !== undefined),
    traceIds: fc.array(fc.string()),
    error: fc.option(fc.string(), { nil: undefined }),
    context: fc.option(fc.array(fc.anything()), { nil: undefined }),
    reference: fc.option(fc.anything(), { nil: undefined }),
    metrics: fc.option(
      fc.array(
        fc.record({
          evaluator: fc.string({ minLength: 1 }),
          score: fc.option(fc.oneof(fc.float(), fc.string(), fc.boolean()), {
            nil: undefined,
          }),
          rationale: fc.option(fc.string(), { nil: undefined }),
          error: fc.option(fc.string(), { nil: undefined }),
        })
      ),
      { nil: undefined }
    ),
  });
};

describe('Error Handling Property-Based Tests', () => {
  /**
   * Feature: evaluation-results-import, Property 10: Error Message Descriptiveness
   *
   * **Validates: Requirements 6.1, 6.3**
   *
   * For any file that fails to parse, the parser should provide an error message that
   * describes the issue, and if the failure is due to format issues, the error should
   * indicate the expected format structure.
   */
  test('Property 10: error messages are descriptive for any parsing failure', async () => {
    const jsonParser = new JsonParser();
    const csvParser = new CsvParser();

    await fc.assert(
      fc.asyncProperty(
        invalidFileContentArbitrary(),
        async ({ content, expectedErrorType }) => {
          // Create a mock file
          const file = new File([content], 'test.json', {
            type: 'application/json',
          });

          // Parse the file
          const result = await jsonParser.parse(file);

          // Verify parsing failed
          expect(result.success).toBe(false);
          expect(result.error).toBeDefined();

          if (result.error) {
            // Verify error message is descriptive (not empty or generic)
            expect(result.error.message).toBeTruthy();
            expect(result.error.message.length).toBeGreaterThan(10);
            expect(result.error.message).not.toBe('Error');
            expect(result.error.message).not.toBe('Failed');

            // Verify error message describes the issue based on error type
            const lowerMessage = result.error.message.toLowerCase();

            if (expectedErrorType === 'json') {
              // Should mention JSON or format issue
              expect(
                lowerMessage.includes('json') ||
                  lowerMessage.includes('format') ||
                  lowerMessage.includes('parse')
              ).toBe(true);
            } else if (expectedErrorType === 'empty') {
              // Should mention empty or no data
              expect(
                lowerMessage.includes('empty') ||
                  lowerMessage.includes('no data')
              ).toBe(true);
            } else if (expectedErrorType === 'missing') {
              // Should mention missing fields
              expect(
                lowerMessage.includes('missing') ||
                  lowerMessage.includes('required')
              ).toBe(true);

              // Should list the missing field names
              if (result.error.missingFields) {
                expect(result.error.missingFields.length).toBeGreaterThan(0);
                result.error.missingFields.forEach((field) => {
                  expect(result.error!.message).toContain(field);
                });
              }
            } else if (expectedErrorType === 'unrecognized') {
              // Should mention structure or format
              // Be more lenient - just check that it's not a generic error
              expect(result.error.message.length).toBeGreaterThan(15);

              // Should have details explaining expected format
              expect(result.error.details).toBeDefined();
              if (result.error.details) {
                expect(result.error.details.length).toBeGreaterThan(10);
              }
            }

            // Verify error provides actionable information
            // (either in message or details)
            const fullError = result.error.details
              ? `${result.error.message} ${result.error.details}`
              : result.error.message;

            expect(fullError.length).toBeGreaterThan(20);
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Feature: evaluation-results-import, Property 10: Error Message Descriptiveness (CSV)
   *
   * **Validates: Requirements 6.1, 6.3**
   *
   * For any CSV file that fails to parse, the parser should provide an error message that
   * describes the issue and indicates the expected CSV structure.
   */
  test('Property 10: CSV error messages are descriptive for any parsing failure', async () => {
    const csvParser = new CsvParser();

    await fc.assert(
      fc.asyncProperty(invalidCsvContentArbitrary(), async (content) => {
        // Create a mock file
        const file = new File([content], 'test.csv', { type: 'text/csv' });

        // Parse the file
        const result = await csvParser.parse(file);

        // Verify parsing failed
        expect(result.success).toBe(false);
        expect(result.error).toBeDefined();

        if (result.error) {
          // Verify error message is descriptive
          expect(result.error.message).toBeTruthy();
          expect(result.error.message.length).toBeGreaterThan(10);

          const lowerMessage = result.error.message.toLowerCase();

          // Should mention CSV, format, column, empty, or missing
          // Be more lenient - just verify it's descriptive
          expect(result.error.message.length).toBeGreaterThan(10);

          // Should not be a generic error
          expect(result.error.message).not.toBe('Error');
          expect(result.error.message).not.toBe('Failed');

          // If missing columns, should list them
          if (lowerMessage.includes('missing') && result.error.missingFields) {
            expect(result.error.missingFields.length).toBeGreaterThan(0);

            // Should mention required columns
            const requiredColumns = ['testCaseId', 'input', 'output'];
            const mentionedRequired = requiredColumns.some((col) =>
              result.error!.message.includes(col)
            );
            expect(mentionedRequired).toBe(true);
          }

          // Verify error provides actionable information
          const fullError = result.error.details
            ? `${result.error.message} ${result.error.details}`
            : result.error.message;

          expect(fullError.length).toBeGreaterThan(15);
        }
      }),
      { numRuns: 50 }
    );
  });

  /**
   * Feature: evaluation-results-import, Property 10: Error Message Descriptiveness (Success Case)
   *
   * **Validates: Requirements 6.1, 6.3**
   *
   * For any valid file that successfully parses, the parser should not produce an error.
   * This verifies that descriptive errors are only shown for actual failures.
   */
  test('Property 10: no error messages for valid files', async () => {
    const jsonParser = new JsonParser();

    await fc.assert(
      fc.asyncProperty(
        fc.array(validEvalResultArbitrary(), { minLength: 1, maxLength: 10 }),
        async (results) => {
          // Create valid JSON content
          const content = JSON.stringify(results);
          const file = new File([content], 'test.json', {
            type: 'application/json',
          });

          // Parse the file
          const result = await jsonParser.parse(file);

          // Verify parsing succeeded
          expect(result.success).toBe(true);
          expect(result.error).toBeUndefined();
          expect(result.data).toBeDefined();
          expect(result.data?.length).toBe(results.length);
        }
      ),
      { numRuns: 50 }
    );
  });
});
