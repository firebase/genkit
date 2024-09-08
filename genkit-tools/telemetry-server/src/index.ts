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

import express from 'express';
import * as http from 'http';
import { TraceData, TraceStore } from './types';

export { FirestoreTraceStore } from './firestoreTraceStore.js';
export { LocalFileTraceStore } from './localFileTraceStore.js';
export {
  InstrumentationLibrarySchema,
  LinkSchema,
  SpanContextSchema,
  SpanData,
  SpanDataSchema,
  SpanMetadata,
  SpanMetadataSchema,
  SpanStatusSchema,
  TimeEventSchema,
  TraceData,
  TraceDataSchema,
  TraceStore,
} from './types';

let server: http.Server;

/**
 * Starts the telemetry server with the provided params
 */
export function startTelemetryServer(params: {
  port: number;
  traceStore: TraceStore;
}) {
  const api = express();

  api.use(express.json({ limit: '30mb' }));

  api.get('/api/__health', async (_, response) => {
    response.status(200).send('OK');
  });

  api.get('/api/traces/:traceId', async (request, response) => {
    const { traceId } = request.params;
    console.debug(`Fetching trace \`${traceId}\`.`);
    response.json(await params.traceStore.load(traceId));
  });

  api.post('/api/traces', async (request, response) => {
    const traceData = request.body as TraceData;

    console.debug(`Writing trace ${traceData.traceId}.`);

    await params.traceStore.save(traceData.traceId, traceData);
    response.status(200).send('OK');
  });

  api.get('/api/traces', async (request, response) => {
    const { limit, continuationToken } = request.query;
    console.debug(`Fetching traces.`);
    response.json(
      await params.traceStore.list({
        limit: limit ? parseInt(limit.toString()) : undefined,
        continuationToken: continuationToken
          ? continuationToken.toString()
          : undefined,
      })
    );
  });

  api.use((err: any, req: any, res: any, next: any) => {
    console.error(err.stack);
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
    console.log(`Telemetry API running on http://localhost:${params.port}`);
  });

  server.on('error', (error) => {
    console.error(error);
  });

  process.on('SIGTERM', async () => await stopTelemetryApi());
}

/**
 * Stops Telemetry API and any running dependencies.
 */
async function stopTelemetryApi() {
  await Promise.all([
    new Promise<void>((resolve) => {
      if (server) {
        server.close(() => {
          console.info('Reflection API has succesfully shut down.');
          resolve();
        });
      } else {
        resolve();
      }
    }),
  ]);
}
