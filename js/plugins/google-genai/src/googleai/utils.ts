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

import { GenkitError } from 'genkit';
import process from 'process';

export { extractImagenImage, extractText, modelName } from '../common/utils.js';

/**
 * Retrieves an API key from environment variables.
 *
 * @returns The API key as a string, or `undefined` if none of the specified
 *          environment variables are set.
 */
export function getApiKeyFromEnvVar(): string | undefined {
  return (
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY ||
    process.env.GOOGLE_GENAI_API_KEY
  );
}

export const MISSING_API_KEY_ERROR = new GenkitError({
  status: 'FAILED_PRECONDITION',
  message:
    'Please pass in the API key or set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.\n' +
    'For more details see https://firebase.google.com/docs/genkit/plugins/google-genai',
});

export const API_KEY_FALSE_ERROR = new GenkitError({
  status: 'INVALID_ARGUMENT',
  message:
    'GoogleAI plugin was initialized with {apiKey: false} but no apiKey configuration was passed at call time.',
});

/**
 * Checks and retrieves an API key based on the provided argument and environment variables.
 *
 * - If `apiKey1` is a non-empty string, it's used as the API key.
 * - If `apiKey1` is `undefined` or an empty string, it attempts to fetch the API key from environment
 * - If `apiKey1` is `false`, key retrieval from the environment is skipped, and the function
 *   will return `undefined`. This mode indicates that the API key is expected to be provided
 *   at a later stage or in a different context.
 *
 * @param apiKey1 - An optional API key string, `undefined` to check the environment, or `false` to bypass all checks in this function.
 * @returns The resolved API key as a string, or `undefined` if `apiKey1` is `false`.
 * @throws {Error} MISSING_API_KEY_ERROR - Thrown if `apiKey1` is not `false` and no API key
 *   can be found either in the `apiKey1` argument or from the environment.
 */
export function checkApiKey(
  apiKey1: string | false | undefined
): string | undefined {
  let apiKey: string | undefined;

  // Don't get the key from the environment if apiKey1 is false
  if (apiKey1 !== false) {
    apiKey = apiKey1 || getApiKeyFromEnvVar();
  }

  // If apiKey1 is false, then we don't throw because we are waiting for
  // the apiKey passed into the individual call
  if (apiKey1 !== false && !apiKey) {
    throw MISSING_API_KEY_ERROR;
  }
  return apiKey;
}

/**
 * Calculates and returns the effective API key based on multiple potential sources.
 * The order of precedence for determining the API key is:
 * 1. `apiKey2` (if provided)
 * 2. `apiKey1` (if provided and not `false`)
 * 3. Environment variable (if `apiKey1` is not `false` and `apiKey1` is not provided)
 *
 * @param apiKey1 - The apiKey value provided during plugin initialization.
 * @param apiKey2 - The apiKey provided to an individual generate call.
 * @returns The resolved API key as a string.
 * @throws {Error} API_KEY_FALSE_ERROR - Thrown if `apiKey1` is `false` and `apiKey2` is not provided
 * @throws {Error} MISSING_API_KEY_ERROR - Thrown if no API key can be resolved from any source
 */
export function calculateApiKey(
  apiKey1: string | false | undefined,
  apiKey2: string | undefined
): string {
  let apiKey: string | undefined;

  // Don't get the key from the environment if apiKey1 is false
  if (apiKey1 !== false) {
    apiKey = apiKey1 || getApiKeyFromEnvVar();
  }

  apiKey = apiKey2 || apiKey;

  if (apiKey1 === false && !apiKey2) {
    throw API_KEY_FALSE_ERROR;
  }

  if (!apiKey) {
    throw MISSING_API_KEY_ERROR;
  }
  return apiKey;
}
