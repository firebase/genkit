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
 * Deletes any properties with `undefined` values in the provided object.
 * Modifies the provided object.
 */
export function deleteUndefinedProps(obj: any) {
  for (const prop in obj) {
    if (obj[prop] === undefined) {
      delete obj[prop];
    } else {
      if (typeof obj[prop] === 'object') {
        deleteUndefinedProps(obj[prop]);
      }
    }
  }
}

/**
 * Strips (non distructively) any properties with `undefined` values in the provided object and returns
 */
export function stripUndefinedProps<T>(input: T): T {
  if (
    input === undefined ||
    input === null ||
    Array.isArray(input) ||
    typeof input !== 'object'
  ) {
    return input;
  }
  const out = {} as T;
  for (const key in input) {
    if (input[key] !== undefined) {
      out[key] = stripUndefinedProps(input[key]);
    }
  }
  return out;
}

/**
 * Returns the current environment that the app code is running in.
 *
 * @hidden
 */
export function getCurrentEnv(): string {
  return process.env.GENKIT_ENV || 'prod';
}

/**
 * Whether the current environment is `dev`.
 */
export function isDevEnv(): boolean {
  return getCurrentEnv() === 'dev';
}

/**
 * Adds flow-specific prefix for OpenTelemetry span attributes.
 */
export function featureMetadataPrefix(name: string) {
  return `feature:${name}`;
}
