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

import React, { useState } from 'react';
import type { EvalMetric, EvalResult, EvalRunKey } from '../types/eval';

/**
 * Format a timestamp to human-readable format.
 */
const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
};

/**
 * Format JSON data for display.
 */
const formatJson = (data: any): string => {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
};

/**
 * Component to display a single metric.
 */
const MetricDisplay: React.FC<{ metric: EvalMetric }> = ({ metric }) => (
  <div className="metric-item" data-testid="metric-item">
    <div className="metric-evaluator" data-testid="metric-evaluator">
      <strong>{metric.evaluator}</strong>
    </div>
    {metric.score !== undefined && (
      <div className="metric-score" data-testid="metric-score">
        Score: {String(metric.score)}
      </div>
    )}
    {metric.status && (
      <div className="metric-status" data-testid="metric-status">
        Status: {metric.status}
      </div>
    )}
    {metric.rationale && (
      <div className="metric-rationale" data-testid="metric-rationale">
        Rationale: {metric.rationale}
      </div>
    )}
    {metric.error && (
      <div className="metric-error" data-testid="metric-error">
        Error: {metric.error}
      </div>
    )}
    {metric.scoreId && (
      <div className="metric-score-id" data-testid="metric-score-id">
        Score ID: {metric.scoreId}
      </div>
    )}
    {metric.traceId && (
      <div className="metric-trace-id" data-testid="metric-trace-id">
        Trace ID: {metric.traceId}
      </div>
    )}
    {metric.spanId && (
      <div className="metric-span-id" data-testid="metric-span-id">
        Span ID: {metric.spanId}
      </div>
    )}
  </div>
);

/**
 * Component to display evaluation metadata.
 */
const MetadataDisplay: React.FC<{ metadata: EvalRunKey }> = ({ metadata }) => (
  <div className="metadata-display" data-testid="metadata-display">
    <h3>Evaluation Metadata</h3>

    <div className="metadata-field" data-testid="eval-run-id">
      <strong>Eval Run ID:</strong> {metadata.evalRunId}
    </div>

    <div className="metadata-field" data-testid="created-at">
      <strong>Created At:</strong> {formatTimestamp(metadata.createdAt)}
    </div>

    {metadata.actionRef && (
      <div className="metadata-field" data-testid="action-ref">
        <strong>Action Reference:</strong> {metadata.actionRef}
      </div>
    )}

    {metadata.datasetId && (
      <div className="metadata-field" data-testid="dataset-id">
        <strong>Dataset ID:</strong> {metadata.datasetId}
      </div>
    )}

    {metadata.datasetVersion !== undefined && (
      <div className="metadata-field" data-testid="dataset-version">
        <strong>Dataset Version:</strong> {metadata.datasetVersion}
      </div>
    )}

    {metadata.actionConfig && (
      <div className="metadata-field" data-testid="action-config">
        <strong>Action Config:</strong>
        <pre>{formatJson(metadata.actionConfig)}</pre>
      </div>
    )}

    {metadata.metricSummaries && metadata.metricSummaries.length > 0 && (
      <div className="metadata-field" data-testid="metric-summaries">
        <strong>Metric Summaries:</strong>
        <pre>{formatJson(metadata.metricSummaries)}</pre>
      </div>
    )}

    {metadata.metricsMetadata && (
      <div className="metadata-field" data-testid="metrics-metadata">
        <strong>Metrics Metadata:</strong>
        {Object.entries(metadata.metricsMetadata).map(([key, value]) => (
          <div key={key} className="metric-metadata-item">
            <div>
              <strong>{key}</strong>
            </div>
            <div>Display Name: {value.displayName}</div>
            <div>Definition: {value.definition}</div>
          </div>
        ))}
      </div>
    )}
  </div>
);

/**
 * Mode for the evaluation viewer.
 * - 'live': Displaying live evaluation data from runtime
 * - 'import': Displaying imported evaluation data from file
 */
export type EvaluationViewerMode = 'live' | 'import';

/**
 * UI state for filters and sorting.
 */
