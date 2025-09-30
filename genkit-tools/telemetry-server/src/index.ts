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

import {
  TraceDataSchema,
  TraceQueryFilterSchema,
} from '@genkit-ai/tools-common';
import { logger } from '@genkit-ai/tools-common/utils';
import express from 'express';
import type * as http from 'http';
import type { TraceStore } from './types';

export { LocalFileTraceStore } from './file-trace-store.js';
export { TraceQuerySchema, type TraceQuery, type TraceStore } from './types';

let server: http.Server;

/**
 * Starts the telemetry server with the provided params
 */
export async function startTelemetryServer(params: {
  port: number;
  traceStore: TraceStore;
  /**
   * Controls the maximum request body size. If this is a number,
   * then the value specifies the number of bytes; if it is a string,
   * the value is passed to the bytes library for parsing.
   *
   * Defaults to '5mb'.
   */
  maxRequestBodySize?: string | number;
}) {
  await params.traceStore.init();
  const api = express();

  // In-memory registry of streaming listeners keyed by traceId
  const listeners = new Map<string, Set<http.ServerResponse>>();

  function getListeners(traceId: string): Set<http.ServerResponse> {
    let set = listeners.get(traceId);
    if (!set) {
      set = new Set<http.ServerResponse>();
      listeners.set(traceId, set);
    }
    return set;
  }

  function findRootSpan(snapshot: any): any | undefined {
    if (!snapshot || !snapshot.spans) return undefined;
    const spans = Object.values(snapshot.spans) as any[];
    return spans.find((s) => !s.parentSpanId);
  }

  function broadcastTrace(traceId: string, snapshot: any) {
    const subs = listeners.get(traceId);
    if (!subs || subs.size === 0) return;
    const line = JSON.stringify(snapshot) + '\n';
    for (const res of subs) {
      try {
        res.write(line);
      } catch (_) {
        // Best-effort write; ignore failures on individual clients
      }
    }
    const root = findRootSpan(snapshot);
    if (root && typeof root.endTime === 'number') {
      // Root span ended: close all listeners for this trace
      for (const res of subs) {
        try {
          res.end();
        } catch (_) {
          // ignore
        }
      }
      listeners.delete(traceId);
    }
  }

  function broadcastDelta(traceId: string, spansDelta: Record<string, any>) {
    const subs = listeners.get(traceId);
    if (!subs || subs.size === 0) return;
    const payload = { type: 'upsert', traceId, spans: spansDelta };
    const line = JSON.stringify(payload) + '\n';
    for (const res of subs) {
      try {
        res.write(line);
      } catch (_) {}
    }
  }

  function broadcastDone(traceId: string) {
    const subs = listeners.get(traceId);
    if (!subs || subs.size === 0) return;
    const line = JSON.stringify({ type: 'done', traceId }) + '\n';
    for (const res of subs) {
      try {
        res.write(line);
        res.end();
      } catch (_) {}
    }
    listeners.delete(traceId);
  }

  api.use(express.json({ limit: params.maxRequestBodySize ?? '30mb' }));

  api.get('/api/__health', async (_, response) => {
    response.status(200).send('OK');
  });

  // Streaming endpoint for live trace updates (NDJSON over chunked HTTP)
  api.get('/api/traces/:traceId/stream', async (request, response, next) => {
    try {
      const { traceId } = request.params;
      response.writeHead(200, {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Transfer-Encoding': 'chunked',
        'Access-Control-Allow-Origin': '*',
      });

      // Send initial snapshot if present
      const snapshot = await params.traceStore.load(traceId);
      if (snapshot) {
        response.write(JSON.stringify(snapshot) + '\n');
        const root = findRootSpan(snapshot);
        if (root && typeof root.endTime === 'number') {
          response.end();
          return;
        }
      }

      // Register listener
      getListeners(traceId).add(response);

      // Cleanup on client disconnect
      (request as any).on('close', () => {
        const set = listeners.get(traceId);
        set?.delete(response);
        if (set && set.size === 0) listeners.delete(traceId);
      });
    } catch (e) {
      next(e);
    }
  });

  api.get('/api/traces/:traceId', async (request, response, next) => {
    try {
      const { traceId } = request.params;
      response.json(await params.traceStore.load(traceId));
    } catch (e) {
      next(e);
    }
  });

  api.post('/api/traces', async (request, response, next) => {
    try {
      const traceData = TraceDataSchema.parse(request.body);
      await params.traceStore.save(traceData.traceId, traceData);
      // After saving, broadcast delta (upsert spans) to any listeners
      try {
        if (traceData.spans && Object.keys(traceData.spans).length > 0) {
          broadcastDelta(traceData.traceId, traceData.spans);
        }
        // If root is now ended, emit done and close listeners
        const snapshot = await params.traceStore.load(traceData.traceId);
        const root = findRootSpan(snapshot);
        if (root && typeof root.endTime === 'number') {
          broadcastDone(traceData.traceId);
        }
      } catch (_) {
        // Best-effort broadcast; do not fail the write path
      }
      response.status(200).send('OK');
    } catch (e) {
      next(e);
    }
  });

  api.get('/api/traces', async (request, response, next) => {
    try {
      const { limit, continuationToken, filter } = request.query;
      response.json(
        await params.traceStore.list({
          limit: limit ? Number.parseInt(limit.toString()) : 10,
          continuationToken: continuationToken
            ? continuationToken.toString()
            : undefined,
          filter: filter
            ? TraceQueryFilterSchema.parse(JSON.parse(filter as string))
            : undefined,
        })
      );
    } catch (e) {
      next(e);
    }
  });

  api.use((err: any, req: any, res: any, next: any) => {
    logger.error(err.stack);
    const error = err as Error;
    const { message, stack } = error;
    const errorResponse = {
      code: 13, // StatusCodes.INTERNAL,
      message,
      details: {
        stack,
        traceId: err.traceId,
      },
    };
    res.status(500).json(errorResponse);
  });

  server = api.listen(params.port, () => {
    logger.info(`Telemetry API running on http://localhost:${params.port}`);
  });

  server.on('error', (error) => {
    logger.error(error);
  });

  process.on('SIGTERM', async () => await stopTelemetryApi());
}

/**
 * Stops Telemetry API and any running dependencies.
 */
export async function stopTelemetryApi() {
  await Promise.all([
    new Promise<void>((resolve) => {
      if (server) {
        server.close(() => {
          logger.debug('Telemetry API has succesfully shut down.');
          resolve();
        });
      } else {
        resolve();
      }
    }),
  ]);
}
