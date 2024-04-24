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
import { renameSync } from 'fs';
import open from 'open';
import os from 'os';
import path from 'path';
import { Runner } from '../runner/runner';
import { logger } from '../utils/logger';
import { toolsPackage } from '../utils/package';
import { downloadAndExtractUiAssets } from '../utils/ui-assets';
import { TOOLS_SERVER_ROUTER } from './router';

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
export function startServer(
  runner: Runner,
  headless: boolean,
  port: number
): Promise<void> {
  let serverEnder: (() => void) | undefined = undefined;
  const enderPromise = new Promise<void>((resolver) => {
    serverEnder = resolver;
  });

  const app = express();

  if (!headless) {
    // Download UI assets from public GCS bucket and serve locally
    downloadAndExtractUiAssets({
      fileUrl: UI_ASSETS_ZIP_GCS_PATH,
      extractPath: UI_ASSETS_ROOT,
      zipFileName: UI_ASSETS_ZIP_FILE_NAME,
    });

    // Move licenses file into `browser` folder for serving
    renameSync(
      path.join(UI_ASSETS_ROOT, 'ui', '3rdpartylicenses.txt'),
      path.join(UI_ASSETS_SERVE_PATH, 'licenses.txt')
    );

    app.use(express.static(UI_ASSETS_SERVE_PATH));
  }

  // tRPC doesn't support simple streaming mutations (https://github.com/trpc/trpc/issues/4477).
  // Don't want a separate WebSocket server for subscriptions - https://trpc.io/docs/subscriptions.
  // TODO: migrate to streamingMutation when it becomes available in tRPC.
  app.options('/api/streamAction', async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.status(200).send('');
  });

  app.post('/api/streamAction', bodyParser.json(), async (req, res) => {
    const { key, input } = req.body;
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Content-Type': 'text/plain',
      'Transfer-Encoding': 'chunked',
    });

    const result = await runner.runAction({ key, input }, (chunk) => {
      res.write(JSON.stringify(chunk) + '\n');
    });
    res.write(JSON.stringify(result));
    res.end();
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
      router: TOOLS_SERVER_ROUTER(runner),
    })
  );

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

  // serve angular paths
  app.all('*', (req, res) => {
    res.status(200).sendFile('/', { root: UI_ASSETS_SERVE_PATH });
  });

  app.listen(port, () => {
    logger.info(
      `${clc.green(clc.bold('Genkit Tools API:'))} http://localhost:${port}/api`
    );
    if (!headless) {
      const uiUrl = 'http://localhost:' + port;
      runner
        .waitUntilHealthy()
        .then(() => {
          logger.info(`${clc.green(clc.bold('Genkit Tools UI:'))} ${uiUrl}`);
          open(uiUrl);
        })
        .catch((e) => {
          logger.error(e.message);
          if (serverEnder) serverEnder();
        });
    }
  });

  return enderPromise;
}
