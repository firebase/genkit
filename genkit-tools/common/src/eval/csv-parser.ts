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

import { csv2json } from 'json-2-csv';
import type { EvalResult } from '../types/eval';
import {
  createErrorResult,
  createParseError,
  createSuccessResult,
  validateRequiredFields,
  type FileParser,
  type ParseResult,
  type ParserConfig,
} from './file-parser';

/**
 * Parser for CSV-formatted evaluation result files.
 *
 * Supports CSV files with flattened metric columns following the pattern:
 * - {evaluator}_score
 * - {evaluator}_rationale
 * - {evaluator}_error
 * - {evaluator}_traceId
 * - {evaluator}_spanId
 */
export class CsvParser implements FileParser {
  /**
   * Parse a CSV file containing evaluation results.
   *
   * @param file - The CSV file to parse
   * @param config - Optional parser configuration
   * @returns Promise resolving to ParseResult with data or error
   */
  async parse(file: File, config?: ParserConfig): Promise<ParseResult> {
    try {
      // Read file content
      const content = await this.readFileContent(file);

      // Check for empty file
      if (!content.trim()) {
        return createErrorResult(
          createParseError(
            'File contains no data',
            'The uploaded file is empty'
          )
        );
      }

      // Parse CSV
      let rows: any[];
      try {
        rows = await csv2json(content);
      } catch (error) {
        return createErrorResult(
          createParseError(
            'Invalid CSV format',
            error instanceof Error ? error.message : 'Failed to parse CSV'
          )
        );
      }

      // Check for empty results
      if (rows.length === 0 && !(config?.allowEmpty ?? false)) {
        return createErrorResult(
          createParseError(
            'File contains no evaluation results',
            'The CSV file has no data rows'
          )
        );
      }

      // Transform CSV rows to EvalResult objects
      const data: EvalResult[] = [];

      for (let i = 0; i < rows.length; i++) {
        const row = rows[i];

        // Validate required columns if enabled
        if (config?.validateRequiredFields ?? true) {
          const requiredFields = config?.requiredFields ?? [
            'testCaseId',
            'input',
            'output',
          ];
          const missingFields = validateRequiredFields(row, requiredFields);

          if (missingFields.length > 0) {
            return createErrorResult(
              createParseError(
                `Invalid CSV: Missing required columns: ${missingFields.join(', ')}`,
                `Row at index ${i} is missing required columns: ${missingFields.join(', ')}`,
                missingFields
              )
            );
          }
        }

        // Convert row to EvalResult
        const evalResult = this.rowToEvalResult(row);
        data.push(evalResult);
      }

      return createSuccessResult(data);
    } catch (error) {
      return createErrorResult(
        createParseError(
          'Failed to parse file',
          error instanceof Error ? error.message : 'Unknown error occurred'
        )
      );
    }
  }

