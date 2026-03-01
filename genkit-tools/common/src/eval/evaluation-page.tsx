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

import React from 'react';
import type { EvalResult, EvalRunKey } from '../types/eval';
import { EvaluationViewer, EvaluationViewerState } from './evaluation-viewer';
import { FileUploadComponent } from './file-upload-component';

/**
 * Props for the EvaluationPage component.
 */
export interface EvaluationPageProps {
  /** Optional CSS class name for styling */
  className?: string;
}

/**
 * Evaluation page component that integrates file upload and evaluation viewer.
 *
 * This page allows users to:
 * - Import evaluation results from JSON or CSV files
 * - View imported evaluation data
 * - Switch between multiple imported files
 * - Clear imported data and return to live mode
 */
export const EvaluationPage: React.FC<EvaluationPageProps> = ({
  className = '',
}) => {
  const [viewerState, setViewerState] = React.useState<
    Partial<EvaluationViewerState>
  >({
    mode: 'live',
    data: [],
  });

  /**
   * Handle successful file upload and parsing.
   */
  const handleUploadComplete = (
    data: EvalResult[],
    metadata?: EvalRunKey,
    filename?: string
  ) => {
    setViewerState({
      mode: 'import',
      data,
      metadata,
      currentFile: filename,
      uiState: viewerState.uiState, // Preserve UI state
    });
  };

  /**
   * Handle upload error.
   */
  const handleUploadError = (error: Error) => {
    console.error('File upload error:', error);
    // Error is already displayed by FileUploadComponent
  };

  /**
   * Handle clearing imported data.
   */
  const handleClearImportedData = () => {
    setViewerState({
      mode: 'live',
      data: [],
      metadata: undefined,
      currentFile: undefined,
      uiState: undefined,
    });
  };

  return (
    <div
      className={`evaluation-page ${className}`}
      data-testid="evaluation-page">
      {/* Page header */}
      <div className="page-header" data-testid="page-header">
        <h1>Evaluation Results</h1>
        <p>Import and view evaluation results from JSON or CSV files</p>
      </div>

      {/* File upload component */}
      <div className="upload-section" data-testid="upload-section">
        <FileUploadComponent
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
        />
      </div>

      {/* Evaluation viewer */}
      <div className="viewer-section" data-testid="viewer-section">
        <EvaluationViewer
          key={viewerState.currentFile || 'live'} // Force re-render when file changes
          initialState={viewerState}
          onClearImportedData={handleClearImportedData}
        />
      </div>
    </div>
  );
};
