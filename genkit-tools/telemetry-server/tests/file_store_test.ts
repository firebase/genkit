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

import type { TraceData, TraceQueryFilter } from '@genkit-ai/tools-common';
import * as assert from 'assert';
import getPort from 'get-port';
import { afterEach, beforeEach, describe, it } from 'node:test';
import os from 'os';
import path from 'path';
import {
  LocalFileTraceStore,
  startTelemetryServer,
  stopTelemetryApi,
} from '../src/index';
import { Index } from '../src/localFileTraceStore';
import { sleep, span } from './utils';

const TRACE_ID = '1234';
const TRACE_ID_1 = '1234';
const TRACE_ID_2 = '2345';
const TRACE_ID_3 = '3456';
const SPAN_A = 'abc';
const SPAN_B = 'bcd';
const SPAN_C = 'cde';

describe('local-file-store', () => {
  let port;
  let storeRoot;
  let indexRoot;
  let url;

  beforeEach(async () => {
    port = await getPort();
    url = `http://localhost:${port}`;
    storeRoot = path.resolve(
      os.tmpdir(),
      `./telemetry-server-api-test-${Date.now()}/traces`
    );
    indexRoot = path.resolve(
      os.tmpdir(),
      `./telemetry-server-api-test-${Date.now()}/traces_idx`
    );

    await startTelemetryServer({
      port,
      traceStore: new LocalFileTraceStore({
        storeRoot,
        indexRoot,
      }),
    });
  });

  afterEach(async () => {
    await stopTelemetryApi();
  });

  it('writes traces', async () => {
    const traceData = {
      traceId: TRACE_ID,
      displayName: 'trace',
      spans: { [SPAN_A]: span(TRACE_ID, SPAN_A, 100, 100) },
    } as TraceData;
    const res = await fetch(`${url}/api/traces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(traceData),
    });
    assert.strictEqual(res.status, 200);

    await assertTraceData(TRACE_ID, traceData);
  });

  it('uppends spans to the trace', async () => {
    const spanA = span(TRACE_ID, SPAN_A, 100, 100);
    const spanB = span(TRACE_ID, SPAN_B, 200, 200);
    const res1 = await fetch(`${url}/api/traces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        traceId: TRACE_ID,
        spans: { [SPAN_A]: spanA },
      } as TraceData),
    });
    assert.strictEqual(res1.status, 200);
    const res2 = await fetch(`${url}/api/traces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        traceId: TRACE_ID,
        spans: { [SPAN_B]: spanB },
      } as TraceData),
    });
    assert.strictEqual(res2.status, 200);

    await assertTraceData(TRACE_ID, {
      traceId: TRACE_ID,
      spans: {
        [SPAN_A]: spanA,
        [SPAN_B]: spanB,
      },
    });
  });

  it('updated final trace data', async () => {
    const spanA = span(TRACE_ID, SPAN_A, 100, 100);
    const spanB = span(TRACE_ID, SPAN_B, 200, 200);
    const res1 = await fetch(`${url}/api/traces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        traceId: TRACE_ID,
        spans: { [SPAN_A]: spanA },
      }),
    });
    assert.strictEqual(res1.status, 200);

    await assertTraceData(TRACE_ID, {
      traceId: TRACE_ID,
      spans: {
        [SPAN_A]: spanA,
      },
    } as TraceData);

    const res2 = await fetch(`${url}/api/traces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        traceId: TRACE_ID,
        displayName: 'final display name',
        startTime: 111,
        endTime: 999,
        spans: { [SPAN_B]: spanB },
      }),
    });
    assert.strictEqual(res2.status, 200);

    await assertTraceData(TRACE_ID, {
      traceId: TRACE_ID,
      displayName: 'final display name',
      startTime: 111,
      endTime: 999,
      spans: {
        [SPAN_A]: spanA,
        [SPAN_B]: spanB,
      },
    });
  });

  it('lists trace data', async () => {
    const wantTraces = [] as TraceData[];
    for (let i = 0; i < 3; i++) {
      const spanId = `abc_${i}`;
      const traceId = TRACE_ID + `_${i}`;
      const spanData = span(traceId, spanId, 100 + i, 100 + i);
      const trace = {
        traceId: traceId,
        displayName: 'trace',
        spans: { [spanId]: spanData },
      };
      wantTraces.push(trace);

      const res = await fetch(`${url}/api/traces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trace),
      });
      assert.strictEqual(res.status, 200);
      await sleep(1); // sleep a little to ensure consistent chronological ordering
    }

    const getResp = await fetch(`${url}/api/traces`);
    assert.strictEqual(getResp.status, 200);
    const tracesResponse = await getResp.json();
    assert.deepStrictEqual(tracesResponse.traces, wantTraces.reverse());
  });

  it('lists filtered trace data', async () => {
    const wantTraces = [] as TraceData[];
    for (let i = 0; i < 3; i++) {
      const spanId = `abc_${i}`;
      const traceId = TRACE_ID + `_${i}`;
      const spanData = span(traceId, spanId, 100 + i, 100 + i);
      if (i % 2 == 0) {
        spanData.attributes['genkit:type'] = 'banana';
      }
      const trace = {
        traceId: traceId,
        displayName: 'trace',
        spans: { [spanId]: spanData },
      };
      if (i % 2 != 0) {
        wantTraces.push(trace);
      }

      const res = await fetch(`${url}/api/traces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trace),
      });
      assert.strictEqual(res.status, 200);
      await sleep(1); // sleep a little to ensure consistent chronological ordering
    }

    const filter = { neq: { type: 'banana' } } as TraceQueryFilter;
    const getResp = await fetch(
      `${url}/api/traces?filter=${encodeURI(JSON.stringify(filter))}`
    );
    assert.strictEqual(getResp.status, 200);
    const tracesResponse = await getResp.json();
    assert.deepStrictEqual(tracesResponse.traces, wantTraces.reverse());
  });

  it('lists trace data with pagination', async () => {
    const wantTraces = [] as TraceData[];
    for (let i = 0; i < 20; i++) {
      const spanId = `abc_${i}`;
      const traceId = TRACE_ID + `_${i}`;
      const spanData = span(traceId, spanId, 100 + i, 100 + i);
      const trace = {
        traceId: traceId,
        displayName: 'trace',
        spans: { [spanId]: spanData },
      };
      wantTraces.push(trace);

      const res = await fetch(`${url}/api/traces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trace),
      });
      assert.strictEqual(res.status, 200);
      await sleep(1); // sleep a little to ensure consistent chronological ordering
    }
    const pageSize = 4;

    const respP1 = await fetch(`${url}/api/traces?limit=${pageSize}`);
    assert.strictEqual(respP1.status, 200);
    const tracesResponseP1 = await respP1.json();
    assert.deepStrictEqual(
      tracesResponseP1.traces,
      wantTraces.slice(wantTraces.length - pageSize).reverse()
    );

    // continue to page 2
    const respP2 = await fetch(
      `${url}/api/traces?limit=${pageSize}&continuationToken=${tracesResponseP1.continuationToken}`
    );
    assert.strictEqual(respP2.status, 200);
    const tracesResponseP2 = await respP2.json();
    assert.deepStrictEqual(
      tracesResponseP2.traces,
      wantTraces
        .slice(wantTraces.length - pageSize * 2, wantTraces.length - pageSize)
        .reverse()
    );
  });

  async function assertTraceData(traceId: string, traceData: TraceData) {
    const getResp = await fetch(`${url}/api/traces/${traceId}`);
    assert.strictEqual(getResp.status, 200);
    assert.deepStrictEqual(await getResp.json(), traceData);
  }
});