  /**
   * Read file content as text.
   *
   * @param file - The file to read
   * @returns Promise resolving to file content as string
   */
  private async readFileContent(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (event) => {
        const content = event.target?.result;
        if (typeof content === 'string') {
          resolve(content);
        } else {
          reject(new Error('Failed to read file as text'));
        }
      };

      reader.onerror = () => {
        reject(new Error('File read error'));
      };

      reader.readAsText(file);
    });
  }

  /**
   * Convert a CSV row to an EvalResult object.
   *
   * @param row - The CSV row as an object
   * @returns EvalResult object
   */
  private rowToEvalResult(row: Record<string, any>): EvalResult {
    // Parse JSON fields
    const input = this.parseJsonField(row.input);
    const output = this.parseJsonField(row.output);
    const reference = this.parseJsonField(row.reference);
    const context = this.parseJsonField(row.context);
    const traceIds = this.parseJsonField(row.traceIds) || [];

    // Reconstruct metrics array from unpacked columns
    const metrics = this.reconstructMetrics(row);

    // Build EvalResult object
    const evalResult: EvalResult = {
      testCaseId: row.testCaseId,
      input,
      output,
      traceIds,
    };

    // Add optional fields if present
    if (row.error !== undefined && row.error !== null && row.error !== '') {
      evalResult.error = row.error;
    }

    if (reference !== undefined && reference !== null) {
      evalResult.reference = reference;
    }

    if (context !== undefined && context !== null) {
      evalResult.context = context;
    }

    if (metrics.length > 0) {
      evalResult.metrics = metrics;
    }

    return evalResult;
  }

  /**
   * Parse a JSON string field from CSV.
   * Handles empty cells as undefined.
   *
   * @param value - The field value
   * @returns Parsed value or undefined
   */
  private parseJsonField(value: any): any {
    if (value === undefined || value === null || value === '') {
      return undefined;
    }

    if (typeof value === 'string') {
      try {
        return JSON.parse(value);
      } catch {
        // If parsing fails, return the string as-is
        return value;
      }
    }

    return value;
  }

  /**
   * Reconstruct metrics array from unpacked CSV columns.
   *
   * Identifies columns matching patterns:
   * - {evaluator}_score
   * - {evaluator}_rationale
   * - {evaluator}_error
   * - {evaluator}_traceId
   * - {evaluator}_spanId
   *
   * @param row - The CSV row as an object
   * @returns Array of EvalMetric objects
   */
  private reconstructMetrics(row: Record<string, any>): any[] {
    const metrics: Record<string, any> = {};

    // Identify metric columns and group by evaluator name
    for (const [key, value] of Object.entries(row)) {
      // Skip if value is empty
      if (value === undefined || value === null || value === '') {
        continue;
      }

      // Check for metric column patterns
      const scoreMatch = key.match(/^(.+)_score$/);
      const rationaleMatch = key.match(/^(.+)_rationale$/);
      const errorMatch = key.match(/^(.+)_error$/);
      const traceIdMatch = key.match(/^(.+)_traceId$/);
      const spanIdMatch = key.match(/^(.+)_spanId$/);
      const scoreIdMatch = key.match(/^(.+)_scoreId$/);
      const statusMatch = key.match(/^(.+)_status$/);

      if (scoreMatch) {
        const evaluator = scoreMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        metrics[evaluator].score = this.parseScoreValue(value);
      } else if (rationaleMatch) {
        const evaluator = rationaleMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        // Ensure rationale is always a string
        metrics[evaluator].rationale = String(value);
      } else if (errorMatch) {
        const evaluator = errorMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        // Ensure error is always a string (CSV parser may convert "0E0" to number 0)
        metrics[evaluator].error = String(value);
      } else if (traceIdMatch) {
        const evaluator = traceIdMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        // Ensure traceId is always a string
        metrics[evaluator].traceId = String(value);
      } else if (spanIdMatch) {
        const evaluator = spanIdMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        // Ensure spanId is always a string
        metrics[evaluator].spanId = String(value);
      } else if (scoreIdMatch) {
        const evaluator = scoreIdMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        // Ensure scoreId is always a string
        metrics[evaluator].scoreId = String(value);
      } else if (statusMatch) {
        const evaluator = statusMatch[1];
        if (!metrics[evaluator]) {
          metrics[evaluator] = { evaluator };
        }
        // Ensure status is always a string
        metrics[evaluator].status = String(value);
      }
    }

    return Object.values(metrics);
  }

  /**
   * Parse a score value from CSV.
   * Handles numeric, boolean, and string scores.
   *
   * @param value - The score value
   * @returns Parsed score value
   */
  private parseScoreValue(value: any): number | string | boolean {
    // Try to parse as number
    if (typeof value === 'number') {
      return value;
    }

    if (typeof value === 'string') {
      // Try to parse as boolean
      if (value.toLowerCase() === 'true') {
        return true;
      }
      if (value.toLowerCase() === 'false') {
        return false;
      }

      // Try to parse as number
      const num = parseFloat(value);
      if (!isNaN(num)) {
        return num;
      }

      // Return as string
      return value;
    }

    if (typeof value === 'boolean') {
      return value;
    }

    return value;
  }
}
