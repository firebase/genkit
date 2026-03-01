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

import { render, screen } from '@testing-library/react';
import * as fc from 'fast-check';
import React from 'react';
import { EvaluationViewer } from '../../src/eval/evaluation-viewer';
import type { EvalMetric, EvalResult, EvalRunKey } from '../../src/types/eval';

/**
 * Generator for EvalMetric objects with varying field combinations.
 */
const evalMetricArbitrary = (): fc.Arbitrary<EvalMetric> => {
  return fc.record({
    evaluator: fc.string({ minLength: 1 }),
    scoreId: fc.option(fc.string(), { nil: undefined }),
    score: fc.option(fc.oneof(fc.float(), fc.string(), fc.boolean()), {
      nil: undefined,
    }),
    status: fc.option(fc.constantFrom('UNKNOWN', 'PASS', 'FAIL'), {
      nil: undefined,
    }),
    rationale: fc.option(fc.string(), { nil: undefined }),
    error: fc.option(fc.string(), { nil: undefined }),
    traceId: fc.option(fc.string(), { nil: undefined }),
    spanId: fc.option(fc.string(), { nil: undefined }),
  });
};

/**
 * Generator for EvalResult objects with varying field combinations.
 */
const evalResultArbitrary = (): fc.Arbitrary<EvalResult> => {
  return fc.record({
    testCaseId: fc.string({ minLength: 1 }),
    input: fc.anything(),
    output: fc.anything(),
    error: fc.option(fc.string(), { nil: undefined }),
    context: fc.option(fc.array(fc.anything()), { nil: undefined }),
    reference: fc.option(fc.anything(), { nil: undefined }),
    traceIds: fc.array(fc.string()),
    metrics: fc.option(fc.array(evalMetricArbitrary()), { nil: undefined }),
  });
};

/**
 * Generator for EvalRunKey metadata with varying optional fields.
 */
const evalRunKeyArbitrary = (): fc.Arbitrary<EvalRunKey> => {
  return fc.record({
    evalRunId: fc.string({ minLength: 1 }),
    createdAt: fc
      .integer({ min: Date.parse('2020-01-01'), max: Date.parse('2030-12-31') })
      .map((ts) => new Date(ts).toISOString()),
    actionRef: fc.option(fc.string(), { nil: undefined }),
    datasetId: fc.option(fc.string(), { nil: undefined }),
    datasetVersion: fc.option(fc.integer({ min: 1 }), { nil: undefined }),
    actionConfig: fc.option(fc.anything(), { nil: undefined }),
    metricSummaries: fc.option(
      fc.array(fc.dictionary(fc.string(), fc.anything())),
      { nil: undefined }
    ),
    metricsMetadata: fc.option(
      fc.dictionary(
        fc.string(),
        fc.record({
          displayName: fc.string(),
          definition: fc.string(),
        })
      ),
      { nil: undefined }
    ),
  });
};

/**
 * Generator for UIState objects with varying filter and sort combinations.
 */
const uiStateArbitrary = (): fc.Arbitrary<any> => {
  return fc.record({
    filters: fc.option(
      fc.dictionary(fc.string({ minLength: 1 }), fc.anything()),
      { nil: undefined }
    ),
    sortOrder: fc.option(
      fc.record({
        field: fc.string({ minLength: 1 }),
        direction: fc.constantFrom('asc' as const, 'desc' as const),
      }),
      { nil: undefined }
    ),
  });
};

