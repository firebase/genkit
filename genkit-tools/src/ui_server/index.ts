import * as express from 'express';
import { logger } from '../utils/logger';
import path = require('path');
import { CliApi, CliEndpoints } from '../api';
import * as clc from 'colorette';

// Static files are copied to the /dist/client directory. This is a litle
// brittle as __dirname refers directly to this particular file.
const UI_STATIC_FILES_DIR = path.resolve(__dirname, '../client/ui/browser');

function apiPath(endpoint: string): string {
  return `/api/${endpoint}`;
}

export function startServer(headless: boolean, port: number): void {
  const app = express();
  if (!headless) {
    app.use(express.static(UI_STATIC_FILES_DIR));
  }

  // Endpoints for CLI control
  app.get(
    apiPath(CliEndpoints.EXAMPLE),
    (
      req: express.Request<
        unknown,
        unknown,
        unknown,
        CliApi['Example']['RequestQuery']
      >,
      res: express.Response<
        CliApi['Example']['Response'],
        Record<string, unknown>
      >,
    ) => {
      res.send({ echoResponse: req.query.echo.toUpperCase() });
    },
  );

  app.listen(port, () => {
    logger.info(`${clc.bold('GenKit UI')} running at http://localhost:${port}`);
  });
}
