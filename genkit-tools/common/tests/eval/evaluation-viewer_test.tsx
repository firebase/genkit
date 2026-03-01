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

import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import {
  EvaluationViewer,
  useEvaluationViewerState,
} from '../../src/eval/evaluation-viewer';
import type { EvalResult, EvalRunKey } from '../../src/types/eval';

describe('EvaluationViewer Unit Tests', () => {
  const mockEvalResult: EvalResult = {
    testCaseId: 'test-1',
    input: { query: 'hello' },
    output: { response: 'hi' },
    reference: { expected: 'hi' },
    traceIds: ['trace-1', 'trace-2'],
    metrics: [
      {
        evaluator: 'faithfulness',
        score: 0.95,
        rationale: 'Accurate response',
      },
    ],
  };

  const mockMetadata: EvalRunKey = {
    evalRunId: 'run-1',
    createdAt: '2024-01-15T10:30:00Z',
    actionRef: 'myAction',
    datasetId: 'dataset-1',
  };

  describe('Import Mode State Management', () => {
    /**
     * Test import mode state transitions
     * Requirements: 7.1, 7.3
     */
    test('should initialize in live mode by default', () => {
      const { container } = render(<EvaluationViewer />);

      // Should not show import mode banner
      expect(
        screen.queryByTestId('import-mode-banner')
      ).not.toBeInTheDocument();
    });

    test('should initialize in import mode when specified', () => {
      const { container } = render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      // Should show import mode banner
      expect(screen.getByTestId('import-mode-banner')).toBeInTheDocument();
    });

    test('should display current filename in import mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'my-eval-results.json',
          }}
        />
      );

      // Should display filename
      const filenameElement = screen.getByTestId('current-filename');
      expect(filenameElement).toBeInTheDocument();
      expect(filenameElement.textContent).toContain('my-eval-results.json');
    });

    test('should call onClearImportedData when clear button is clicked', () => {
      const mockClearCallback = jest.fn();

      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
          onClearImportedData={mockClearCallback}
        />
      );

      // Click clear button
      const clearButton = screen.getByTestId('clear-imported-button');
      fireEvent.click(clearButton);

      // Callback should be called
      expect(mockClearCallback).toHaveBeenCalledTimes(1);
    });
  });

  describe('Import Mode Indicator Display', () => {
    /**
     * Test import mode indicator display
     * Requirements: 5.4, 7.2, 7.3
     */
    test('should display import badge in import mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      const badge = screen.getByTestId('import-badge');
      expect(badge).toBeInTheDocument();
      expect(badge.textContent).toContain('Imported Data');
    });

    test('should not display import banner in live mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'live',
            data: [mockEvalResult],
          }}
        />
      );

      expect(
        screen.queryByTestId('import-mode-banner')
      ).not.toBeInTheDocument();
    });

    test('should display clear button in import mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      const clearButton = screen.getByTestId('clear-imported-button');
      expect(clearButton).toBeInTheDocument();
      expect(clearButton.textContent).toContain('Clear Imported Data');
    });
  });

  describe('Trace Lookup Disabled in Import Mode', () => {
    /**
     * Test trace lookup disabled in import mode
     * Requirements: 5.1, 5.2, 5.3
     */
    test('should display trace IDs as non-interactive text in import mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      // Should display trace IDs as text
      const traceText = screen.getByTestId('trace-ids-text');
      expect(traceText).toBeInTheDocument();
      expect(traceText.textContent).toContain('trace-1');
      expect(traceText.textContent).toContain('trace-2');

      // Should not have trace links
      expect(screen.queryByTestId('trace-link')).not.toBeInTheDocument();
    });

    test('should display trace IDs as interactive links in live mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'live',
            data: [mockEvalResult],
          }}
        />
      );

      // Should display trace IDs as links
      const traceLinks = screen.getAllByTestId('trace-link');
      expect(traceLinks.length).toBe(2);
      expect(traceLinks[0].getAttribute('href')).toContain('trace-1');
      expect(traceLinks[1].getAttribute('href')).toContain('trace-2');

      // Should not have trace text (non-interactive)
      expect(screen.queryByTestId('trace-ids-text')).not.toBeInTheDocument();
    });

    test('should show tooltip explaining trace unavailability in import mode', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      const traceText = screen.getByTestId('trace-ids-text');
      expect(traceText.getAttribute('title')).toContain('unavailable');
    });
  });

  describe('Field Display', () => {
    /**
     * Test all evaluation fields are displayed
     * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
     */
    test('should display test case ID', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      expect(screen.getByText('test-1')).toBeInTheDocument();
    });

    test('should display input and output', () => {
      const { container } = render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      expect(screen.getAllByText(/Input:/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Output:/).length).toBeGreaterThan(0);
      expect(container.textContent).toContain('hello');
      expect(container.textContent).toContain('hi');
    });

    test('should display reference when present', () => {
      const { container } = render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      expect(screen.getAllByText(/Reference:/).length).toBeGreaterThan(0);
      expect(container.textContent).toContain('expected');
    });

    test('should display metrics', () => {
      const { container } = render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            currentFile: 'test.json',
          }}
        />
      );

      expect(container.textContent).toContain('faithfulness');
      expect(container.textContent).toContain('0.95');
      expect(container.textContent).toContain('Accurate response');
    });

    test('should display metadata when present', () => {
      const { container } = render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            metadata: mockMetadata,
            currentFile: 'test.json',
          }}
        />
      );

      expect(container.textContent).toContain('run-1');
      expect(container.textContent).toContain('myAction');
      expect(container.textContent).toContain('dataset-1');
      expect(screen.getAllByText(/Created At:/).length).toBeGreaterThan(0);
    });

    test('should format timestamp in human-readable format', () => {
      const { container } = render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [mockEvalResult],
            metadata: mockMetadata,
            currentFile: 'test.json',
          }}
        />
      );

      // Should not display raw ISO string
      expect(container.textContent).not.toContain('2024-01-15T10:30:00Z');
      // Should display formatted date
      expect(container.textContent).toMatch(/Jan.*2024/);
    });
  });

  describe('No Data State', () => {
    test('should display no data message when data is empty', () => {
      render(
        <EvaluationViewer
          initialState={{
            mode: 'import',
            data: [],
            currentFile: 'test.json',
          }}
        />
      );

      expect(screen.getByTestId('no-data')).toBeInTheDocument();
      expect(
        screen.getByText(/No evaluation data available/)
      ).toBeInTheDocument();
    });
  });

  describe('useEvaluationViewerState Hook', () => {
    /**
     * Test state management hook
     */
    test('should manage state transitions correctly', () => {
      let hookResult: any;

      const TestComponent = () => {
        hookResult = useEvaluationViewerState();
        return null;
      };

      const { rerender } = render(<TestComponent />);

      // Initial state should be live mode
      expect(hookResult.state.mode).toBe('live');
      expect(hookResult.state.data).toEqual([]);

      // Load imported data
      React.act(() => {
        hookResult.loadImportedData(
          [mockEvalResult],
          mockMetadata,
          'test.json'
        );
      });

      rerender(<TestComponent />);

      // Should switch to import mode
      expect(hookResult.state.mode).toBe('import');
      expect(hookResult.state.data).toEqual([mockEvalResult]);
      expect(hookResult.state.metadata).toEqual(mockMetadata);
      expect(hookResult.state.currentFile).toBe('test.json');

      // Clear imported data
      React.act(() => {
        hookResult.clearImportedData();
      });

      rerender(<TestComponent />);

      // Should return to live mode
      expect(hookResult.state.mode).toBe('live');
      expect(hookResult.state.data).toEqual([]);
      expect(hookResult.state.metadata).toBeUndefined();
      expect(hookResult.state.currentFile).toBeUndefined();
    });
  });

  describe('UI State Preservation', () => {
    /**
     * Test filter preservation across file switches
     * Requirements: 7.4
     */
    test('should preserve filters when switching between imported files', () => {
      let hookResult: any;

      const TestComponent = () => {
        hookResult = useEvaluationViewerState();
        return null;
      };

      const { rerender } = render(<TestComponent />);

      const firstFileData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
          metrics: [{ evaluator: 'faithfulness', score: 0.9 }],
        },
      ];

      const secondFileData: EvalResult[] = [
        {
          testCaseId: 'test-2',
          input: { query: 'goodbye' },
          output: { response: 'bye' },
          traceIds: [],
          metrics: [{ evaluator: 'faithfulness', score: 0.8 }],
        },
      ];

      // Load first file
      React.act(() => {
        hookResult.loadImportedData(firstFileData, undefined, 'first.json');
      });

      rerender(<TestComponent />);

      // Apply filters
      const filters = { evaluator: 'faithfulness', minScore: 0.8 };
      React.act(() => {
        hookResult.updateUIState({ filters });
      });

      rerender(<TestComponent />);

      // Verify filters are applied
      expect(hookResult.state.uiState?.filters).toEqual(filters);

      // Switch to second file
      React.act(() => {
        hookResult.loadImportedData(secondFileData, undefined, 'second.json');
      });

      rerender(<TestComponent />);

      // Verify filters are preserved
      expect(hookResult.state.uiState?.filters).toEqual(filters);
      expect(hookResult.state.currentFile).toBe('second.json');
      expect(hookResult.state.data).toEqual(secondFileData);
    });

    /**
     * Test sort order preservation across file switches
     * Requirements: 7.4
     */
    test('should preserve sort order when switching between imported files', () => {
      let hookResult: any;

      const TestComponent = () => {
        hookResult = useEvaluationViewerState();
        return null;
      };

      const { rerender } = render(<TestComponent />);

      const firstFileData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const secondFileData: EvalResult[] = [
        {
          testCaseId: 'test-2',
          input: { query: 'goodbye' },
          output: { response: 'bye' },
          traceIds: [],
        },
      ];

      // Load first file
      React.act(() => {
        hookResult.loadImportedData(firstFileData, undefined, 'first.json');
      });

      rerender(<TestComponent />);

      // Apply sort order
      const sortOrder = { field: 'testCaseId', direction: 'asc' as const };
      React.act(() => {
        hookResult.updateUIState({ sortOrder });
      });

      rerender(<TestComponent />);

      // Verify sort order is applied
      expect(hookResult.state.uiState?.sortOrder).toEqual(sortOrder);

      // Switch to second file
      React.act(() => {
        hookResult.loadImportedData(secondFileData, undefined, 'second.json');
      });

      rerender(<TestComponent />);

      // Verify sort order is preserved
      expect(hookResult.state.uiState?.sortOrder).toEqual(sortOrder);
      expect(hookResult.state.currentFile).toBe('second.json');
      expect(hookResult.state.data).toEqual(secondFileData);
    });

    /**
     * Test state reset when not applicable
     * Requirements: 7.4
     */
    test('should detect when UI state is not applicable to new data', () => {
      let hookResult: any;

      const TestComponent = () => {
        hookResult = useEvaluationViewerState();
        return null;
      };

      const { rerender } = render(<TestComponent />);

      // Data with a specific field
      const dataWithField: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
          metrics: [{ evaluator: 'faithfulness', score: 0.9 }],
        },
      ];

      // Data without that field
      const dataWithoutField: EvalResult[] = [
        {
          testCaseId: 'test-2',
          input: { query: 'goodbye' },
          output: { response: 'bye' },
          traceIds: [],
          // No metrics
        },
      ];

      // Test sort field applicability
      const sortByMetricScore = { field: 'score', direction: 'desc' as const };
      const uiStateWithSort = { sortOrder: sortByMetricScore };

      // Should be applicable to data with metrics
      expect(
        hookResult.isUIStateApplicable(uiStateWithSort, dataWithField)
      ).toBe(true);

      // Should not be applicable to data without metrics
      expect(
        hookResult.isUIStateApplicable(uiStateWithSort, dataWithoutField)
      ).toBe(false);

      // Test filter field applicability
      const filterByEvaluator = { evaluator: 'faithfulness' };
      const uiStateWithFilter = { filters: filterByEvaluator };

      // Should be applicable to data with metrics
      expect(
        hookResult.isUIStateApplicable(uiStateWithFilter, dataWithField)
      ).toBe(true);

      // Should not be applicable to data without metrics
      expect(
        hookResult.isUIStateApplicable(uiStateWithFilter, dataWithoutField)
      ).toBe(false);
    });

    test('should reset UI state when not applicable to new data', () => {
      let hookResult: any;

      const TestComponent = () => {
        hookResult = useEvaluationViewerState();
        return null;
      };

      const { rerender } = render(<TestComponent />);

      // Data with metrics
      const dataWithMetrics: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
          metrics: [{ evaluator: 'faithfulness', score: 0.9 }],
        },
      ];

      // Load data and set UI state
      React.act(() => {
        hookResult.loadImportedData(dataWithMetrics, undefined, 'first.json');
      });

      rerender(<TestComponent />);

      const sortOrder = { field: 'score', direction: 'desc' as const };
      React.act(() => {
        hookResult.updateUIState({ sortOrder });
      });

      rerender(<TestComponent />);

      // Verify UI state is set
      expect(hookResult.state.uiState?.sortOrder).toEqual(sortOrder);

      // Reset UI state if not applicable
      React.act(() => {
        hookResult.resetUIStateIfNotApplicable();
      });

      rerender(<TestComponent />);

      // UI state should still be present (it's applicable)
      expect(hookResult.state.uiState?.sortOrder).toEqual(sortOrder);

      // Now load data without metrics
      const dataWithoutMetrics: EvalResult[] = [
        {
          testCaseId: 'test-2',
          input: { query: 'goodbye' },
          output: { response: 'bye' },
          traceIds: [],
        },
      ];

      React.act(() => {
        hookResult.loadImportedData(
          dataWithoutMetrics,
          undefined,
          'second.json'
        );
      });

      rerender(<TestComponent />);

      // UI state should still be preserved (loadImportedData preserves it)
      expect(hookResult.state.uiState?.sortOrder).toEqual(sortOrder);

      // But when we check applicability and reset
      React.act(() => {
        hookResult.resetUIStateIfNotApplicable();
      });

      rerender(<TestComponent />);

      // UI state should now be reset (not applicable)
      expect(hookResult.state.uiState).toBeUndefined();
    });

    test('should not preserve UI state when switching from live to import mode', () => {
      let hookResult: any;

      const TestComponent = () => {
        hookResult = useEvaluationViewerState();
        return null;
      };

      const { rerender } = render(<TestComponent />);

      const liveData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const importData: EvalResult[] = [
        {
          testCaseId: 'test-2',
          input: { query: 'goodbye' },
          output: { response: 'bye' },
          traceIds: [],
        },
      ];

      // Start in live mode
      React.act(() => {
        hookResult.updateLiveData(liveData);
      });

      rerender(<TestComponent />);

      // Apply UI state in live mode
      const sortOrder = { field: 'testCaseId', direction: 'asc' as const };
      React.act(() => {
        hookResult.updateUIState({ sortOrder });
      });

      rerender(<TestComponent />);

      // Verify UI state is applied
      expect(hookResult.state.uiState?.sortOrder).toEqual(sortOrder);
      expect(hookResult.state.mode).toBe('live');

      // Switch to import mode
      React.act(() => {
        hookResult.loadImportedData(importData, undefined, 'imported.json');
      });

      rerender(<TestComponent />);

      // UI state should NOT be preserved when switching from live to import
      expect(hookResult.state.mode).toBe('import');
      expect(hookResult.state.uiState).toBeUndefined();
    });
  });
});
