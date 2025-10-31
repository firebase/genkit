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

  // Download UI assets from public GCS bucket and serve locally
  downloadAndExtractUiAssets({
    fileUrl: UI_ASSETS_ZIP_GCS_PATH,
    extractPath: UI_ASSETS_ROOT,
    zipFileName: UI_ASSETS_ZIP_FILE_NAME,
  });
  app.use(express.static(UI_ASSETS_SERVE_PATH));

  // tRPC doesn't support simple streaming mutations (https://github.com/trpc/trpc/issues/4477).
  // Don't want a separate WebSocket server for subscriptions - https://trpc.io/docs/subscriptions.
  // TODO: migrate to streamingMutation when it becomes available in tRPC.
  app.options('/api/streamAction', async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.status(200).send('');
  });

  // Plain HTTP runAction endpoint (non-streaming)
  app.options('/api/runAction', async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.status(200).send('');
  });

  app.post(
    '/api/runAction',
    bodyParser.json({ limit: MAX_PAYLOAD_SIZE }),
    async (req, res) => {
      const { key, input, context, runtimeId } = req.body;
      
      try {
        const resultPromise = manager.runAction(
          { key, input, context, runtimeId },
          undefined, // no streaming callback
          (traceId) => {
            // Send headers immediately when trace ID is available
            // This is the first place headers are sent, so no check needed
            res.setHeader('X-Genkit-Trace-Id', traceId);
            res.setHeader('Content-Type', 'application/json');
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
            res.statusCode = 200;
            res.flushHeaders();
          }
        );
        
        const result = await resultPromise;
        res.end(JSON.stringify(result));
      } catch (err) {
        const error = err as GenkitToolsError;
        
        // If headers not sent, we can send error status
        if (!res.headersSent) {
          res.writeHead(500, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          });
        }
        res.end(JSON.stringify({ error: error.data }));
      }
    }
  );

  app.post(
    '/api/streamAction',
    bodyParser.json({ limit: MAX_PAYLOAD_SIZE }),
    async (req, res) => {
      const { key, input, context } = req.body;
      
      // Set streaming headers immediately
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      res.setHeader('Content-Type', 'text/plain');
      res.setHeader('Transfer-Encoding', 'chunked');
      res.statusCode = 200;
      res.flushHeaders();

      try {
        const result = await manager.runAction(
          { key, input, context },
          (chunk) => {
            res.write(JSON.stringify(chunk) + '\n');
          },
          (traceId) => {
            // Add trace ID to headers when available (headers already sent, but we can add more)
            res.setHeader('X-Genkit-Trace-Id', traceId);
          }
        );
        res.write(JSON.stringify(result));
      } catch (err) {
        res.write(JSON.stringify({ error: (err as GenkitToolsError).data }));
      }
      res.end();
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
    (req, res, next) => {
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      if (req.method === 'OPTIONS') res.send('');
      else next();
    },
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
