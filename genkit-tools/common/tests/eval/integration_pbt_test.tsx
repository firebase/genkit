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
import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import * as fc from 'fast-check';
import React from 'react';
import { EvaluationPage } from '../../src/eval/evaluation-page';

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

/**
 * Generator for EvalResult objects.
 */
const evalResultArbitrary = fc.record({
  testCaseId: fc.string({ minLength: 1, maxLength: 50 }),
  input: fc.jsonValue(),
  output: fc.jsonValue(),
  reference: fc.option(fc.jsonValue(), { nil: undefined }),
  error: fc.option(fc.string(), { nil: undefined }),
  context: fc.option(fc.array(fc.jsonValue()), { nil: undefined }),
  traceIds: fc.array(fc.string({ minLength: 1, maxLength: 20 }), {
    maxLength: 5,
  }),
  metrics: fc.option(
    fc.array(
      fc.record({
        evaluator: fc.string({ minLength: 1, maxLength: 30 }),
        score: fc.option(
          fc.oneof(fc.double({ min: 0, max: 1 }), fc.string(), fc.boolean()),
          { nil: undefined }
        ),
        rationale: fc.option(fc.string(), { nil: undefined }),
        error: fc.option(fc.string(), { nil: undefined }),
      }),
      { maxLength: 5 }
    ),
    { nil: undefined }
  ),
});

/**
 * Generator for EvalRunKey metadata.
 */
const evalRunKeyArbitrary = fc.record({
  evalRunId: fc.string({ minLength: 1, maxLength: 50 }),
  createdAt: fc
    .integer({ min: Date.parse('2020-01-01'), max: Date.parse('2030-12-31') })
    .map((ts) => new Date(ts).toISOString()),
  actionRef: fc.option(fc.string({ minLength: 1, maxLength: 50 }), {
    nil: undefined,
  }),
  datasetId: fc.option(fc.string({ minLength: 1, maxLength: 50 }), {
    nil: undefined,
  }),
  datasetVersion: fc.option(fc.integer({ min: 1, max: 100 }), {
    nil: undefined,
  }),
});

/**
 * Generator for file names.
 */
const filenameArbitrary = fc
  .string({ minLength: 1, maxLength: 30 })
  .map((s) => s.replace(/[^a-zA-Z0-9_-]/g, '') + '.json');

