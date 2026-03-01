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

import type { EvalResult, EvalRunKey } from '../types/eval';

/**
 * Error information for file parsing failures.
 *
 * Provides detailed information about what went wrong during parsing,
 * including specific missing fields and additional context.
 */
export interface ParseError {
  /** Human-readable error message describing the issue */
  message: string;
  /** Additional details about the error (e.g., stack trace, line numbers) */
  details?: string;
  /** List of required field names that are missing from the data */
  missingFields?: string[];
}

/**
 * Result of parsing an evaluation results file.
 *
 * Contains either the successfully parsed data or error information.
 */
export interface ParseResult {
  /** Whether the parsing operation succeeded */
  success: boolean;
  /** Parsed evaluation results (present when success is true) */
  data?: EvalResult[];
  /** Evaluation run metadata (present when available in the file) */
  metadata?: EvalRunKey;
  /** Error information (present when success is false) */
  error?: ParseError;
}

/**
 * Configuration options for file parsers.
 *
 * Allows customization of parsing behavior and validation rules.
 */
export interface ParserConfig {
  /** Whether to validate required fields (default: true) */
  validateRequiredFields?: boolean;
  /** Custom list of required field names (overrides defaults) */
  requiredFields?: string[];
  /** Whether to allow empty files (default: false) */
  allowEmpty?: boolean;
}

/**
 * Base interface for file parsers.
 *
 * Implementations should handle specific file formats (JSON, CSV, etc.)
 * and transform them into the standard EvalResult[] format.
 */
export interface FileParser {
  /**
   * Parse an evaluation results file.
   *
   * @param file - The file to parse
   * @param config - Optional parser configuration
   * @returns Promise resolving to ParseResult with data or error
   */
  parse(file: File, config?: ParserConfig): Promise<ParseResult>;
}

/**
 * Validates that an evaluation result contains all required fields.
 *
 * @param result - The evaluation result to validate
 * @param requiredFields - List of required field names (defaults to standard fields)
 * @returns Array of missing field names (empty if all required fields are present)
 */
export function validateRequiredFields(
  result: any,
  requiredFields: string[] = ['testCaseId', 'input', 'output']
): string[] {
  const missing: string[] = [];

  for (const field of requiredFields) {
    if (result[field] === undefined) {
      missing.push(field);
    }
  }

  return missing;
}

/**
 * Creates a descriptive error message for parsing failures.
 *
 * @param message - Base error message
 * @param details - Optional additional details
 * @param missingFields - Optional list of missing field names
 * @returns Formatted ParseError object
 */
export function createParseError(
  message: string,
  details?: string,
  missingFields?: string[]
): ParseError {
  return {
    message,
    details,
    missingFields,
  };
}

/**
 * Creates a successful ParseResult.
 *
 * @param data - Parsed evaluation results
 * @param metadata - Optional evaluation run metadata
 * @returns ParseResult with success=true
 */
export function createSuccessResult(
  data: EvalResult[],
  metadata?: EvalRunKey
): ParseResult {
  return {
    success: true,
    data,
    metadata,
  };
}

/**
 * Creates a failed ParseResult.
 *
 * @param error - Error information
 * @returns ParseResult with success=false
 */
export function createErrorResult(error: ParseError): ParseResult {
  return {
    success: false,
    error,
  };
}
