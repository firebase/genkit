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

import * as trpcExpress from '@trpc/server/adapters/express';
import * as bodyParser from 'body-parser';
import * as clc from 'colorette';
import cors from 'cors';
import express, { type ErrorRequestHandler } from 'express';
import type { Server } from 'http';
import os from 'os';
import path from 'path';
import type { GenkitToolsError } from '../manager';
import type { RuntimeManager } from '../manager/manager';
import { writeToolsInfoFile } from '../utils';
import { logger } from '../utils/logger';
import { toolsPackage } from '../utils/package';
import { downloadAndExtractUiAssets } from '../utils/ui-assets';
import { TOOLS_SERVER_ROUTER } from './router';

const MAX_PAYLOAD_SIZE = 30000000;
const UI_ASSETS_GCS_BUCKET = `https://storage.googleapis.com/genkit-assets`;
const UI_ASSETS_ZIP_FILE_NAME = `${toolsPackage.version}.zip`;
const UI_ASSETS_ZIP_GCS_PATH = `${UI_ASSETS_GCS_BUCKET}/${UI_ASSETS_ZIP_FILE_NAME}`;
const UI_ASSETS_ROOT = path.resolve(
  os.homedir(),
  '.genkit',
  'assets',
  toolsPackage.version
);
const UI_ASSETS_SERVE_PATH = path.resolve(UI_ASSETS_ROOT, 'ui', 'browser');
const API_BASE_PATH = '/api';

/**
 * Starts up the Genkit Tools server which includes static files for the UI and the Tools API.
 */
export function startServer(manager: RuntimeManager, port: number) {
  let server: Server;
  const app = express();

  // Allow all origins
  app.use(
    cors({
      origin: '*',
      allowedHeaders: ['Content-Type'],
    })
  );

  // Download UI assets from public GCS bucket and serve locally
  downloadAndExtractUiAssets({
    fileUrl: UI_ASSETS_ZIP_GCS_PATH,
    extractPath: UI_ASSETS_ROOT,
    zipFileName: UI_ASSETS_ZIP_FILE_NAME,
  });
  app.use(express.static(UI_ASSETS_SERVE_PATH));

  // tRPC doesn't support simple streaming mutations
  // (https://github.com/trpc/trpc/issues/4477), and we don't want a separate
  // WebSocket server for subscriptions (https://trpc.io/docs/subscriptions).
  //
  // TODO: migrate to streamingMutation when it becomes available in tRPC.
  app.post(
    '/api/runAction',
    bodyParser.json({ limit: MAX_PAYLOAD_SIZE }),
    async (req, res) => {
      res.setHeader('Content-Type', 'text/plain');

      try {
        const onTraceIdCallback = !manager.disableRealtimeTelemetry
          ? (traceId: string) => {
              // Send the initial trace ID, which will also flush headers and
              // serve as a "keep alive" while we wait for the action to
              // complete.
              res.write(JSON.stringify({ telemetry: { traceId } }) + '\n');
            }
          : undefined;

        const result = await manager.runAction(
          req.body,
          undefined, // no streaming callback
          onTraceIdCallback
        );

        res.end(JSON.stringify(result));
      } catch (err) {
        const error = err as GenkitToolsError;

        // If headers haven't been sent (e.g., telemetry is disabled or the
        // error occurred before a trace ID was available), we can still
        // send a 500 status code.
        if (!res.headersSent) {
          res.status(500);
        }
        res.end(JSON.stringify({ error: error.data }));
      }
    }
  );

  app.post(
    '/api/streamAction',
    bodyParser.json({ limit: MAX_PAYLOAD_SIZE }),
    async (req, res) => {
      res.setHeader('Content-Type', 'text/plain');

      try {
        const onTraceIdCallback = !manager.disableRealtimeTelemetry
          ? (traceId: string) => {
              // Send the initial trace ID, which will also flush headers and
              // serve as a "keep alive" while we wait for the action to stream.
              res.write(JSON.stringify({ telemetry: { traceId } }) + '\n');
            }
          : undefined;

        const result = await manager.runAction(
          req.body,
          (chunk) => {
            res.write(JSON.stringify(chunk) + '\n');
          },
          onTraceIdCallback
        );
        res.write(JSON.stringify(result));
      } catch (err) {
        // If headers haven't been sent (e.g., telemetry is disabled or the
        // error occurred before a trace ID was available), we can still
        // send a 500 status code.
        if (!res.headersSent) {
          res.status(500);
        }
        res.write(JSON.stringify({ error: (err as GenkitToolsError).data }));
      }
      res.end();
    }
  );

  app.post(
    '/api/streamTrace',
    bodyParser.json({ limit: MAX_PAYLOAD_SIZE }),
    async (req, res) => {
      const { traceId } = req.body;

      if (!traceId) {
        res.status(400).json({ error: 'traceId is required' });
        return;
      }

      // text/plain because we are sending various chunks that do not form
      // a single json document.
      res.setHeader('Content-Type', 'text/plain');

      try {
        // Send the initial trace ID, which will also flush headers and serve
        // as a "keep alive" while we wait for the trace to stream.
        res.write(JSON.stringify({ telemetry: { traceId } }) + '\n');

        await manager.streamTrace({ traceId }, (chunk) => {
          res.write(JSON.stringify(chunk) + '\n');
        });
        res.end();
      } catch (err) {
        const error = err as GenkitToolsError;

        // If headers haven't been sent (e.g., the error occurred before the
        // initial trace ID chunk was written), we can still send a 500
        // status code.
        if (!res.headersSent) {
          res.status(500);
        }
        res.write(
          JSON.stringify({ error: error.data || { message: error.message } })
        );
        res.end();
      }
    }
  );

  app.get('/api/__health', (_, res) => {
    res.status(200).send('');
  });

  app.post('/api/__quitquitquit', (_, res) => {
    logger.debug('Shutting down tools API');
    res.status(200).send('Server is shutting down');
    server.close(() => {
      process.exit(0);
    });
  });

  // Endpoints for CLI control
  app.use(
    API_BASE_PATH,
    trpcExpress.createExpressMiddleware({
      router: TOOLS_SERVER_ROUTER(manager),
      maxBodySize: MAX_PAYLOAD_SIZE,
    })
  );

  app.all('*', (_, res) => {
    res.status(200).sendFile('/', { root: UI_ASSETS_SERVE_PATH });
  });

  const errorHandler: ErrorRequestHandler = (
    error,
    request,
    response,
    // Poor API doesn't allow leaving off `next` without changing the entire signature...
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    next
  ) => {
    if (error instanceof Error) {
      logger.error(error.stack);
    }
    return response.status(500).send(error);
  };
  app.use(errorHandler);

  server = app.listen(port, async () => {
    const uiUrl = 'http://localhost:' + port;
    const projectRoot = manager.projectRoot;
    logger.info(`${clc.green(clc.bold('Project root:'))} ${projectRoot}`);
    logger.info(`${clc.green(clc.bold('Genkit Developer UI:'))} ${uiUrl}`);
    await writeToolsInfoFile(uiUrl, projectRoot);
  });

  return new Promise<void>((resolve) => {
    server.once('close', resolve);
  });
}
