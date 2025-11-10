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
  TraceData,
  TraceDataSchema,
  TraceQueryFilterSchema,
} from '@genkit-ai/tools-common';
import { logger } from '@genkit-ai/tools-common/utils';
import { randomBytes } from 'crypto';
import express from 'express';
import type * as http from 'http';
import type { TraceStore } from './types';
import { traceDataFromOtlp } from './utils/otlp';

export { LocalFileTraceStore } from './file-trace-store.js';
export { TraceQuerySchema, type TraceQuery, type TraceStore } from './types';

type Span = TraceData['spans'][string];

let server: http.Server;
let traceBuffer: Map<string, TraceData[]>;
let traceStore: TraceStore;

function generateId(bytes = 8): string {
  return randomBytes(bytes).toString('hex');
}

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
  traceStore = params.traceStore;
  const api = express();
  traceBuffer = new Map<string, TraceData[]>();

  api.use(express.json({ limit: params.maxRequestBodySize ?? '30mb' }));

  api.get('/api/__health', async (_, response) => {
    response.status(200).send('OK');
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
      const bufferedTraces = traceBuffer.get(traceData.traceId);
      if (bufferedTraces) {
        for (const bufferedTrace of bufferedTraces) {
          for (const span of Object.values(bufferedTrace.spans)) {
            traceData.spans[span.spanId] = span;
          }
        }
        traceBuffer.delete(traceData.traceId);
      }
      await params.traceStore.save(traceData.traceId, traceData);
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

  api.post(
    '/api/otlp/:parentTraceId/:parentSpanId',
    async (request, response) => {
      try {
        const { parentTraceId, parentSpanId } = request.params;

        if (!request.body.resourceSpans?.length) {
          // Acknowledge and ignore empty payloads.
          response.status(200).json({});
          return;
        }
        const traces = traceDataFromOtlp(request.body);
        if (!traceBuffer.has(parentTraceId)) {
          traceBuffer.set(parentTraceId, []);
        }
        const bufferedTraces = traceBuffer.get(parentTraceId)!;
        for (const trace of traces) {
          const traceData = TraceDataSchema.parse(trace);
          for (const span of Object.values(traceData.spans)) {
            span.traceId = parentTraceId;
            if (!span.parentSpanId) {
              span.parentSpanId = parentSpanId;
            }
          }
          bufferedTraces.push(traceData);
        }
        response.status(200).json({});
      } catch (err) {
        logger.error(`Error processing OTLP payload: ${err}`);
        response.status(500).json({
          code: 13, // INTERNAL
          message:
            'An internal error occurred while processing the OTLP payload.',
        });
      }
    }
  );

  api.post('/api/otlp', async (request, response) => {
    try {
      if (!request.body.resourceSpans?.length) {
        // Acknowledge and ignore empty payloads.
        response.status(200).json({});
        return;
      }
      const traces = traceDataFromOtlp(request.body);
      for (const trace of traces) {
        const traceData = TraceDataSchema.parse(trace);
        await params.traceStore.save(traceData.traceId, traceData);
      }
      response.status(200).json({});
    } catch (err) {
      logger.error(`Error processing OTLP payload: ${err}`);
      response.status(500).json({
        code: 13, // INTERNAL
        message:
          'An internal error occurred while processing the OTLP payload.',
      });
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
  if (traceBuffer && traceStore) {
    console.log('Force flushing traces......');
    for (const [traceId, bufferedTraces] of traceBuffer.entries()) {
      if (!bufferedTraces.length) continue;

      const topSpanId = generateId(8);
      let startTime = Infinity;
      let endTime = 0;
      const spans: { [spanId: string]: Span } = {};

      for (const trace of bufferedTraces) {
        for (const span of Object.values(trace.spans)) {
          // Not saving traceId for debugging
          spans[span.spanId] = span;
          if (span.startTime < startTime) {
            startTime = span.startTime;
          }
          if (span.endTime > endTime) {
            endTime = span.endTime;
          }
        }
      }

      for (const span of Object.values(spans)) {
        if (!span.parentSpanId) {
          span.parentSpanId = topSpanId;
        }
      }

      spans[topSpanId] = {
        spanId: topSpanId,
        traceId: traceId,
        startTime: startTime,
        endTime: endTime,
        attributes: {},
        displayName: 'synthetic-parent',
        instrumentationLibrary: { name: 'genkit-tracer', version: 'v1' },
        spanKind: 'INTERNAL',
        status: { code: 0 },
      };

      const traceData: TraceData = {
        traceId: traceId,
        spans: spans,
        displayName: `flushed-trace-${traceId}`,
      };

      await traceStore.save(traceId, traceData);
    }
    traceBuffer.clear();
  }

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
