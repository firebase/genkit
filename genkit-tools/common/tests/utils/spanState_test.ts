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

import { backfillSpanStates } from '../../src/utils/spanState';
import type { TraceData } from '../../src/types/trace';

function buildTrace(spans: TraceData['spans']): TraceData {
  return {
    traceId: 'trace-1',
    displayName: 'test-trace',
    spans,
  };
}

function buildSpan(overrides: Partial<TraceData['spans'][string]> = {}) {
  return {
    spanId: 'span-1',
    traceId: 'trace-1',
    startTime: 0,
    endTime: 1,
    attributes: {},
    displayName: 'span',
    instrumentationLibrary: { name: 'test' },
    spanKind: 'INTERNAL',
    ...overrides,
  };
}

describe('backfillSpanStates', () => {
  it('does nothing when span already has a genkit:state', () => {
    const trace = buildTrace({
      a: buildSpan({ attributes: { 'genkit:state': 'success' } }),
    });

    const result = backfillSpanStates(trace);

    expect(result.spans.a.attributes['genkit:state']).toBe('success');
  });

  it('does nothing when span has genkit:metadata:flow:state', () => {
    const trace = buildTrace({
      a: buildSpan({ attributes: { 'genkit:metadata:flow:state': 'run' } }),
    });

    const result = backfillSpanStates(trace);

    expect(result.spans.a.attributes['genkit:state']).toBeUndefined();
  });

  it('marks spans with StatusCode.ERROR as error', () => {
    const trace = buildTrace({
      a: buildSpan({ status: { code: 2 } }),
    });

    const result = backfillSpanStates(trace);

    expect(result.spans.a.attributes['genkit:state']).toBe('error');
  });

  it('marks spans with StatusCode.OK as success', () => {
    const trace = buildTrace({
      a: buildSpan({ status: { code: 1 } }),
    });

    const result = backfillSpanStates(trace);

    expect(result.spans.a.attributes['genkit:state']).toBe('success');
  });

  it('marks spans with StatusCode.UNSET (or other codes) as unknown', () => {
    const trace = buildTrace({
      a: buildSpan({ status: { code: 0 } }),
    });

    const result = backfillSpanStates(trace);

    expect(result.spans.a.attributes['genkit:state']).toBe('unknown');
  });
});
