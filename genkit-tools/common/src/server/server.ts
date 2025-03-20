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
import express, { ErrorRequestHandler } from 'express';
import { Server } from 'http';
import os from 'os';
import path from 'path';
import { GenkitToolsError } from '../manager';
import { RuntimeManager } from '../manager/manager';
import { findProjectRoot, writeToolsInfoFile } from '../utils';
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

  app.post(
    '/api/streamAction',
    bodyParser.json({ limit: MAX_PAYLOAD_SIZE }),
    async (req, res) => {
      const { key, input, context } = req.body;
      res.writeHead(200, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'text/plain',
        'Transfer-Encoding': 'chunked',
      });

      try {
        const result = await manager.runAction(
          { key, input, context },
          (chunk) => {
            res.write(JSON.stringify(chunk) + '\n');
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
    logger.info('Shutting down tools API');
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
    const projectRoot = await findProjectRoot();
    logger.info(`${clc.green(clc.bold('Project root:'))} ${projectRoot}`);
    logger.info(`${clc.green(clc.bold('Genkit Developer UI:'))} ${uiUrl}`);
    await writeToolsInfoFile(uiUrl, projectRoot);
  });

  return new Promise<void>((resolve) => {
    server.once('close', resolve);
  });
}
