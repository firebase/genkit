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
import getPort from 'get-port';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { defineFlow } from '../src/flow.js';
import { z } from '../src/index.js';
import { initNodeFeatures } from '../src/node.js';
import { ReflectionServer } from '../src/reflection.js';
import { Registry } from '../src/registry.js';

initNodeFeatures();

/** Returns the port from ReflectionServer.runtimeId (e.g. "12345-3100" -> 3100). */
function getPortFromRuntimeId(runtimeId: string): number | null {
  const parts = runtimeId.split('-');
  if (parts.length < 2) return null;
  const port = parseInt(parts[parts.length - 1], 10);
  return Number.isNaN(port) ? null : port;
}

/** Polls GET /api/__health until 200 or timeout. */
async function waitForServer(baseUrl: string, maxAttempts = 20): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${baseUrl}/api/__health`);
      if (res.ok) return;
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 50));
  }
  throw new Error(`Server at ${baseUrl} did not become ready`);
}

describe('ReflectionServer', () => {
  let registry: Registry;
  let reflectionServer: ReflectionServer;
  let baseUrl: string;

  beforeEach(async () => {
    delete process.env.GENKIT_ENV;
    registry = new Registry();
    defineFlow(
      registry,
      {
        name: 'echoFlow',
        inputSchema: z.string(),
        outputSchema: z.string(),
      },
      async (input) => input
    );
    const port = await getPort({ port: 32000 });
    reflectionServer = new ReflectionServer(registry, { port });
    await reflectionServer.start();
    const resolvedPort = getPortFromRuntimeId(reflectionServer.runtimeId);
    assert.ok(resolvedPort != null, 'expected runtimeId to include port');
    baseUrl = `http://localhost:${resolvedPort}`;
    await waitForServer(baseUrl);
  });

  afterEach(async () => {
    if (reflectionServer) await reflectionServer.stop();
    ReflectionServer.stopAll();
  });

  describe('GET /api/__health', () => {
    it('returns 200 without query id', async () => {
      const res = await fetch(`${baseUrl}/api/__health`);
      assert.strictEqual(res.status, 200);
      assert.strictEqual(await res.text(), 'OK');
    });

    it('returns 200 when id matches runtimeId', async () => {
      const runtimeId = reflectionServer.runtimeId;
      const res = await fetch(
        `${baseUrl}/api/__health?id=${encodeURIComponent(runtimeId)}`
      );
      assert.strictEqual(res.status, 200);
      assert.strictEqual(await res.text(), 'OK');
    });

    it('returns 503 when id does not match runtimeId', async () => {
      const res = await fetch(
        `${baseUrl}/api/__health?id=${encodeURIComponent('wrong-id')}`
      );
      assert.strictEqual(res.status, 503);
      assert.strictEqual(await res.text(), 'Invalid runtime ID');
    });
  });

  describe('GET /api/actions', () => {
    it('returns list of actions with expected shape', async () => {
      const res = await fetch(`${baseUrl}/api/actions`);
      assert.strictEqual(res.status, 200);
      const body = (await res.json()) as Record<string, unknown>;
      assert.ok(
        body['/flow/echoFlow'],
        `expected /flow/echoFlow in actions, got keys: ${Object.keys(body).join(', ')}`
      );
      const action = body['/flow/echoFlow'] as Record<string, unknown>;
      assert.strictEqual(action.key, '/flow/echoFlow');
      assert.strictEqual(action.name, 'echoFlow');
      assert.ok('inputSchema' in action);
      assert.ok('outputSchema' in action);
    });
  });

  describe('POST /api/runAction', () => {
    it('runs action and returns result and telemetry', async () => {
      const res = await fetch(`${baseUrl}/api/runAction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key: '/flow/echoFlow',
          input: 'hello',
        }),
      });
      assert.strictEqual(res.status, 200);
      assert.strictEqual(
        res.headers.get('Content-Type'),
        'application/json',
        'expected JSON response'
      );
      const data = (await res.json()) as {
        result?: string;
        error?: unknown;
        telemetry?: { traceId?: string };
      };
      assert.ok(!data.error, `unexpected error: ${JSON.stringify(data.error)}`);
      assert.strictEqual(data.result, 'hello');
      assert.ok(
        data.telemetry?.traceId,
        `expected telemetry.traceId, got ${JSON.stringify(data.telemetry)}`
      );
    });
  });

  describe('POST /api/cancelAction', () => {
    it('returns 404 when traceId is not found', async () => {
      const res = await fetch(`${baseUrl}/api/cancelAction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ traceId: 'nonexistent-trace-id' }),
      });
      assert.strictEqual(res.status, 404);
      const body = (await res.json()) as { message?: string };
      assert.ok(
        body.message?.includes('not found') ||
          body.message?.includes('already completed')
      );
    });

    it('returns 400 when traceId is missing', async () => {
      const res = await fetch(`${baseUrl}/api/cancelAction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      assert.strictEqual(res.status, 400);
    });
  });

  describe('GET /api/envs', () => {
    it('returns configured envs', async () => {
      const res = await fetch(`${baseUrl}/api/envs`);
      assert.strictEqual(res.status, 200);
      const envs = (await res.json()) as string[];
      assert.ok(Array.isArray(envs));
      assert.ok(
        envs.includes('dev'),
        `expected ['dev'] to include 'dev', got ${JSON.stringify(envs)}`
      );
    });
  });
});