export interface UIState {
  /** Active filters (e.g., by evaluator, status, etc.) */
  filters?: Record<string, any>;
  /** Current sort order (field and direction) */
  sortOrder?: {
    field: string;
    direction: 'asc' | 'desc';
  };
}

/**
 * State for the evaluation viewer.
 */
export interface EvaluationViewerState {
  /** Current mode: live or import */
  mode: EvaluationViewerMode;
  /** Evaluation results to display */
  data: EvalResult[];
  /** Optional metadata from evaluation run */
  metadata?: EvalRunKey;
  /** Current filename being viewed (only in import mode) */
  currentFile?: string;
  /** UI state (filters, sort order) */
  uiState?: UIState;
}

/**
 * Props for the EvaluationViewer component.
 */
export interface EvaluationViewerProps {
  /** Initial state for the viewer */
  initialState?: Partial<EvaluationViewerState>;
  /** Callback when user clears imported data */
  onClearImportedData?: () => void;
}

/**
 * Hook for managing evaluation viewer state.
 */
export const useEvaluationViewerState = (
  initialState?: Partial<EvaluationViewerState>
) => {
  const [state, setState] = useState<EvaluationViewerState>({
    mode: initialState?.mode || 'live',
    data: initialState?.data || [],
    metadata: initialState?.metadata,
    currentFile: initialState?.currentFile,
    uiState: initialState?.uiState,
  });

  /**
   * Switch to import mode with new data.
   * Replaces any existing imported data.
   * Preserves UI state where applicable.
   */
  const loadImportedData = (
    data: EvalResult[],
    metadata?: EvalRunKey,
    filename?: string
  ) => {
    // Preserve current UI state when switching files
    const preservedUIState =
      state.mode === 'import' ? state.uiState : undefined;

    setState({
      mode: 'import',
      data,
      metadata,
      currentFile: filename,
      uiState: preservedUIState,
    });
  };

  /**
   * Switch to live mode and clear imported data.
   */
  const clearImportedData = () => {
    setState({
      mode: 'live',
      data: [],
      metadata: undefined,
      currentFile: undefined,
      uiState: undefined,
    });
  };

  /**
   * Update live data (only works in live mode).
   */
  const updateLiveData = (data: EvalResult[], metadata?: EvalRunKey) => {
    if (state.mode === 'live') {
      setState({
        ...state,
        data,
        metadata,
      });
    }
  };

  /**
   * Update UI state (filters, sort order).
   */
  const updateUIState = (uiState: UIState) => {
    setState({
      ...state,
      uiState,
    });
  };

  /**
   * Check if preserved UI state is applicable to new data.
   * Returns true if the UI state can be applied, false otherwise.
   */
  const isUIStateApplicable = (
    uiState: UIState | undefined,
    data: EvalResult[]
  ): boolean => {
    if (!uiState) return true;

    // Check if sort field exists in the data
    if (uiState.sortOrder) {
      const field = uiState.sortOrder.field;

      // Check if any result has the sort field
      const hasField = data.some((result) => {
        // Check top-level fields
        if (field in result) return true;

        // Check metric fields
        if (result.metrics) {
          return result.metrics.some((metric) => field in metric);
        }

        return false;
      });

      if (!hasField) return false;
    }

    // Check if filter fields exist in the data
    if (uiState.filters) {
      for (const filterField of Object.keys(uiState.filters)) {
        const hasField = data.some((result) => {
          // Check top-level fields
          if (filterField in result) return true;

          // Check metric fields
          if (result.metrics) {
            return result.metrics.some((metric) => filterField in metric);
          }

          return false;
        });

        if (!hasField) return false;
      }
    }

    return true;
  };

  /**
   * Reset UI state if it's not applicable to current data.
   */
  const resetUIStateIfNotApplicable = () => {
    if (!isUIStateApplicable(state.uiState, state.data)) {
      setState({
        ...state,
        uiState: undefined,
      });
    }
  };

  return {
    state,
    loadImportedData,
    clearImportedData,
    updateLiveData,
    updateUIState,
    isUIStateApplicable,
    resetUIStateIfNotApplicable,
  };
};