describe('index', () => {
  let indexRoot;
  let index: Index;

  beforeEach(async () => {
    indexRoot = path.resolve(
      os.tmpdir(),
      `./telemetry-server-api-test-${Date.now()}/traces_idx`
    );

    index = new Index(indexRoot);
  });

  it('should index and search spans', () => {
    const spanA = span(TRACE_ID_1, SPAN_A, 100, 100);
    spanA.displayName = 'spanA';
    spanA.startTime = 1234;
    spanA.endTime = 2345;

    const spanB = span(TRACE_ID_2, SPAN_B, 200, 200);
    spanB.displayName = 'spanB';
    spanB.startTime = 2345;
    spanB.endTime = 3456;

    index.add({
      traceId: TRACE_ID_1,
      spans: {
        [SPAN_A]: spanA,
      },
    } as TraceData);
    index.add({
      traceId: TRACE_ID_2,
      spans: {
        [SPAN_B]: spanB,
      },
    } as TraceData);

    assert.deepStrictEqual(index.search({ limit: 5 }).data, [
      {
        id: TRACE_ID_2,
        type: 'flow',
        name: 'spanB',
        start: 2345,
        end: 3456,
        status: 0,
      },
      {
        id: TRACE_ID_1,
        type: 'flow',
        name: 'spanA',
        start: 1234,
        end: 2345,
        status: 0,
      },
    ]);
  });

  it('should apply search filters', () => {
    const spanA = span(TRACE_ID_1, SPAN_A, 100, 100);
    spanA.displayName = 'flowA';
    spanA.attributes['genkit:type'] = 'banana';

    const spanB = span(TRACE_ID_2, SPAN_B, 200, 200);
    spanB.displayName = 'flowA';

    const spanC = span(TRACE_ID_3, SPAN_C, 200, 200);
    spanC.displayName = 'flowB';

    index.add({
      traceId: TRACE_ID_1,
      spans: {
        [SPAN_A]: spanA,
      },
    } as TraceData);
    index.add({
      traceId: TRACE_ID_2,
      spans: {
        [SPAN_B]: spanB,
      },
    } as TraceData);
    index.add({
      traceId: TRACE_ID_3,
      spans: {
        [SPAN_C]: spanC,
      },
    } as TraceData);

    assert.deepStrictEqual(
      index.search({
        limit: 5,
        filter: {
          eq: { name: 'flowA' },
        },
      }).data,
      [
        {
          id: TRACE_ID_2,
          type: 'flow',
          name: 'flowA',
          start: 1,
          end: 2,
          status: 0,
        },
        {
          id: TRACE_ID_1,
          type: 'banana',
          name: 'flowA',
          start: 1,
          end: 2,
          status: 0,
        },
      ]
    );

    assert.deepStrictEqual(
      index.search({
        limit: 5,
        filter: {
          eq: { name: 'flowA', type: 'banana' },
        },
      }).data,
      [
        {
          id: TRACE_ID_1,
          type: 'banana',
          name: 'flowA',
          start: 1,
          end: 2,
          status: 0,
        },
      ]
    );

    assert.deepStrictEqual(
      index.search({
        limit: 5,
        filter: {
          eq: { name: 'flowA' },
          neq: { type: 'banana' },
        },
      }).data,
      [
        {
          id: TRACE_ID_2,
          type: 'flow',
          name: 'flowA',
          start: 1,
          end: 2,
          status: 0,
        },
      ]
    );
  });

  it('can filter out unknown types', () => {
    const spanA = span(TRACE_ID_1, SPAN_A, 100, 100);
    spanA.displayName = 'flowA';
    spanA.attributes['genkit:type'] = 'banana';

    const spanB = span(TRACE_ID_2, SPAN_B, 200, 200);
    spanB.displayName = 'flowB';
    spanB.attributes['genkit:type'] = undefined;

    const spanC = span(TRACE_ID_3, SPAN_C, 200, 200);
    spanC.displayName = 'flowC';
    spanC.attributes['genkit:type'] = undefined;

    index.add({
      traceId: TRACE_ID_1,
      spans: {
        [SPAN_A]: spanA,
      },
    } as TraceData);
    index.add({
      traceId: TRACE_ID_2,
      spans: {
        [SPAN_B]: spanB,
      },
    } as TraceData);
    index.add({
      traceId: TRACE_ID_3,
      spans: {
        [SPAN_C]: spanC,
      },
    } as TraceData);

    assert.deepStrictEqual(
      index.search({
        limit: 5,
        filter: {
          neq: { type: 'UNKNOWN' },
        },
      }).data,
      [
        {
          id: TRACE_ID_1,
          type: 'banana',
          name: 'flowA',
          start: 1,
          end: 2,
          status: 0,
        },
      ]
    );
  });

  it('should paginate search', () => {
    for (let i = 0; i < 20; i++) {
      const traceId = 'trace_' + i;
      const spanId = 'span_' + i;
      const s = span(traceId, spanId, 100 + i, 200 + i);
      s.displayName = 'spanA';
      s.startTime = 1234 + i;
      s.endTime = 2345 + i;

      index.add({
        traceId,
        spans: {
          [spanId]: s,
        },
      } as TraceData);
    }

    const result1 = index.search({ limit: 3 });
    assert.deepStrictEqual(
      result1.data.map((d) => d.id),
      ['trace_19', 'trace_18', 'trace_17']
    );
    assert.strictEqual(result1.pageLastIndex, 3);

    const result2 = index.search({
      limit: 3,
      startFromIndex: result1.pageLastIndex,
    });
    assert.deepStrictEqual(
      result2.data.map((d) => d.id),
      ['trace_16', 'trace_15', 'trace_14']
    );
    assert.strictEqual(result2.pageLastIndex, 6);

    // check edge conditions

    const result3 = index.search({ limit: 3, startFromIndex: 17 });
    assert.deepStrictEqual(
      result3.data.map((d) => d.id),
      ['trace_2', 'trace_1', 'trace_0']
    );
    assert.strictEqual(result3.pageLastIndex, undefined);

    const result4 = index.search({ limit: 10, startFromIndex: 18 });
    assert.deepStrictEqual(
      result4.data.map((d) => d.id),
      ['trace_1', 'trace_0']
    );
    assert.strictEqual(result4.pageLastIndex, undefined);
  });
});
