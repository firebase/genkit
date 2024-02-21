import * as trpcExpress from '@trpc/server/adapters/express';
import * as clc from 'colorette';
import * as express from 'express';
import { ErrorRequestHandler } from 'express';
import { writeFileSync } from 'fs';
import * as path from 'path';
import { logger } from '../utils/logger';
import { TOOLS_SERVER_ROUTER } from './router';
import { Runner } from '../runner/runner';

// Static files are copied to the /dist/client directory. This is a litle
// brittle as __dirname refers directly to this particular file.
const UI_STATIC_FILES_DIR = path.resolve(
  __dirname,
  '../client/ui/browser/assets',
);
const UI_DEVELOPMENT_FILES_DIR = path.resolve(__dirname, '../../ui/src/assets');
const API_BASE_PATH = '/api';

/**
 * Writes a small JS file containing the CLI port number, optionally to the
 * development environment so that `ng serve` works as expected as well.
 */
function generateDiscoverabilityFile(headless: boolean, port: number): void {
  const basePath = headless ? UI_DEVELOPMENT_FILES_DIR : UI_STATIC_FILES_DIR;
  writeFileSync(
    path.join(basePath, 'discovery.js'),
    `(() => window._tools_server_port_ = ${port})();`,
  );
}

/**
 * Starts up the Genkit Tools server which includes static files for the UI and the Tools API.
 */
export function startServer(
  runner: Runner,
  headless: boolean,
  port: number,
): void {
  generateDiscoverabilityFile(headless, port);

  const app = express();

  if (!headless) {
    app.use(express.static(UI_STATIC_FILES_DIR));
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
      router: TOOLS_SERVER_ROUTER(runner),
    }),
  );

  const errorHandler: ErrorRequestHandler = (
    error,
    request,
    response,
    // Poor API doesn't allow leaving off `next` without changing the entire signature...
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    next,
  ) => {
    if (error instanceof Error) {
      logger.error(error.stack);
    }
    return response.status(500).send(error);
  };
  app.use(errorHandler);

  app.listen(port, () => {
    logger.info(
      `${clc.green(
        clc.bold('Genkit Tools API:'),
      )} http://localhost:${port}/api`,
    );
    if (!headless) {
      logger.info(
        `${clc.green(clc.bold('Genkit Tools UI:'))} http://localhost:${port}`,
      );
    }
  });
}
