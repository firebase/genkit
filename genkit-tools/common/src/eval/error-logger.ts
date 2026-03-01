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

import type { ParseError } from './file-parser';

/**
 * Error log entry with detailed information.
 */
export interface ErrorLogEntry {
  /** Timestamp when the error occurred */
  timestamp: string;
  /** Error type (e.g., 'ParseError', 'FileReadError', 'ValidationError') */
  type: string;
  /** Error message */
  message: string;
  /** Additional error details */
  details?: string;
  /** Missing fields (for validation errors) */
  missingFields?: string[];
  /** File name that caused the error */
  fileName?: string;
  /** File size in bytes */
  fileSize?: number;
  /** File type/extension */
  fileType?: string;
  /** Stack trace (if available) */
  stackTrace?: string;
}

/**
 * Error logger for tracking and debugging file upload/parsing errors.
 *
 * Logs detailed error information to the console for debugging purposes.
 * In production, this could be extended to send logs to a monitoring service.
 */
export class ErrorLogger {
  private static logs: ErrorLogEntry[] = [];
  private static maxLogs = 100; // Keep last 100 errors

  /**
   * Log a parsing error with detailed information.
   *
   * @param error - The error to log
   * @param file - Optional file that caused the error
   */
  static logParseError(error: ParseError | Error, file?: File): void {
    const entry: ErrorLogEntry = {
      timestamp: new Date().toISOString(),
      type: this.getErrorType(error),
      message: error instanceof Error ? error.message : error.message,
      details: error instanceof Error ? undefined : error.details,
      missingFields: error instanceof Error ? undefined : error.missingFields,
      fileName: file?.name,
      fileSize: file?.size,
      fileType: file?.type || this.getFileExtension(file?.name),
      stackTrace: error instanceof Error ? error.stack : undefined,
    };

    // Add to logs
    this.logs.push(entry);

    // Trim logs if exceeding max
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // Log to console for debugging
    console.error('[ErrorLogger] Parse error:', entry);
  }

  /**
   * Log a file read error.
   *
   * @param error - The error that occurred
   * @param file - The file that failed to read
   */
  static logFileReadError(error: Error, file: File): void {
    const entry: ErrorLogEntry = {
      timestamp: new Date().toISOString(),
      type: 'FileReadError',
      message: error.message,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type || this.getFileExtension(file.name),
      stackTrace: error.stack,
    };

    this.logs.push(entry);

    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    console.error('[ErrorLogger] File read error:', entry);
  }

  /**
   * Log a validation error.
   *
   * @param message - Error message
   * @param missingFields - List of missing fields
   * @param file - Optional file that failed validation
   */
  static logValidationError(
    message: string,
    missingFields: string[],
    file?: File
  ): void {
    const entry: ErrorLogEntry = {
      timestamp: new Date().toISOString(),
      type: 'ValidationError',
      message,
      missingFields,
      fileName: file?.name,
      fileSize: file?.size,
      fileType: file?.type || this.getFileExtension(file?.name),
    };

    this.logs.push(entry);

    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    console.error('[ErrorLogger] Validation error:', entry);
  }

  /**
   * Get all logged errors.
   *
   * @returns Array of error log entries
   */
  static getLogs(): ErrorLogEntry[] {
    return [...this.logs];
  }

  /**
   * Clear all logged errors.
   */
  static clearLogs(): void {
    this.logs = [];
  }

  /**
   * Get the most recent error log entry.
   *
   * @returns Most recent error log entry or undefined
   */
  static getLastError(): ErrorLogEntry | undefined {
    return this.logs[this.logs.length - 1];
  }

  /**
   * Export logs as JSON string for debugging.
   *
   * @returns JSON string of all logs
   */
  static exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  /**
   * Determine error type from error object.
   *
   * @param error - The error object
   * @returns Error type string
   */
  private static getErrorType(error: ParseError | Error): string {
    if (error instanceof Error) {
      return error.name || 'Error';
    }

    const message = error.message.toLowerCase();

    if (message.includes('json')) {
      return 'JSONParseError';
    }

    if (message.includes('csv')) {
      return 'CSVParseError';
    }

    if (message.includes('missing') || message.includes('required')) {
      return 'ValidationError';
    }

    if (message.includes('empty')) {
      return 'EmptyFileError';
    }

    if (message.includes('unsupported')) {
      return 'UnsupportedFormatError';
    }

    return 'ParseError';
  }

  /**
   * Extract file extension from filename.
   *
   * @param fileName - The file name
   * @returns File extension or undefined
   */
  private static getFileExtension(fileName?: string): string | undefined {
    if (!fileName) return undefined;
    const parts = fileName.split('.');
    return parts.length > 1 ? `.${parts[parts.length - 1]}` : undefined;
  }
}
