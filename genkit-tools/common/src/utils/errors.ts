/**
 * Copyright 2025 Google LLC
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

// Connection error codes for different runtimes
const CONNECTION_ERROR_CODES = {
  NODE_ECONNREFUSED: 'ECONNREFUSED',
  BUN_CONNECTION_REFUSED: 'ConnectionRefused',
  ECONNRESET: 'ECONNRESET',
} as const;

const CONNECTION_ERROR_PATTERNS = [
  'ECONNREFUSED',
  'Connection refused',
  'ConnectionRefused',
  'connect ECONNREFUSED',
] as const;

type ErrorWithCode = {
  code?: string;
  message?: string;
  cause?: ErrorWithCode;
};

/**
 * Checks if an error is a connection refused error across Node.js and Bun runtimes.
 *
 * Node.js structure: error.cause.code === 'ECONNREFUSED'
 * Bun structure: error.code === 'ConnectionRefused' or error.code === 'ECONNRESET'
 */
export function isConnectionRefusedError(error: unknown): boolean {
  if (!error) {
    return false;
  }

  const errorCode = getErrorCode(error);
  if (errorCode && isConnectionErrorCode(errorCode)) {
    return true;
  }

  // Fallback: check error message
  if (isErrorWithMessage(error)) {
    return CONNECTION_ERROR_PATTERNS.some((pattern) =>
      error.message.includes(pattern)
    );
  }

  return false;
}

/**
 * Helper function to check if a code is a connection error code.
 */
function isConnectionErrorCode(code: string): boolean {
  return Object.values(CONNECTION_ERROR_CODES).includes(
    code as (typeof CONNECTION_ERROR_CODES)[keyof typeof CONNECTION_ERROR_CODES]
  );
}

/**
 * Type guard to check if an error has a message property.
 */
function isErrorWithMessage(error: unknown): error is { message: string } {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof (error as any).message === 'string'
  );
}

/**
 * Extracts error code from an object, handling nested structures.
 */
function extractErrorCode(obj: unknown): string | undefined {
  if (
    typeof obj === 'object' &&
    obj !== null &&
    'code' in obj &&
    typeof (obj as ErrorWithCode).code === 'string'
  ) {
    return (obj as ErrorWithCode).code;
  }
  return undefined;
}

/**
 * Gets the error code from an error object, handling both Node.js and Bun styles.
 */
export function getErrorCode(error: unknown): string | undefined {
  if (!error) {
    return undefined;
  }

  // Direct error code
  const directCode = extractErrorCode(error);
  if (directCode) {
    return directCode;
  }

  // Node.js style with cause
  if (typeof error === 'object' && error !== null && 'cause' in error) {
    const causeCode = extractErrorCode((error as ErrorWithCode).cause);
    if (causeCode) {
      return causeCode;
    }
  }

  return undefined;
}

/**
 * Extracts error message from various error formats.
 */
function extractErrorMessage(error: unknown): string | undefined {
  if (error instanceof Error) {
    return error.message;
  }

  if (isErrorWithMessage(error)) {
    return error.message;
  }

  return undefined;
}

/**
 * Safely extracts error details for logging.
 */
export function getErrorDetails(error: unknown): string {
  if (error === null || error === undefined) {
    return 'Unknown error';
  }

  const code = getErrorCode(error);
  const message = extractErrorMessage(error);

  if (message) {
    return code ? `${message} (${code})` : message;
  }

  return String(error);
}
