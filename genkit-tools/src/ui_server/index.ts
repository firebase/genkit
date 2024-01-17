import * as express from 'express';
import { logger } from '../utils/logger';
import path = require('path');
import * as clc from 'colorette';
import { writeFileSync } from 'fs';
import * as trpcExpress from '@trpc/server/adapters/express';
import { uiEndpointsRouter } from './endpoints';

// Static files are copied to the /dist/client directory. This is a litle
// brittle as __dirname refers directly to this particular file.
const UI_STATIC_FILES_DIR = path.resolve(__dirname, '../client/ui/browser');
const UI_DEVELOPMENT_FILES_DIR = path.resolve(__dirname, '../../ui/src');
const API_BASE_PATH = '/api';

/**
 * Writes a small JS file containing the CLI port number, optionally to the
 * development environment so that `ng serve` works as expected as well.
 */
function generateDiscoverabilityFile(headless: boolean, port: number): void {
  const basePath = headless ? UI_DEVELOPMENT_FILES_DIR : UI_STATIC_FILES_DIR;
  writeFileSync(
    path.join(basePath, 'discovery.js'),
    `(() => window._cli_port_ = ${port})();`,
  );
}

/**
 * Starts up the CLI server, including static files for the UI as well as the
 * CLI API.
 */
export function startServer(headless: boolean, port: number): void {
  generateDiscoverabilityFile(headless, port);

  const app = express();

  let startupMessage = `${clc.bold(
    'GenKit CLI endpoints',
  )} listening at http://localhost:${port}/api`;
  if (!headless) {
    app.use(express.static(UI_STATIC_FILES_DIR));
    startupMessage = `${clc.bold(
      'GenKit UI',
    )} running at http://localhost:${port}`;
  }

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
      router: uiEndpointsRouter,
      createContext: () => ({}),
    }),
  );

  app.listen(port, () => {
    logger.info(startupMessage);
  });
}
