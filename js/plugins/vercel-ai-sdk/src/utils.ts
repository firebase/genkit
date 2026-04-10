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

import type { FinishReason } from 'ai';
import { getHttpStatus } from 'genkit/context';

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

/** Convert a Fetch API `Headers` object to a plain `Record<string, string>`. */
export function headersToRecord(headers: Headers): Record<string, string> {
  const out: Record<string, string> = {};
  headers.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

/**
 * `getHttpStatus` only handles `GenkitError`; also accept plain
 * `{ status: number }` errors (e.g. from custom context providers).
 */
export function resolveStatus(err: unknown): number {
  const s = getHttpStatus(err);
  if (s !== 500) return s;
  const plain = (err as any)?.status;
  return typeof plain === 'number' && plain >= 100 && plain < 600 ? plain : 500;
}

// ---------------------------------------------------------------------------
// Finish reason normalisation
// ---------------------------------------------------------------------------

const VALID_FINISH_REASONS: readonly FinishReason[] = [
  'stop',
  'length',
  'content-filter',
  'tool-calls',
  'error',
  'other',
];

/** Map an arbitrary Genkit `finishReason` string to a known AI SDK value, or `undefined`. */
export function normalizeFinishReason(
  reason: string | undefined
): FinishReason | undefined {
  if (reason == null) return undefined;
  if ((VALID_FINISH_REASONS as string[]).includes(reason))
    return reason as FinishReason;
  if (reason === 'blocked') return 'content-filter';
  if (reason === 'unknown') return 'other';
  return undefined;
}
