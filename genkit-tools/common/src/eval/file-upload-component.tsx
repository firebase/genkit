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

import React, { useRef, useState, type ChangeEvent } from 'react';
import type { EvalResult, EvalRunKey } from '../types/eval';
import { CsvParser } from './csv-parser';
import { ErrorDisplay } from './error-display';
import { ErrorLogger } from './error-logger';
import type { ParseError, ParseResult } from './file-parser';
import { JsonParser } from './json-parser';

/**
 * Props for the FileUploadComponent.
 */
export interface FileUploadComponentProps {
  /** Callback when file is successfully parsed */
  onUploadComplete: (
    data: EvalResult[],
    metadata?: EvalRunKey,
    filename?: string
  ) => void;
  /** Callback when an error occurs during upload or parsing */
  onUploadError: (error: Error) => void;
  /** Optional CSS class name for styling */
  className?: string;
}

/**
 * File upload component for importing evaluation results.
 *
 * Supports JSON and CSV file formats. Validates file extensions,
 * provides visual feedback during upload, and displays error messages
 * for unsupported file types.
 */
export const FileUploadComponent: React.FC<FileUploadComponentProps> = ({
  onUploadComplete,
  onUploadError,
  className = '',
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<ParseError | Error | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const jsonParser = new JsonParser();
  const csvParser = new CsvParser();

  /**
   * Validate file extension.
   *
   * @param file - The file to validate
   * @returns true if file has .json or .csv extension
   */
  const validateFileExtension = (file: File): boolean => {
    const extension = file.name.toLowerCase().split('.').pop();
    return extension === 'json' || extension === 'csv';
  };

  /**
   * Get the appropriate parser for a file based on its extension.
   *
   * @param file - The file to parse
   * @returns JsonParser or CsvParser
   */
  const getParser = (file: File) => {
    const extension = file.name.toLowerCase().split('.').pop();
    return extension === 'json' ? jsonParser : csvParser;
  };

  /**
   * Handle file selection and parsing.
   *
   * @param event - The file input change event
   */
  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    // Clear previous error
    setError(null);

    // Validate file extension
    if (!validateFileExtension(file)) {
      const errorMessage =
        'Unsupported file format. Please upload a .json or .csv file.';
      const parseError: ParseError = {
        message: errorMessage,
        details: `File extension: .${file.name.toLowerCase().split('.').pop()}`,
      };
      setError(parseError);

      // Log error for debugging
      ErrorLogger.logParseError(parseError, file);

      onUploadError(new Error(errorMessage));

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    // Start upload
    setIsUploading(true);

    try {
      // Get appropriate parser
      const parser = getParser(file);

      // Parse file
      const result: ParseResult = await parser.parse(file);

      if (result.success && result.data) {
        // Success - pass data to parent
        onUploadComplete(result.data, result.metadata, file.name);
        setError(null);
      } else if (result.error) {
        // Parsing error
        setError(result.error);

        // Log error for debugging
        ErrorLogger.logParseError(result.error, file);

        const errorMessage = result.error.details
          ? `${result.error.message}: ${result.error.details}`
          : result.error.message;
        onUploadError(new Error(errorMessage));
      }
    } catch (err) {
      // Unexpected error
      const errorObj =
        err instanceof Error ? err : new Error('An unexpected error occurred');
      setError(errorObj);

      // Log error for debugging
      ErrorLogger.logParseError(errorObj, file);

      onUploadError(errorObj);
    } finally {
      setIsUploading(false);

      // Reset file input to allow re-uploading the same file
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  /**
   * Handle click on the upload button.
   */
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  /**
   * Handle retry by triggering file input click.
   */
  const handleRetry = () => {
    setError(null);
    handleUploadClick();
  };

  return (
    <div className={`file-upload-component ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,.csv"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        disabled={isUploading}
        data-testid="file-input"
      />

      <button
        onClick={handleUploadClick}
        disabled={isUploading}
        className="upload-button"
        data-testid="upload-button">
        {isUploading ? 'Uploading...' : 'Import Evaluation Results'}
      </button>

      {isUploading && (
        <div className="loading-indicator" data-testid="loading-indicator">
          <span>Loading...</span>
        </div>
      )}

      {error && (
        <ErrorDisplay
          error={error}
          onRetry={handleRetry}
          data-testid="error-display"
        />
      )}
    </div>
  );
};