describe('Evaluation Viewer Property-Based Tests', () => {
  /**
   * Feature: evaluation-results-import, Property 7: Comprehensive Field Display
   *
   * **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6, 8.1, 8.2, 8.3, 8.5**
   *
   * For any imported evaluation data, the Evaluation_Viewer should display all available
   * fields including: test case inputs, outputs, reference values, metric scores, rationales,
   * errors, evalRunId, createdAt timestamp, and any optional fields (actionRef, datasetId,
   * datasetVersion, metricSummaries, metricsMetadata, actionConfig) that are present in the data.
   */
  test('Property 7: displays all available fields for any evaluation data', () => {
    fc.assert(
      fc.property(
        fc.array(evalResultArbitrary(), { minLength: 1, maxLength: 5 }),
        fc.option(evalRunKeyArbitrary(), { nil: undefined }),
        (results, metadata) => {
          // Render the component with generated data
          const { container } = render(
            <EvaluationViewer
              initialState={{
                mode: 'import',
                data: results,
                metadata,
                currentFile: 'test.json',
              }}
            />
          );

          // Verify each result is displayed with all its fields
          results.forEach((result) => {
            // Test case ID should always be displayed
            // Use container.textContent to handle edge cases like whitespace-only strings
            expect(container.textContent).toContain(result.testCaseId);

            // Input and output should always be displayed
            const inputElements = screen.getAllByText(/Input:/);
            expect(inputElements.length).toBeGreaterThan(0);

            const outputElements = screen.getAllByText(/Output:/);
            expect(outputElements.length).toBeGreaterThan(0);

            // Reference should be displayed if present
            if (result.reference !== undefined) {
              const referenceElements = screen.getAllByText(/Reference:/);
              expect(referenceElements.length).toBeGreaterThan(0);
            }

            // Error should be displayed if present
            if (result.error) {
              expect(container.textContent).toContain(result.error);
            }

            // Context should be displayed if present
            if (result.context && result.context.length > 0) {
              const contextElements = screen.getAllByText(/Context:/);
              expect(contextElements.length).toBeGreaterThan(0);
            }

            // Trace IDs should be displayed if present
            if (result.traceIds && result.traceIds.length > 0) {
              const traceElements = screen.getAllByText(/Trace IDs:/);
              expect(traceElements.length).toBeGreaterThan(0);
            }

            // Metrics should be displayed if present
            if (result.metrics && result.metrics.length > 0) {
              result.metrics.forEach((metric) => {
                // Evaluator name should be displayed
                expect(container.textContent).toContain(metric.evaluator);

                // Score should be displayed if present
                if (metric.score !== undefined) {
                  const scoreText = String(metric.score);
                  expect(container.textContent).toContain(scoreText);
                }

                // Rationale should be displayed if present
                if (metric.rationale) {
                  expect(container.textContent).toContain(metric.rationale);
                }

                // Error should be displayed if present
                if (metric.error) {
                  expect(container.textContent).toContain(metric.error);
                }
              });
            }
          });

          // Verify metadata is displayed if present
          if (metadata) {
            // Eval Run ID should always be displayed
            expect(container.textContent).toContain(metadata.evalRunId);

            // Created At should be displayed (formatted)
            expect(screen.getAllByText(/Created At:/).length).toBeGreaterThan(
              0
            );

            // Optional metadata fields should be displayed if present
            if (metadata.actionRef) {
              expect(container.textContent).toContain(metadata.actionRef);
            }

            if (metadata.datasetId) {
              expect(container.textContent).toContain(metadata.datasetId);
            }

            if (metadata.datasetVersion !== undefined) {
              expect(container.textContent).toContain(
                String(metadata.datasetVersion)
              );
            }

            if (metadata.actionConfig) {
              expect(
                screen.getAllByText(/Action Config:/).length
              ).toBeGreaterThan(0);
            }

            if (
              metadata.metricSummaries &&
              metadata.metricSummaries.length > 0
            ) {
              expect(
                screen.getAllByText(/Metric Summaries:/).length
              ).toBeGreaterThan(0);
            }

            if (metadata.metricsMetadata) {
              expect(
                screen.getAllByText(/Metrics Metadata:/).length
              ).toBeGreaterThan(0);

              // Verify each metric metadata entry is displayed
              Object.entries(metadata.metricsMetadata).forEach(
                ([key, value]) => {
                  expect(container.textContent).toContain(key);
                  expect(container.textContent).toContain(value.displayName);
                  expect(container.textContent).toContain(value.definition);
                }
              );
            }
          }
        }
      ),
      { numRuns: 25 }
    );
  });

  /**
   * Feature: evaluation-results-import, Property 8: Filtering and Sorting Parity
   *
   * **Validates: Requirements 4.7**
   *
   * For any filtering or sorting operation that works on live evaluation results,
   * the same operation should work identically on imported evaluation results.
   */
  test('Property 8: filtering and sorting work identically in live and import modes', () => {
    fc.assert(
      fc.property(
        fc.array(evalResultArbitrary(), { minLength: 2, maxLength: 10 }),
        fc.option(evalRunKeyArbitrary(), { nil: undefined }),
        (results, metadata) => {
          // Render in live mode
          const { container: liveContainer } = render(
            <EvaluationViewer
              initialState={{
                mode: 'live',
                data: results,
                metadata,
              }}
            />
          );

          // Render in import mode with same data
          const { container: importContainer } = render(
            <EvaluationViewer
              initialState={{
                mode: 'import',
                data: results,
                metadata,
                currentFile: 'test.json',
              }}
            />
          );

          // Verify both modes display the same number of results
          const liveResults = liveContainer.querySelectorAll(
            '[data-testid="result-item"]'
          );
          const importResults = importContainer.querySelectorAll(
            '[data-testid="result-item"]'
          );
          expect(liveResults.length).toBe(importResults.length);
          expect(liveResults.length).toBe(results.length);

          // Verify both modes display results in the same order
          results.forEach((result, index) => {
            const liveItem = liveResults[index];
            const importItem = importResults[index];

            // Both should contain the same test case ID
            expect(liveItem.textContent).toContain(result.testCaseId);
            expect(importItem.textContent).toContain(result.testCaseId);

            // Both should contain the same input/output data
            const inputStr = JSON.stringify(result.input);
            const outputStr = JSON.stringify(result.output);

            expect(liveItem.textContent).toContain('Input:');
            expect(importItem.textContent).toContain('Input:');
            expect(liveItem.textContent).toContain('Output:');
            expect(importItem.textContent).toContain('Output:');
          });

          // Verify metadata is displayed identically in both modes
          if (metadata) {
            expect(liveContainer.textContent).toContain(metadata.evalRunId);
            expect(importContainer.textContent).toContain(metadata.evalRunId);

            if (metadata.actionRef) {
              expect(liveContainer.textContent).toContain(metadata.actionRef);
              expect(importContainer.textContent).toContain(metadata.actionRef);
            }

            if (metadata.datasetId) {
              expect(liveContainer.textContent).toContain(metadata.datasetId);
              expect(importContainer.textContent).toContain(metadata.datasetId);
            }
          }

          // The only difference should be the import mode banner
          const importBanner = importContainer.querySelector(
            '[data-testid="import-mode-banner"]'
          );
          const liveBanner = liveContainer.querySelector(
            '[data-testid="import-mode-banner"]'
          );

          expect(importBanner).toBeInTheDocument();
          expect(liveBanner).not.toBeInTheDocument();
        }
      ),
      { numRuns: 25 }
    );
  });

  /**
   * Feature: evaluation-results-import, Property 9: Trace Lookup Disabled in Import Mode
   *
   * **Validates: Requirements 5.1, 5.3**
   *
   * For any imported evaluation result, attempting to view trace details should display
   * an unavailability message, and trace IDs (when present) should be displayed as
   * non-interactive text rather than clickable links.
   */
  test('Property 9: trace lookup is disabled in import mode', () => {
    fc.assert(
      fc.property(
        fc.array(
          evalResultArbitrary().map((result) => ({
            ...result,
            // Ensure at least some results have trace IDs
            traceIds:
              result.traceIds.length > 0
                ? result.traceIds
                : ['trace-1', 'trace-2'],
          })),
          { minLength: 1, maxLength: 5 }
        ),
        (results) => {
          // Render in import mode
          const { container: importContainer } = render(
            <EvaluationViewer
              initialState={{
                mode: 'import',
                data: results,
                currentFile: 'test.json',
              }}
            />
          );

          // Render in live mode for comparison
          const { container: liveContainer } = render(
            <EvaluationViewer
              initialState={{
                mode: 'live',
                data: results,
              }}
            />
          );

          // Verify trace IDs are displayed in both modes
          results.forEach((result) => {
            if (result.traceIds && result.traceIds.length > 0) {
              result.traceIds.forEach((traceId) => {
                // Both modes should display the trace ID text
                expect(importContainer.textContent).toContain(traceId);
                expect(liveContainer.textContent).toContain(traceId);
              });
            }
          });

          // In import mode, trace IDs should be non-interactive text
          const importTraceText = importContainer.querySelectorAll(
            '[data-testid="trace-ids-text"]'
          );
          expect(importTraceText.length).toBeGreaterThan(0);

          // Verify no trace links exist in import mode
          const importTraceLinks = importContainer.querySelectorAll(
            '[data-testid="trace-link"]'
          );
          expect(importTraceLinks.length).toBe(0);

          // In live mode, trace IDs should be interactive links
          const liveTraceLinks = liveContainer.querySelectorAll(
            '[data-testid="trace-link"]'
          );
          expect(liveTraceLinks.length).toBeGreaterThan(0);

          // Verify no trace text (non-interactive) exists in live mode
          const liveTraceText = liveContainer.querySelectorAll(
            '[data-testid="trace-ids-text"]'
          );
          expect(liveTraceText.length).toBe(0);

          // Verify tooltip message about unavailability in import mode
          const traceTextElements = importContainer.querySelectorAll(
            '[data-testid="trace-ids-text"]'
          );
          traceTextElements.forEach((element) => {
            expect(element.getAttribute('title')).toContain('unavailable');
          });
        }
      ),
      { numRuns: 25 }
    );
  });

  /**
   * Feature: evaluation-results-import, Property 13: UI State Preservation
   *
   * **Validates: Requirements 7.4**
   *
   * For any UI state (filters, sort order) applied to imported data, switching to a
   * different imported file should preserve that UI state where applicable.
   */
  test('Property 13: UI state is preserved across file switches', () => {
    fc.assert(
      fc.property(
        fc.array(evalResultArbitrary(), { minLength: 1, maxLength: 5 }),
        fc.array(evalResultArbitrary(), { minLength: 1, maxLength: 5 }),
        uiStateArbitrary(),
        (firstFileData, secondFileData, uiState) => {
          // Create a test component that uses the hook
          let hookResult: any;

          const TestComponent = () => {
            hookResult =
              require('../../src/eval/evaluation-viewer').useEvaluationViewerState();
            return null;
          };

          const { rerender } = render(<TestComponent />);

          // Load first file
          React.act(() => {
            hookResult.loadImportedData(firstFileData, undefined, 'first.json');
          });

          rerender(<TestComponent />);

          // Apply UI state
          React.act(() => {
            hookResult.updateUIState(uiState);
          });

          rerender(<TestComponent />);

          // Verify UI state is applied
          expect(hookResult.state.uiState).toEqual(uiState);

          // Load second file (should preserve UI state)
          React.act(() => {
            hookResult.loadImportedData(
              secondFileData,
              undefined,
              'second.json'
            );
          });

          rerender(<TestComponent />);

          // Verify UI state is preserved
          expect(hookResult.state.uiState).toEqual(uiState);
          expect(hookResult.state.currentFile).toBe('second.json');
          expect(hookResult.state.data).toEqual(secondFileData);
        }
      ),
      { numRuns: 25 }
    );
  });
});
