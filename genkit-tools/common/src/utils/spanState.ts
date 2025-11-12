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

import type { SpanData, TraceData } from '../types';

const GENKIT_STATE_ATTR = 'genkit:state';
const GENKIT_FLOW_STATE_ATTR = 'genkit:metadata:flow:state';

/**
 * Backfills genkit span state attributes from OpenTelemetry status codes so the
 * Dev UI can render accurate success/error indicators even when spans are
 * emitted by auto-instrumentations that don't set genkit-specific attributes.
 */
export function backfillSpanStates(trace: TraceData): TraceData {
  if (!trace.spans) {
    return trace;
  }

  Object.values(trace.spans).forEach((span) => {
    if (hasExplicitState(span)) {
      return;
    }

    const derivedState = deriveStateFromStatus(span.status?.code);
    if (!derivedState) {
      return;
    }

    span.attributes[GENKIT_STATE_ATTR] = derivedState;
  });

  return trace;
}

function hasExplicitState(span: SpanData): boolean {
  return Boolean(
    span.attributes[GENKIT_STATE_ATTR] ||
      span.attributes[GENKIT_FLOW_STATE_ATTR]
  );
}

function deriveStateFromStatus(
  code?: number
): 'success' | 'error' | 'unknown' | undefined {
  if (code === undefined) {
    return undefined;
  }

  switch (code) {
    case 2:
      return 'error';
    case 1:
      return 'success';
    default:
      return 'unknown';
  }
}
