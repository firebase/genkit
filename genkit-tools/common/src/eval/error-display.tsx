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
import type { ParseError } from './file-parser';

/**
 * Props for the ErrorDisplay component.
 */
export interface ErrorDisplayProps {
  /** The error to display */
  error: ParseError | Error | string;
  /** Optional callback to retry the operation */
  onRetry?: () => void;
  /** Optional CSS class name for styling */
  className?: string;
}

/**
 * Get actionable guidance for common error types.
 *
 * @param message - The error message
 * @param missingFields - Optional list of missing fields
 * @returns User-friendly guidance text
 */
const getActionableGuidance = (
  message: string,
  missingFields?: string[]
): string => {
  const lowerMessage = message.toLowerCase();

  // Unsupported file extension
  if (
    lowerMessage.includes('unsupported file format') ||
    lowerMessage.includes('unsupported file')
  ) {
    return 'Please select a file with .json or .csv extension. These are the only supported formats for evaluation results.';
  }

  // File read error
  if (
    lowerMessage.includes('failed to read file') ||
    lowerMessage.includes('file read error')
  ) {
    return 'Check that the file is not corrupted and you have permission to read it. Try selecting the file again.';
  }

  // Malformed JSON
  if (
    lowerMessage.includes('invalid json') ||
    lowerMessage.includes('malformed json')
  ) {
    return 'The JSON file is not properly formatted. Validate your JSON syntax using a JSON validator tool.';
  }

  // Malformed CSV
  if (
    lowerMessage.includes('invalid csv') ||
    lowerMessage.includes('malformed csv')
  ) {
    return 'The CSV file is not properly formatted. Ensure it has proper headers and all rows have the same number of columns.';
  }

  // Missing required fields
  if (missingFields && missingFields.length > 0) {
    return `The evaluation data is missing required fields: ${missingFields.join(', ')}. Ensure your exported data includes all required fields.`;
  }

  if (
    lowerMessage.includes('missing required fields') ||
    lowerMessage.includes('missing required columns')
  ) {
    return 'Ensure your exported evaluation data includes all required fields: testCaseId, input, and output.';
  }

  // Empty file
  if (lowerMessage.includes('empty') || lowerMessage.includes('no data')) {
    return 'The file appears to be empty. Please select a file that contains evaluation results.';
  }

  // Unrecognized structure
  if (
    lowerMessage.includes('unrecognized') ||
    lowerMessage.includes('invalid structure')
  ) {
    return 'The file structure is not recognized. Expected either an EvalRun object with key and results, or an array of EvalResult objects.';
  }

  // Generic guidance
  return 'Please check the file format and try again. If the problem persists, verify that the file was exported correctly from Genkit.';
};

/**
 * Format error message for user-friendly display.
 *
 * @param error - The error to format
 * @returns Formatted error message
 */
const formatErrorMessage = (error: ParseError | Error | string): string => {
  if (typeof error === 'string') {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  // ParseError
  if (error.details) {
    return `${error.message}: ${error.details}`;
  }

  return error.message;
};

/**
 * Extract ParseError if available.
 *
 * @param error - The error object
 * @returns ParseError or undefined
 */
const getParseError = (
  error: ParseError | Error | string
): ParseError | undefined => {
  if (typeof error === 'string' || error instanceof Error) {
    return undefined;
  }
  return error;
};

/**
 * Error display component for showing user-friendly error messages.
 *
 * Displays error messages with actionable guidance for common error types.
 * Supports retry functionality and formats errors for easy understanding.
 */
export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  className = '',
}) => {
  const parseError = getParseError(error);
  const errorMessage = formatErrorMessage(error);
  const guidance = getActionableGuidance(
    errorMessage,
    parseError?.missingFields
  );

  return (
    <div
      className={`error-display ${className}`}
      data-testid="error-display"
      role="alert"
      aria-live="assertive">
      <div className="error-icon" data-testid="error-icon">
        ⚠️
      </div>

      <div className="error-content">
        <div className="error-message" data-testid="error-message">
          <strong>Error:</strong> {errorMessage}
        </div>

        {parseError?.missingFields && parseError.missingFields.length > 0 && (
          <div className="missing-fields" data-testid="missing-fields">
            <strong>Missing fields:</strong>{' '}
            {parseError.missingFields.join(', ')}
          </div>
        )}

        <div className="error-guidance" data-testid="error-guidance">
          {guidance}
        </div>

        {onRetry && (
          <button
            onClick={onRetry}
            className="retry-button"
            data-testid="retry-button">
            Try Again
          </button>
        )}
      </div>
    </div>
  );
};