/**
 * Evaluation viewer component that displays evaluation results.
 * Supports both live and import modes.
 */
export const EvaluationViewer: React.FC<EvaluationViewerProps> = ({
  initialState,
  onClearImportedData,
}) => {
  const { state, clearImportedData } = useEvaluationViewerState(initialState);

  const handleClearImportedData = () => {
    clearImportedData();
    onClearImportedData?.();
  };

  return (
    <div className="evaluation-viewer" data-testid="evaluation-viewer">
      {/* Import mode indicator banner */}
      {state.mode === 'import' && (
        <div className="import-mode-banner" data-testid="import-mode-banner">
          <div className="banner-content">
            <span className="import-badge" data-testid="import-badge">
              📁 Imported Data
            </span>
            {state.currentFile && (
              <span className="current-filename" data-testid="current-filename">
                File: {state.currentFile}
              </span>
            )}
          </div>
          <button
            onClick={handleClearImportedData}
            className="clear-imported-button"
            data-testid="clear-imported-button"
            title="Clear imported data and return to live mode">
            ✕ Clear Imported Data
          </button>
        </div>
      )}

      {/* Evaluation results display */}
      <div className="evaluation-results" data-testid="evaluation-results">
        {/* Display metadata if available */}
        {state.metadata && <MetadataDisplay metadata={state.metadata} />}

        {state.data.length === 0 ? (
          <div className="no-data" data-testid="no-data">
            No evaluation data available
          </div>
        ) : (
          <div className="results-list" data-testid="results-list">
            {state.data.map((result, index) => (
              <div
                key={result.testCaseId || index}
                className="result-item"
                data-testid="result-item">
                {/* Test Case ID */}
                <div className="test-case-id" data-testid="test-case-id">
                  <strong>Test Case ID:</strong> {result.testCaseId}
                </div>

                {/* Input */}
                <div className="result-input" data-testid="result-input">
                  <strong>Input:</strong>
                  <pre>{formatJson(result.input)}</pre>
                </div>

                {/* Output */}
                <div className="result-output" data-testid="result-output">
                  <strong>Output:</strong>
                  <pre>{formatJson(result.output)}</pre>
                </div>

                {/* Reference (optional) */}
                {result.reference !== undefined && (
                  <div
                    className="result-reference"
                    data-testid="result-reference">
                    <strong>Reference:</strong>
                    <pre>{formatJson(result.reference)}</pre>
                  </div>
                )}

                {/* Error (optional) */}
                {result.error && (
                  <div className="result-error" data-testid="result-error">
                    <strong>Error:</strong> {result.error}
                  </div>
                )}

                {/* Context (optional) */}
                {result.context && result.context.length > 0 && (
                  <div className="result-context" data-testid="result-context">
                    <strong>Context:</strong>
                    <pre>{formatJson(result.context)}</pre>
                  </div>
                )}

                {/* Display trace IDs based on mode */}
                {result.traceIds && result.traceIds.length > 0 && (
                  <div className="trace-ids" data-testid="trace-ids">
                    <strong>Trace IDs: </strong>
                    {state.mode === 'import' ? (
                      // In import mode, display as non-interactive text
                      <span
                        className="trace-ids-text"
                        data-testid="trace-ids-text"
                        title="Trace lookup is unavailable for imported data">
                        {result.traceIds.join(', ')}
                      </span>
                    ) : (
                      // In live mode, display as interactive links
                      <span
                        className="trace-ids-links"
                        data-testid="trace-ids-links">
                        {result.traceIds.map((traceId, idx) => (
                          <a
                            key={idx}
                            href={`#/trace/${traceId}`}
                            className="trace-link"
                            data-testid="trace-link">
                            {traceId}
                          </a>
                        ))}
                      </span>
                    )}
                  </div>
                )}

                {/* Metrics */}
                {result.metrics && result.metrics.length > 0 && (
                  <div className="result-metrics" data-testid="result-metrics">
                    <strong>Metrics:</strong>
                    <div className="metrics-list">
                      {result.metrics.map((metric, idx) => (
                        <MetricDisplay key={idx} metric={metric} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
