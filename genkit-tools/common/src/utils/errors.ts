// genkit-tools/common/src/utils/errors.ts

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

  // Handle plain objects with a code property (Bun fetch errors)
  if (typeof error === 'object' && 'code' in error) {
    const code = (error as any).code;
    if (
      code === 'ECONNREFUSED' || // Node.js
      code === 'ConnectionRefused' || // Bun
      code === 'ECONNRESET' // Connection reset (also indicates server is down)
    ) {
      return true;
    }
  }

  // Handle Error instances
  if (error instanceof Error) {
    // Direct error code
    if ('code' in error && typeof error.code === 'string') {
      const code = error.code;
      if (
        code === 'ECONNREFUSED' ||
        code === 'ConnectionRefused' ||
        code === 'ECONNRESET'
      ) {
        return true;
      }
    }

    // Node.js style with cause
    if (
      'cause' in error &&
      error.cause &&
      typeof error.cause === 'object' &&
      'code' in error.cause &&
      error.cause.code === 'ECONNREFUSED'
    ) {
      return true;
    }

    // Fallback: check error message
    if (
      error.message &&
      (error.message.includes('ECONNREFUSED') ||
        error.message.includes('Connection refused') ||
        error.message.includes('ConnectionRefused') ||
        error.message.includes('connect ECONNREFUSED'))
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Gets the error code from an error object, handling both Node.js and Bun styles.
 */
export function getErrorCode(error: unknown): string | undefined {
  if (!error) {
    return undefined;
  }

  // Handle plain objects with a code property
  if (
    typeof error === 'object' &&
    'code' in error &&
    typeof (error as any).code === 'string'
  ) {
    return (error as any).code;
  }

  // Handle Error instances
  if (error instanceof Error) {
    // Direct error code
    if ('code' in error && typeof error.code === 'string') {
      return error.code;
    }

    // Node.js style with cause
    if (
      'cause' in error &&
      error.cause &&
      typeof error.cause === 'object' &&
      'code' in error.cause &&
      typeof error.cause.code === 'string'
    ) {
      return error.cause.code;
    }
  }

  return undefined;
}

/**
 * Safely extracts error details for logging.
 */
export function getErrorDetails(error: unknown): string {
  if (!error) {
    return 'Unknown error';
  }

  const code = getErrorCode(error);

  if (error instanceof Error) {
    return code ? `${error.message} (${code})` : error.message;
  }

  if (typeof error === 'object' && 'message' in error) {
    const message = (error as any).message;
    return code ? `${message} (${code})` : message;
  }

  return String(error);
}
