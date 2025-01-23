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

import * as assert from 'assert';
import { describe, it } from 'node:test';
import { rebatchSpans } from '../src/firestoreTraceStore';

const TRACE_ID = '1234';
const SPAN_A = 'abc';
const SPAN_B = 'bcd';
const SPAN_C = 'cde';

describe('rebatchSpans', () => {
  it('batches all small spans together', async () => {
    const batches = rebatchSpans({
      traceId: TRACE_ID,
      spans: {
        [SPAN_A]: span(TRACE_ID, SPAN_A, 100, 100),
        [SPAN_B]: span(TRACE_ID, SPAN_B, 100, 100),
      },
    });
    assert.deepEqual(batches, [
      {
        [SPAN_A]: span(TRACE_ID, SPAN_A, 100, 100),
        [SPAN_B]: span(TRACE_ID, SPAN_B, 100, 100),
      },
    ]);
  });

  it('moves large span into a separate batch', async () => {
    const batches = rebatchSpans({
      traceId: TRACE_ID,
      spans: {
        [SPAN_A]: span(TRACE_ID, SPAN_A, 100, 100),
        [SPAN_B]: span(TRACE_ID, SPAN_B, 100_000, 100_000),
        [SPAN_C]: span(TRACE_ID, SPAN_C, 400_000, 400_000),
      },
    });
    assert.deepEqual(batches, [
      {
        [SPAN_A]: span(TRACE_ID, SPAN_A, 100, 100),
        [SPAN_B]: span(TRACE_ID, SPAN_B, 100_000, 100_000),
      },
      {
        [SPAN_C]: span(TRACE_ID, SPAN_C, 400_000, 400_000),
      },
    ]);
  });

  it('truncates output first', async () => {
    const batches = rebatchSpans({
      traceId: TRACE_ID,
      spans: {
        [SPAN_A]: span(TRACE_ID, SPAN_A, 100, 1_000_000),
      },
    });
    assert.deepStrictEqual(batches, [
      {
        [SPAN_A]: {
          ...span(TRACE_ID, SPAN_A, 100, undefined),
          truncated: true,
        },
      },
    ]);
  });

  it('truncates both output and input if both are too big', async () => {
    const batches = rebatchSpans({
      traceId: TRACE_ID,
      spans: {
        [SPAN_A]: span(TRACE_ID, SPAN_A, 1_100_000, 1_100_000),
      },
    });
    assert.deepStrictEqual(batches, [
      {
        [SPAN_A]: {
          ...span(TRACE_ID, SPAN_A, undefined, undefined),
          truncated: true,
        },
      },
    ]);
  });
});

function span(
  traceId: string,
  id: string,
  inputLength: number | undefined,
  outputLength: number | undefined
) {
  const attributes = {
    'genkit:type': 'flow',
  };
  if (inputLength) {
    attributes['genkit:input'] = generateString(inputLength);
  }
  if (outputLength) {
    attributes['genkit:output'] = generateString(outputLength);
  }
  return {
    traceId: traceId,
    spanId: id,
    displayName: `Span ${id}`,
    startTime: 1,
    endTime: 2,
    instrumentationLibrary: { name: 'genkit' },
    spanKind: 'INTERNAL',
    attributes,
  };
}

function generateString(length: number) {
  let str = '';
  while (str.length < length) {
    str += 'blah ';
  }
  return str.substring(0, length);
}
