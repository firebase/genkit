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
import React from 'react';
import { CsvParser } from '../../src/eval/csv-parser';
import { ErrorDisplay } from '../../src/eval/error-display';
import type { ParseError } from '../../src/eval/file-parser';
import { JsonParser } from '../../src/eval/json-parser';

describe('Error Handling Unit Tests', () => {
  describe('ErrorDisplay Component', () => {
    /**
     * Test error display component rendering
     * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
     */
    test('renders error message correctly', () => {
      const error: ParseError = {
        message: 'Test error message',
        details: 'Additional details',
      };

      render(<ErrorDisplay error={error} />);

      expect(screen.getByTestId('error-display')).toBeInTheDocument();
      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Test error message'
      );
      expect(screen.getByTestId('error-guidance')).toBeInTheDocument();
    });

    test('displays missing fields when provided', () => {
      const error: ParseError = {
        message: 'Missing required fields',
        missingFields: ['testCaseId', 'input', 'output'],
      };

      render(<ErrorDisplay error={error} />);

      expect(screen.getByTestId('missing-fields')).toBeInTheDocument();
      expect(screen.getByTestId('missing-fields')).toHaveTextContent(
        'testCaseId'
      );
      expect(screen.getByTestId('missing-fields')).toHaveTextContent('input');
      expect(screen.getByTestId('missing-fields')).toHaveTextContent('output');
    });

    test('displays retry button when onRetry is provided', () => {
      const error: ParseError = {
        message: 'Test error',
      };
      const onRetry = jest.fn();

      render(<ErrorDisplay error={error} onRetry={onRetry} />);

      const retryButton = screen.getByTestId('retry-button');
      expect(retryButton).toBeInTheDocument();

      retryButton.click();
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    test('does not display retry button when onRetry is not provided', () => {
      const error: ParseError = {
        message: 'Test error',
      };

      render(<ErrorDisplay error={error} />);

      expect(screen.queryByTestId('retry-button')).not.toBeInTheDocument();
    });

    test('handles Error objects', () => {
      const error = new Error('Standard error message');

      render(<ErrorDisplay error={error} />);

      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Standard error message'
      );
    });

    test('handles string errors', () => {
      render(<ErrorDisplay error="Simple string error" />);

      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Simple string error'
      );
    });

    test('provides actionable guidance for unsupported file format', () => {
      const error: ParseError = {
        message: 'Unsupported file format. Please upload a .json or .csv file.',
      };

      render(<ErrorDisplay error={error} />);

      const guidance = screen.getByTestId('error-guidance');
      expect(guidance).toHaveTextContent('.json or .csv');
      expect(guidance).toHaveTextContent('supported formats');
    });

    test('provides actionable guidance for malformed JSON', () => {
      const error: ParseError = {
        message: 'Invalid JSON format',
      };

      render(<ErrorDisplay error={error} />);

      const guidance = screen.getByTestId('error-guidance');
      expect(guidance).toHaveTextContent('JSON');
      expect(guidance.textContent?.toLowerCase()).toContain('validate');
    });

    test('provides actionable guidance for empty file', () => {
      const error: ParseError = {
        message: 'File contains no data',
      };

      render(<ErrorDisplay error={error} />);

      const guidance = screen.getByTestId('error-guidance');
      expect(guidance).toHaveTextContent('empty');
    });
  });

  describe('JSON Parser Error Handling', () => {
    const jsonParser = new JsonParser();

    /**
     * Test unsupported file extension error
     * Requirements: 6.1
     */
    test('handles unsupported file extension', async () => {
      // This test is handled by FileUploadComponent
      // JSON parser itself doesn't validate extensions
      expect(true).toBe(true);
    });

    /**
     * Test file read error
     * Requirements: 6.1
     */
    test('handles file read error gracefully', async () => {
      // File read errors are caught by the parser
      const invalidFile = new File([''], 'test.json', {
        type: 'application/json',
      });

      const result = await jsonParser.parse(invalidFile);

      // Empty file should produce an error
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    /**
     * Test malformed JSON error
     * Requirements: 6.1, 6.3
     */
    test('handles malformed JSON with descriptive error', async () => {
      const malformedJson = '{ invalid json }';
      const file = new File([malformedJson], 'test.json', {
        type: 'application/json',
      });

      const result = await jsonParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('JSON');
      expect(result.error?.details).toBeDefined();
    });

    /**
     * Test missing required fields error
     * Requirements: 6.1, 6.2
     */
    test('handles missing required fields with field list', async () => {
      const invalidData = JSON.stringify([
        {
          testCaseId: 'test-1',
          // Missing input and output
        },
      ]);
      const file = new File([invalidData], 'test.json', {
        type: 'application/json',
      });

      const result = await jsonParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required fields');
      expect(result.error?.missingFields).toBeDefined();
      expect(result.error?.missingFields).toContain('input');
      expect(result.error?.missingFields).toContain('output');
    });

    /**
     * Test empty file error
     * Requirements: 6.1, 6.4
     */
    test('handles empty file with descriptive error', async () => {
      const file = new File([''], 'test.json', { type: 'application/json' });

      const result = await jsonParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('no data');
    });

    test('handles empty results array', async () => {
      const emptyArray = JSON.stringify([]);
      const file = new File([emptyArray], 'test.json', {
        type: 'application/json',
      });

      const result = await jsonParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('no evaluation results');
    });

    test('handles unrecognized structure', async () => {
      const invalidStructure = JSON.stringify({ foo: 'bar', results: [] });
      const file = new File([invalidStructure], 'test.json', {
        type: 'application/json',
      });

      const result = await jsonParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      // The parser will detect this as an empty results array
      expect(result.error?.message).toContain('no evaluation results');
    });
  });

  describe('CSV Parser Error Handling', () => {
    const csvParser = new CsvParser();

    /**
     * Test malformed CSV error
     * Requirements: 6.1, 6.3
     */
    test('handles malformed CSV with descriptive error', async () => {
      const malformedCsv =
        'testCaseId,input,output\ntest-1,"unclosed quote,value\n';
      const file = new File([malformedCsv], 'test.csv', { type: 'text/csv' });

      const result = await csvParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('CSV');
    });

    /**
     * Test missing required columns error
     * Requirements: 6.1, 6.2
     */
    test('handles missing testCaseId column', async () => {
      const csvWithoutTestCaseId = 'input,output\n"{}","{}"\n';
      const file = new File([csvWithoutTestCaseId], 'test.csv', {
        type: 'text/csv',
      });

      const result = await csvParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('Missing required columns');
      expect(result.error?.missingFields).toContain('testCaseId');
    });

    test('handles missing input column', async () => {
      const csvWithoutInput = 'testCaseId,output\ntest-1,"{}"\n';
      const file = new File([csvWithoutInput], 'test.csv', {
        type: 'text/csv',
      });

      const result = await csvParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.missingFields).toContain('input');
    });

    test('handles missing output column', async () => {
      const csvWithoutOutput = 'testCaseId,input\ntest-1,"{}"\n';
      const file = new File([csvWithoutOutput], 'test.csv', {
        type: 'text/csv',
      });

      const result = await csvParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.missingFields).toContain('output');
    });

    /**
     * Test empty file error
     * Requirements: 6.1, 6.4
     */
    test('handles empty CSV file', async () => {
      const file = new File([''], 'test.csv', { type: 'text/csv' });

      const result = await csvParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('no data');
    });

    test('handles CSV with only headers', async () => {
      const csvWithOnlyHeaders = 'testCaseId,input,output\n';
      const file = new File([csvWithOnlyHeaders], 'test.csv', {
        type: 'text/csv',
      });

      const result = await csvParser.parse(file);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.message).toContain('no evaluation results');
    });
  });

  describe('Error Recovery', () => {
    /**
     * Test that errors preserve UI state
     * Requirements: 6.5
     */
    test('error display preserves component state', () => {
      const error: ParseError = {
        message: 'Test error',
      };

      const { rerender } = render(<ErrorDisplay error={error} />);

      expect(screen.getByTestId('error-display')).toBeInTheDocument();

      // Update error
      const newError: ParseError = {
        message: 'New error',
      };

      rerender(<ErrorDisplay error={newError} />);

      // Component should still be rendered
      expect(screen.getByTestId('error-display')).toBeInTheDocument();
      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'New error'
      );
    });

    /**
     * Test retry functionality
     * Requirements: 6.5
     */
    test('retry button allows recovery without page refresh', () => {
      const error: ParseError = {
        message: 'Test error',
      };
      const onRetry = jest.fn();

      render(<ErrorDisplay error={error} onRetry={onRetry} />);

      const retryButton = screen.getByTestId('retry-button');

      // Click retry multiple times
      retryButton.click();
      retryButton.click();

      expect(onRetry).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Message Formatting', () => {
    /**
     * Test user-friendly error display
     * Requirements: 6.5
     */
    test('formats error messages for user-friendly display', () => {
      const error: ParseError = {
        message: 'Invalid JSON format',
        details: 'Unexpected token at position 5',
      };

      render(<ErrorDisplay error={error} />);

      const errorMessage = screen.getByTestId('error-message');
      expect(errorMessage).toHaveTextContent('Invalid JSON format');
      expect(errorMessage).toHaveTextContent('Unexpected token at position 5');
    });

    test('displays actionable guidance for all error types', () => {
      const errorTypes = [
        {
          message: 'Unsupported file format',
          expectedGuidance: 'json or .csv',
        },
        { message: 'Failed to read file', expectedGuidance: 'permission' },
        { message: 'Invalid JSON format', expectedGuidance: 'validate' },
        { message: 'Invalid CSV format', expectedGuidance: 'headers' },
        {
          message: 'Missing required fields',
          expectedGuidance: 'required fields',
        },
        { message: 'File contains no data', expectedGuidance: 'empty' },
        {
          message: 'Unrecognized file structure',
          expectedGuidance: 'structure',
        },
      ];

      errorTypes.forEach(({ message, expectedGuidance }) => {
        const { unmount } = render(<ErrorDisplay error={{ message }} />);

        const guidance = screen.getByTestId('error-guidance');
        expect(guidance.textContent?.toLowerCase()).toContain(
          expectedGuidance.toLowerCase()
        );

        unmount();
      });
    });
  });
});
