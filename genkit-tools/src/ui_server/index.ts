import * as express from 'express';
import { logger } from '../utils/logger';
import path = require('path');
import { EchoExample, Endpoints } from '../api/cli';
import * as clc from 'colorette';
import { writeFileSync } from 'fs';

// Static files are copied to the /dist/client directory. This is a litle
// brittle as __dirname refers directly to this particular file.
const UI_STATIC_FILES_DIR = path.resolve(__dirname, '../client/ui/browser');
const UI_DEVELOPMENT_FILES_DIR = path.resolve(__dirname, '../../ui/src');

/**
 * Writes a small JS file containing the CLI port number, optionally to the
 * development environment so that `ng serve` works as expected as well.
 */
function generateDiscoverabilityFile(headless: boolean, port: number): void {
  const basePath = headless ? UI_DEVELOPMENT_FILES_DIR : UI_STATIC_FILES_DIR;
  writeFileSync(path.join(basePath, 'discovery.js'), `(() => window._cli_port_ = ${port})();`);
}

function apiPath(endpoint: string): string {
  return `/api/${endpoint}`;
}

export function startServer(headless: boolean, port: number): void {
  generateDiscoverabilityFile(headless, port);

  const app = express();
  if (!headless) {
    app.use(express.static(UI_STATIC_FILES_DIR));
  }

  // Endpoints for CLI control
  app.get(
    apiPath(Endpoints.ECHO_EXAMPLE),
    (
      req: express.Request<
        unknown,
        unknown,
        unknown,
        EchoExample.RequestQueryParams
      >,
      res: express.Response<
        EchoExample.ResponseBody,
        Record<string, unknown>
      >,
    ) => {
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.send({ echoedValue: req.query.value.toUpperCase() });
    },
  );

  app.listen(port, () => {
    logger.info(`${clc.bold('GenKit UI')} running at http://localhost:${port}`);
  });
}
