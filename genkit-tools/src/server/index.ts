import * as trpcExpress from '@trpc/server/adapters/express';
import * as clc from 'colorette';
import * as express from 'express';
import { ErrorRequestHandler } from 'express';
import { writeFileSync } from 'fs';
import * as path from 'path';
import { logger } from '../utils/logger';
import { TOOLS_SERVER_ROUTER } from './router';
import { Runner } from '../runner/runner';
import * as open from 'open';
import * as bodyParser from 'body-parser';

// Static files are copied to the /dist/client directory. This is a litle
// brittle as __dirname refers directly to this particular file.
const UI_STATIC_FILES_DIR = path.resolve(
  __dirname,
  '../client/dist/ui/browser'
);
const UI_DEVELOPMENT_FILES_DIR = path.resolve(__dirname, '../../ui/src/assets');
const API_BASE_PATH = '/api';

/**
 * Writes a small JS file containing the CLI port number, optionally to the
 * development environment so that `ng serve` works as expected as well.
 */
function generateDiscoverabilityFile(headless: boolean, port: number): void {
  const basePath = headless
    ? UI_DEVELOPMENT_FILES_DIR
    : path.resolve(UI_STATIC_FILES_DIR, 'assets');
  writeFileSync(
    path.join(basePath, 'discovery.js'),
    `(() => window._tools_server_url_ = ${headless ? `"http://localhost:${port}"` : '""'})();`
  );
}

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

  generateDiscoverabilityFile(headless, port);

  const app = express();

  if (!headless) {
    app.use(express.static(UI_STATIC_FILES_DIR));
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
    res.status(200).sendFile('/', { root: UI_STATIC_FILES_DIR });
  });

  app.listen(port, () => {
    logger.info(
      `${clc.green(clc.bold('Genkit Tools API:'))} http://localhost:${port}/api`
    );
    if (!headless) {
      const uiUrl = 'http://localhost:' + port;
      logger.info(`${clc.green(clc.bold('Genkit Tools UI:'))} ${uiUrl}`);
      runner
        .waitUntilHealthy()
        .then(() => open(uiUrl))
        .catch((e) => {
          logger.error(e.message);
          if (serverEnder) serverEnder();
        });
    }
  });

  return enderPromise;
}
