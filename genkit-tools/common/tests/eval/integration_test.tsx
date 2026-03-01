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
import React from 'react';
import { EvaluationPage } from '../../src/eval/evaluation-page';
import type { EvalResult, EvalRunKey } from '../../src/types/eval';

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

describe('Integration Tests - End-to-End File Import Flow', () => {
  describe('JSON file import and display', () => {
    it('should upload JSON file, parse it, and display results', async () => {
      // Create test data
      const testData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'What is AI?' },
          output: { response: 'AI is artificial intelligence' },
          reference: { expected: 'AI is artificial intelligence' },
          traceIds: ['trace-1'],
          metrics: [
            {
              evaluator: 'faithfulness',
              score: 0.95,
              rationale: 'Accurate response',
            },
          ],
        },
        {
          testCaseId: 'test-2',
          input: { query: 'What is ML?' },
          output: { response: 'ML is machine learning' },
          traceIds: ['trace-2'],
          metrics: [
            {
              evaluator: 'relevance',
              score: 0.9,
              rationale: 'Relevant to query',
            },
          ],
        },
      ];

      const metadata: EvalRunKey = {
        evalRunId: 'run-123',
        createdAt: '2024-01-15T10:30:00Z',
        actionRef: 'myAction',
        datasetId: 'dataset-1',
      };

      const evalRun = {
        key: metadata,
        results: testData,
      };

      // Render the evaluation page
      render(<EvaluationPage />);

      // Verify page is rendered
      expect(screen.getByTestId('evaluation-page')).toBeInTheDocument();
      expect(screen.getByTestId('upload-button')).toBeInTheDocument();

      // Create and upload JSON file
      const file = new File([JSON.stringify(evalRun)], 'test-eval.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      // Wait for file to be parsed and displayed
      await waitFor(() => {
        expect(screen.getByTestId('import-mode-banner')).toBeInTheDocument();
      });

      // Verify import mode indicator
      expect(screen.getByTestId('import-badge')).toHaveTextContent(
        'Imported Data'
      );
      expect(screen.getByTestId('current-filename')).toHaveTextContent(
        'test-eval.json'
      );

      // Verify metadata is displayed
      expect(screen.getByTestId('metadata-display')).toBeInTheDocument();
      expect(screen.getByTestId('eval-run-id')).toHaveTextContent('run-123');
      expect(screen.getByTestId('created-at')).toBeInTheDocument();
      expect(screen.getByTestId('action-ref')).toHaveTextContent('myAction');
      expect(screen.getByTestId('dataset-id')).toHaveTextContent('dataset-1');

      // Verify results are displayed
      const resultItems = screen.getAllByTestId('result-item');
      expect(resultItems).toHaveLength(2);

      // Verify first result
      const testCaseIds = screen.getAllByTestId('test-case-id');
      expect(testCaseIds[0]).toHaveTextContent('test-1');

      // Verify trace IDs are displayed as text (not links) in import mode
      const traceIdsText = screen.getAllByTestId('trace-ids-text');
      expect(traceIdsText).toHaveLength(2);
      expect(traceIdsText[0]).toHaveTextContent('trace-1');

      // Verify metrics are displayed
      const metrics = screen.getAllByTestId('metric-item');
      expect(metrics.length).toBeGreaterThan(0);
    });

    it('should handle JSON file with array of results (no EvalRun wrapper)', async () => {
      const testData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      render(<EvaluationPage />);

      const file = new File([JSON.stringify(testData)], 'results.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('import-mode-banner')).toBeInTheDocument();
      });

      expect(screen.getByTestId('current-filename')).toHaveTextContent(
        'results.json'
      );
      expect(screen.getByTestId('result-item')).toBeInTheDocument();
    });
  });

  describe('CSV file import and display', () => {
    it('should upload CSV file, parse it, and display results', async () => {
      const csvContent = `testCaseId,input,output,reference,traceIds,faithfulness_score,faithfulness_rationale,relevance_score,relevance_rationale
test-1,"{""query"":""What is AI?""}","{""response"":""AI is artificial intelligence""}","{""expected"":""AI is artificial intelligence""}","[""trace-1""]",0.95,"Accurate response",0.90,"Relevant to query"
test-2,"{""query"":""What is ML?""}","{""response"":""ML is machine learning""}",,"[""trace-2""]",0.88,"Good response",0.92,"Very relevant"`;

      render(<EvaluationPage />);

      const file = new File([csvContent], 'test-eval.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('import-mode-banner')).toBeInTheDocument();
      });

      // Verify import mode
      expect(screen.getByTestId('current-filename')).toHaveTextContent(
        'test-eval.csv'
      );

      // Verify results are displayed
      const resultItems = screen.getAllByTestId('result-item');
      expect(resultItems).toHaveLength(2);

      // Verify metrics were reconstructed from CSV columns
      const metrics = screen.getAllByTestId('metric-item');
      expect(metrics.length).toBeGreaterThan(0);
    });
  });

  describe('switching between multiple imported files', () => {
    it('should replace current data when new file is uploaded', async () => {
      render(<EvaluationPage />);

      // Upload first file
      const firstData: EvalResult[] = [
        {
          testCaseId: 'file1-test-1',
          input: { query: 'first file' },
          output: { response: 'first response' },
          traceIds: [],
        },
      ];

      const firstFile = new File([JSON.stringify(firstData)], 'first.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [firstFile],
        writable: false,
        configurable: true,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('current-filename')).toHaveTextContent(
          'first.json'
        );
      });

      // Verify first file data is displayed
      expect(screen.getByTestId('test-case-id')).toHaveTextContent(
        'file1-test-1'
      );

      // Upload second file
      const secondData: EvalResult[] = [
        {
          testCaseId: 'file2-test-1',
          input: { query: 'second file' },
          output: { response: 'second response' },
          traceIds: [],
        },
        {
          testCaseId: 'file2-test-2',
          input: { query: 'another test' },
          output: { response: 'another response' },
          traceIds: [],
        },
      ];

      const secondFile = new File([JSON.stringify(secondData)], 'second.json', {
        type: 'application/json',
      });

      Object.defineProperty(fileInput, 'files', {
        value: [secondFile],
        writable: false,
        configurable: true,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('current-filename')).toHaveTextContent(
          'second.json'
        );
      });

      // Verify second file data replaced first file data
      const testCaseIds = screen.getAllByTestId('test-case-id');
      expect(testCaseIds).toHaveLength(2);
      expect(testCaseIds[0]).toHaveTextContent('file2-test-1');
      expect(testCaseIds[1]).toHaveTextContent('file2-test-2');

      // First file data should not be present
      expect(screen.queryByText('file1-test-1')).not.toBeInTheDocument();
    });
  });

  describe('clearing imported data and returning to live mode', () => {
    it('should clear imported data when clear button is clicked', async () => {
      render(<EvaluationPage />);

      // Upload a file
      const testData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const file = new File([JSON.stringify(testData)], 'test.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('import-mode-banner')).toBeInTheDocument();
      });

      // Verify data is displayed
      expect(screen.getByTestId('result-item')).toBeInTheDocument();

      // Click clear button
      const clearButton = screen.getByTestId('clear-imported-button');
      fireEvent.click(clearButton);

      // Verify import mode banner is removed
      await waitFor(() => {
        expect(
          screen.queryByTestId('import-mode-banner')
        ).not.toBeInTheDocument();
      });

      // Verify data is cleared
      expect(screen.queryByTestId('result-item')).not.toBeInTheDocument();
      expect(screen.getByTestId('no-data')).toBeInTheDocument();
    });
  });

  describe('error handling throughout the flow', () => {
    it('should display error for invalid JSON file', async () => {
      render(<EvaluationPage />);

      const file = new File(['invalid json content'], 'invalid.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Invalid JSON format'
      );
      expect(
        screen.queryByTestId('import-mode-banner')
      ).not.toBeInTheDocument();
    });

    it('should display error for missing required fields', async () => {
      render(<EvaluationPage />);

      const invalidData = [
        {
          testCaseId: 'test-1',
          // Missing input and output
        },
      ];

      const file = new File([JSON.stringify(invalidData)], 'invalid.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      const errorMessage = screen.getByTestId('error-message');
      expect(errorMessage).toHaveTextContent('Missing required fields');
    });

    it('should display error for unsupported file type', async () => {
      render(<EvaluationPage />);

      const file = new File(['some content'], 'test.txt', {
        type: 'text/plain',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      expect(screen.getByTestId('error-message')).toHaveTextContent(
        'Unsupported file format'
      );
    });

    it('should allow retry after error', async () => {
      render(<EvaluationPage />);

      // First upload - invalid file
      const invalidFile = new File(['invalid'], 'invalid.json', {
        type: 'application/json',
      });

      const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
      Object.defineProperty(fileInput, 'files', {
        value: [invalidFile],
        writable: false,
        configurable: true,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      // Second upload - valid file
      const validData: EvalResult[] = [
        {
          testCaseId: 'test-1',
          input: { query: 'hello' },
          output: { response: 'hi' },
          traceIds: [],
        },
      ];

      const validFile = new File([JSON.stringify(validData)], 'valid.json', {
        type: 'application/json',
      });

      Object.defineProperty(fileInput, 'files', {
        value: [validFile],
        writable: false,
        configurable: true,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(screen.getByTestId('import-mode-banner')).toBeInTheDocument();
      });

      // Error should be cleared
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
      expect(screen.getByTestId('result-item')).toBeInTheDocument();
    });
  });
});