describe('Property-Based Tests - Integration', () => {
  /**
   * Feature: evaluation-results-import, Property 11: File Replacement
   *
   * **Validates: Requirements 7.1**
   *
   * For any new file upload while viewing imported data, the Developer_UI should replace
   * the currently displayed evaluation data with the new file's data.
   */
  it('Property 11: File Replacement - new file replaces current data', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.tuple(
          fc.array(evalResultArbitrary, { minLength: 1, maxLength: 3 }),
          fc.array(evalResultArbitrary, { minLength: 1, maxLength: 3 }),
          filenameArbitrary,
          filenameArbitrary
        ),
        async ([firstData, secondData, firstName, secondName]) => {
          // Ensure filenames are different
          if (firstName === secondName) {
            secondName = 'different_' + secondName;
          }

          // Ensure test case IDs are unique and simple for verification
          firstData = firstData.map((result, i) => ({
            ...result,
            testCaseId: `first-file-test-${i}`,
          }));
          secondData = secondData.map((result, i) => ({
            ...result,
            testCaseId: `second-file-test-${i}`,
          }));

          // Render the evaluation page
          const { unmount } = render(<EvaluationPage />);

          try {
            // Upload first file
            const firstFile = new File([JSON.stringify(firstData)], firstName, {
              type: 'application/json',
            });

            const fileInput = screen.getByTestId(
              'file-input'
            ) as HTMLInputElement;
            Object.defineProperty(fileInput, 'files', {
              value: [firstFile],
              writable: false,
              configurable: true,
            });

            fireEvent.change(fileInput);

            // Wait for first file to be displayed
            await waitFor(
              () => {
                expect(
                  screen.getByTestId('current-filename')
                ).toHaveTextContent(firstName);
              },
              { timeout: 3000 }
            );

            // Verify first file data is displayed
            const firstTestCaseId = firstData[0].testCaseId;
            expect(
              screen.getByText(new RegExp(firstTestCaseId))
            ).toBeInTheDocument();

            // Upload second file
            const secondFile = new File(
              [JSON.stringify(secondData)],
              secondName,
              {
                type: 'application/json',
              }
            );

            Object.defineProperty(fileInput, 'files', {
              value: [secondFile],
              writable: false,
              configurable: true,
            });

            fireEvent.change(fileInput);

            // Wait for second file to be displayed
            await waitFor(
              () => {
                expect(
                  screen.getByTestId('current-filename')
                ).toHaveTextContent(secondName);
              },
              { timeout: 3000 }
            );

            // Wait a bit for the UI to update
            await waitFor(
              () => {
                const resultItems = screen.queryAllByTestId('result-item');
                expect(resultItems.length).toBeGreaterThan(0);
              },
              { timeout: 3000 }
            );

            // Verify second file data is displayed
            const secondTestCaseId = secondData[0].testCaseId;
            await waitFor(
              () => {
                expect(
                  screen.getByText(new RegExp(secondTestCaseId))
                ).toBeInTheDocument();
              },
              { timeout: 3000 }
            );

            // Verify first file data is NOT displayed (replaced)
            expect(
              screen.queryByText(new RegExp(firstTestCaseId))
            ).not.toBeInTheDocument();

            // Verify the number of results matches second file
            const resultItems = screen.getAllByTestId('result-item');
            expect(resultItems).toHaveLength(secondData.length);
          } finally {
            unmount();
          }
        }
      ),
      { numRuns: 100 }
    );
  }, 60000); // Increase timeout for property-based test

  /**
   * Feature: evaluation-results-import, Property 12: Current File Indication
   *
   * **Validates: Requirements 7.3**
   *
   * For any imported evaluation data being viewed, the Developer_UI should display
   * the filename of the currently viewed file.
   */
  it('Property 12: Current File Indication - displays current filename', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.tuple(
          fc.array(evalResultArbitrary, { minLength: 1, maxLength: 3 }),
          filenameArbitrary
        ),
        async ([data, filename]) => {
          // Render the evaluation page
          const { unmount } = render(<EvaluationPage />);

          try {
            // Upload file
            const file = new File([JSON.stringify(data)], filename, {
              type: 'application/json',
            });

            const fileInput = screen.getByTestId(
              'file-input'
            ) as HTMLInputElement;
            Object.defineProperty(fileInput, 'files', {
              value: [file],
              writable: false,
            });

            fireEvent.change(fileInput);

            // Wait for file to be displayed
            await waitFor(
              () => {
                expect(
                  screen.getByTestId('import-mode-banner')
                ).toBeInTheDocument();
              },
              { timeout: 3000 }
            );

            // Verify filename is displayed
            const filenameElement = screen.getByTestId('current-filename');
            expect(filenameElement).toBeInTheDocument();
            expect(filenameElement).toHaveTextContent(filename);

            // Verify import badge is displayed
            expect(screen.getByTestId('import-badge')).toBeInTheDocument();
          } finally {
            unmount();
          }
        }
      ),
      { numRuns: 100 }
    );
  }, 60000); // Increase timeout for property-based test

  /**
   * Feature: evaluation-results-import, Property 14: Timestamp Formatting
   *
   * **Validates: Requirements 8.4**
   *
   * For any imported evaluation data with a createdAt timestamp, the Evaluation_Viewer
   * should display it in a human-readable format (not as a raw ISO string or Unix timestamp).
   */
  it('Property 14: Timestamp Formatting - displays human-readable timestamps', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.tuple(
          fc.array(evalResultArbitrary, { minLength: 1, maxLength: 2 }),
          evalRunKeyArbitrary,
          filenameArbitrary
        ),
        async ([data, metadata, filename]) => {
          // Create EvalRun with metadata
          const evalRun = {
            key: metadata,
            results: data,
          };

          // Render the evaluation page
          const { unmount } = render(<EvaluationPage />);

          try {
            // Upload file with metadata
            const file = new File([JSON.stringify(evalRun)], filename, {
              type: 'application/json',
            });

            const fileInput = screen.getByTestId(
              'file-input'
            ) as HTMLInputElement;
            Object.defineProperty(fileInput, 'files', {
              value: [file],
              writable: false,
            });

            fireEvent.change(fileInput);

            // Wait for file to be displayed
            await waitFor(
              () => {
                expect(
                  screen.getByTestId('metadata-display')
                ).toBeInTheDocument();
              },
              { timeout: 3000 }
            );

            // Verify timestamp is displayed
            const createdAtElement = screen.getByTestId('created-at');
            expect(createdAtElement).toBeInTheDocument();

            const displayedText = createdAtElement.textContent || '';

            // Verify it's NOT a raw ISO string (should not contain 'T' and 'Z' together)
            // Human-readable format should have spaces and commas
            const isHumanReadable =
              displayedText.includes(',') || // Has comma separator
              (displayedText.includes(' ') && !displayedText.includes('T')); // Has spaces but not ISO format

            // Also verify it's not a Unix timestamp (all digits)
            const isNotUnixTimestamp = !/^\d+$/.test(
              displayedText.replace(/[^0-9]/g, '')
            );

            expect(isHumanReadable || isNotUnixTimestamp).toBe(true);

            // Verify the timestamp contains some expected date components
            // (month, day, year, or time components)
            const hasDateComponents =
              /\d{1,2}/.test(displayedText) && // Has numbers (day/month/year)
              (/Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/.test(
                displayedText
              ) || // Has month name
                /\d{4}/.test(displayedText)); // Or has year

            expect(hasDateComponents).toBe(true);
          } finally {
            unmount();
          }
        }
      ),
      { numRuns: 100 }
    );
  }, 60000); // Increase timeout for property-based test
});
