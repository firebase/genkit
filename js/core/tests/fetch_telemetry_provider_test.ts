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
 *
 * Run just this file:
 *   npm test -- --test-name-pattern FetchTelemetryProvider
 * Or from repo js/core:
 *   node --import tsx --test tests/fetch_telemetry_provider_test.ts
 *
 * Manual test with dev UI: set GENKIT_TELEMETRY_SERVER to your telemetry server URL
 * (e.g. from `genkit start`), use FetchTelemetryProvider in your app, run a flow,
 * then open the dev UI and confirm the trace appears.
 */

import { trace } from '@opentelemetry/api';
import * as assert from 'node:assert';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { FetchTelemetryProvider } from '../src/tracing/fetch-telemetry-provider.js';
import { sleep } from './utils.js';

describe('FetchTelemetryProvider', () => {
  const capturedRequests: {
    url: string;
    body: unknown;
    headers: Record<string, string>;
  }[] = [];
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    capturedRequests.length = 0;
    originalFetch = globalThis.fetch;
    globalThis.fetch = async (
      url: string | URL | Request,
      init?: RequestInit
    ) => {
      const req = url instanceof Request ? url : new Request(url, init);
      const urlStr = req.url;
      if (urlStr.includes('/api/traces')) {
        const body =
          req.method === 'POST' && req.body
            ? JSON.parse(await req.text())
            : undefined;
        const headers: Record<string, string> = {};
        req.headers.forEach((v, k) => {
          headers[k] = v;
        });
        capturedRequests.push({ url: urlStr, body, headers });
        return new Response('OK', { status: 200 });
      }
      return originalFetch(url, init);
    };
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('enables telemetry and exports spans via fetch when serverUrl is set', async () => {
    const serverUrl = 'http://telemetry.test';
    const provider = new FetchTelemetryProvider({
      serverUrl,
      realtime: true, // SimpleSpanProcessor so export happens on span end
    });

    await provider.enableTelemetry({});

    const tracer = trace.getTracer('test', '1.0');
    tracer.startActiveSpan('testSpan', {}, (span) => {
      span.end();
    });

    await provider.flushTracing();
    // Export is async (fire-and-forget from processor); poll for the request.
    for (let i = 0; i < 50; i++) {
      if (capturedRequests.length >= 1) break;
      await sleep(20);
    }
    assert.ok(
      capturedRequests.length >= 1,
      `expected at least 1 request to /api/traces, got ${capturedRequests.length}`
    );
    const last = capturedRequests[capturedRequests.length - 1];
    assert.ok(
      last.url.startsWith(serverUrl),
      `url should start with serverUrl: ${last.url}`
    );
    assert.ok(
      last.url.endsWith('/api/traces'),
      `url should end with /api/traces: ${last.url}`
    );
    assert.strictEqual(typeof (last.body as any)?.traceId, 'string');
    assert.ok(typeof (last.body as any)?.spans === 'object');
  });

  it('enableTelemetry does not throw when serverUrl is omitted', async () => {
    const provider = new FetchTelemetryProvider({});
    await assert.doesNotReject(provider.enableTelemetry({}));
    await assert.doesNotReject(provider.flushTracing());
  });

  it('sends custom headers with trace export requests when headers option is set', async () => {
    const serverUrl = 'http://telemetry.test';
    const provider = new FetchTelemetryProvider({
      serverUrl,
      realtime: true,
      headers: {
        Authorization: 'Bearer test-token',
        'X-Custom-Header': 'custom-value',
      },
    });

    await provider.enableTelemetry({});

    const tracer = trace.getTracer('test', '1.0');
    tracer.startActiveSpan('testSpan', {}, (span) => {
      span.end();
    });

    await provider.flushTracing();
    for (let i = 0; i < 50; i++) {
      if (capturedRequests.length >= 1) break;
      await sleep(20);
    }
    assert.ok(
      capturedRequests.length >= 1,
      `expected at least 1 request to /api/traces, got ${capturedRequests.length}`
    );
    const last = capturedRequests[capturedRequests.length - 1];
    assert.strictEqual(
      last.headers['authorization'],
      'Bearer test-token',
      'Authorization header should be sent'
    );
    assert.strictEqual(
      last.headers['x-custom-header'],
      'custom-value',
      'X-Custom-Header should be sent'
    );
  });
});
