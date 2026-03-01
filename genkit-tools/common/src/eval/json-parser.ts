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

import type { EvalResult, EvalRun, EvalRunKey } from '../types/eval';
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
 * Parser for JSON-formatted evaluation result files.
 *
 * Supports two JSON structures:
 * 1. EvalRun object with key and results
 * 2. Raw array of EvalResult objects
 */
export class JsonParser implements FileParser {
  /**
   * Parse a JSON file containing evaluation results.
   *
   * @param file - The JSON file to parse
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

      // Parse JSON
      let parsed: any;
      try {
        parsed = JSON.parse(content);
      } catch (error) {
        return createErrorResult(
          createParseError(
            'Invalid JSON format',
            error instanceof Error ? error.message : 'Failed to parse JSON'
          )
        );
      }

      // Detect structure and extract data
      const { data, metadata } = this.extractEvaluationData(parsed);

      // Validate data
      if (!Array.isArray(data)) {
        return createErrorResult(
          createParseError(
            'Unrecognized file structure',
            'Expected EvalRun object or array of EvalResult objects'
          )
        );
      }

      // Check for empty results
      if (data.length === 0 && !(config?.allowEmpty ?? false)) {
        return createErrorResult(
          createParseError(
            'File contains no evaluation results',
            'The results array is empty'
          )
        );
      }

      // Validate required fields if enabled
      if (config?.validateRequiredFields ?? true) {
        const requiredFields = config?.requiredFields ?? [
          'testCaseId',
          'input',
          'output',
        ];

        for (let i = 0; i < data.length; i++) {
          const result = data[i];
          const missingFields = validateRequiredFields(result, requiredFields);

          if (missingFields.length > 0) {
            return createErrorResult(
              createParseError(
                `Invalid evaluation data: Missing required fields: ${missingFields.join(', ')}`,
                `Result at index ${i} is missing required fields: ${missingFields.join(', ')}`,
                missingFields
              )
            );
          }
        }
      }

      return createSuccessResult(data, metadata);
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
   * Extract evaluation data from parsed JSON.
   *
   * Detects whether the JSON is an EvalRun object or a raw array of results.
   *
   * @param parsed - The parsed JSON object
   * @returns Object containing data array and optional metadata
   */
  private extractEvaluationData(parsed: any): {
    data: EvalResult[];
    metadata?: EvalRunKey;
  } {
    // Check if it's an EvalRun structure (has key and results)
    if (
      parsed &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed) &&
      'key' in parsed &&
      'results' in parsed
    ) {
      const evalRun = parsed as EvalRun;
      return {
        data: evalRun.results,
        metadata: evalRun.key,
      };
    }

    // Check if it's a raw array of results
    if (Array.isArray(parsed)) {
      return {
        data: parsed as EvalResult[],
      };
    }

    // Unrecognized structure
    return {
      data: [] as EvalResult[],
    };
  }
}
