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

import { Registry } from './registry.js';
import { StatusName } from './statusTypes.js';

/**
 * Base error class for Genkit errors.
 */
export class GenkitError extends Error {
  source?: string;
  status: StatusName;
  detail?: any;

  constructor({
    status,
    message,
    detail,
    source,
  }: {
    status: StatusName;
    message: string;
    detail?: any;
    source?: string;
  }) {
    super(`${source ? `${source}: ` : ''}${status}: ${message}`);
    this.status = status;
    this.detail = detail;
    this.name = 'GenkitError';
  }
}

export class UnstableApiError extends GenkitError {
  constructor(level: 'beta', message?: string) {
    super({
      status: 'FAILED_PRECONDITION',
      message: `${message ? message + ' ' : ''}This API requires '${level}' stability level.\n\nTo use this feature, initialize Genkit using \`import {genkit} from "genkit/${level}"\`.`,
    });
    this.name = 'UnstableApiError';
  }
}

/**
 * assertUnstable allows features to raise exceptions when using Genkit from *more* stable initialized instances.
 *
 * @param level The maximum stability channel allowed.
 * @param message An optional message describing which feature is not allowed.
 */
export function assertUnstable(
  registry: Registry,
  level: 'beta',
  message?: string
) {
  if (level === 'beta' && registry.apiStability === 'stable') {
    throw new UnstableApiError(level, message);
  }
}

/**
 * Extracts error message from the given error object, or if input is not an error then just turn the error into a string.
 */
export function getErrorMessage(e: any): string {
  if (e instanceof Error) {
    return e.message;
  }
  return `${e}`;
}

/**
 * Extracts stack trace from the given error object, or if input is not an error then returns undefined.
 */
export function getErrorStack(e: any): string | undefined {
  if (e instanceof Error) {
    return e.stack;
  }
  return undefined;
}
