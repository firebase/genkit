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
  type TraceData,
} from '@genkit-ai/tools-common';
import { logger } from '@genkit-ai/tools-common/utils';
import express from 'express';
import type * as http from 'http';
import type { Response } from 'express';
import type { TraceStore } from './types';
import { traceDataFromOtlp } from './utils/otlp';

export { LocalFileTraceStore } from './file-trace-store.js';
export { TraceQuerySchema, type TraceQuery, type TraceStore } from './types';

let server: http.Server;

/**
 * Broadcast manager for SSE connections.
 * Tracks active connections per traceId and broadcasts updates.
 */
class BroadcastManager {
  private connections: Map<string, Set<Response>> = new Map();

  /**
   * Register a new SSE connection for a traceId.
   */
  subscribe(traceId: string, response: Response): void {
    if (!this.connections.has(traceId)) {
      this.connections.set(traceId, new Set());
    }
    this.connections.get(traceId)!.add(response);

    // Clean up when connection closes
    response.on('close', () => {
      this.unsubscribe(traceId, response);
    });
  }

  /**
   * Remove a connection from subscriptions.
   */
  unsubscribe(traceId: string, response: Response): void {
    const connections = this.connections.get(traceId);
    if (connections) {
      connections.delete(response);
      if (connections.size === 0) {
        this.connections.delete(traceId);
      }
    }
  }

  /**
   * Broadcast span updates to all subscribers of a traceId.
   */
  broadcast(traceId: string, message: {
    type: 'upsert' | 'done';
    traceId: string;
    spans?: TraceData['spans'];
    traceData?: TraceData;
  }): void {
    const connections = this.connections.get(traceId);
    if (!connections || connections.size === 0) {
      return;
    }

    const data = JSON.stringify(message);
    const messageToSend = `data: ${data}\n\n`;

    // Send to all connections, removing dead ones
    const deadConnections: Response[] = [];
    for (const connection of connections) {
      try {
        connection.write(messageToSend);
      } catch (error) {
        // Connection is dead, mark for removal
        deadConnections.push(connection);
      }
    }

    // Clean up dead connections
    for (const deadConnection of deadConnections) {
      this.unsubscribe(traceId, deadConnection);
    }
  }

  /**
   * Close all connections for a traceId.
   */
  close(traceId: string): void {
    const connections = this.connections.get(traceId);
    if (connections) {
      for (const connection of connections) {
        try {
          connection.end();
        } catch (error) {
          // Ignore errors when closing
        }
      }
      this.connections.delete(traceId);
    }
  }
}

const broadcastManager = new BroadcastManager();

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

  // SSE endpoint for live trace streaming
  api.get('/api/traces/:traceId/stream', async (request, response, next) => {
    try {
      const { traceId } = request.params;
      
      // Set SSE headers
      response.setHeader('Content-Type', 'text/event-stream');
      response.setHeader('Cache-Control', 'no-cache');
      response.setHeader('Connection', 'keep-alive');
      response.setHeader('Access-Control-Allow-Origin', '*');
      response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      
      // Send initial snapshot of current trace data
      const currentTrace = await params.traceStore.load(traceId);
      if (currentTrace) {
        const snapshot = JSON.stringify(currentTrace);
        response.write(`data: ${snapshot}\n\n`);
      }
      
      // Register this connection for broadcasts
      broadcastManager.subscribe(traceId, response);
      
      // Keep connection alive with periodic heartbeat
      const heartbeatInterval = setInterval(() => {
        try {
          response.write(': heartbeat\n\n');
        } catch (error) {
          clearInterval(heartbeatInterval);
        }
      }, 30000); // 30 second heartbeat
      
      // Clean up on disconnect
      response.on('close', () => {
        clearInterval(heartbeatInterval);
        broadcastManager.unsubscribe(traceId, response);
      });
    } catch (e) {
      next(e);
    }
  });

  api.post('/api/traces', async (request, response, next) => {
    try {
      const traceData = TraceDataSchema.parse(request.body);
      await params.traceStore.save(traceData.traceId, traceData);
      
      // Broadcast span updates to all subscribed clients
      broadcastManager.broadcast(traceData.traceId, {
        type: 'upsert',
        traceId: traceData.traceId,
        spans: traceData.spans,
      });
      
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
        for (const traceData of traces) {
          traceData.traceId = parentTraceId;
          for (const span of Object.values(traceData.spans)) {
            span.attributes['genkit:otlp-traceId'] = span.traceId;
            span.traceId = parentTraceId;
            if (!span.parentSpanId) {
              span.parentSpanId = parentSpanId;
            }
          }
          await params.traceStore.save(parentTraceId, traceData);
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
      for (const traceData of traces) {
        await params.traceStore.save(traceData.traceId, traceData);
        // Broadcast span updates to all subscribed clients
        broadcastManager.broadcast(traceData.traceId, {
          type: 'upsert',
          traceId: traceData.traceId,
          spans: traceData.spans,
        });
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
