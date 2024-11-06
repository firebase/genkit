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

import { startServer } from '@genkit-ai/tools-common/server';
import { logger } from '@genkit-ai/tools-common/utils';
import { spawn } from 'child_process';
import { Command } from 'commander';
import getPort, { makeRange } from 'get-port';
import { startManager } from '../utils/manager-utils';

interface RunOptions {
  noui?: boolean;
  port?: string;
}

/** Command to run code in dev mode and/or the Dev UI. */
export const start = new Command('start')
  .description('runs a command in Genkit dev mode')
  .option('-n, --noui', 'do not start the Dev UI', false)
  .option('-p, --port', 'port for the Dev UI')
  .action(async (options: RunOptions) => {

    let processPromise = Promise.resolve();
    if (start.args.length > 0) {
      processPromise = new Promise((urlResolver, reject) => {
        const appProcess = spawn(start.args[0], start.args.slice(1), {
          env: { ...process.env, GENKIT_ENV: 'dev' },
        });

        appProcess.stdout?.on('data', (data) => {
          process.stdout.write(data);
        });
        appProcess.stderr?.on('data', (data) => {
          process.stderr.write(data);
        });
        appProcess.on('error', (error): void => {
          console.log(`Error in app process: ${error}`);
          reject(error);
          process.exitCode = 1;
        });
        appProcess.on('exit', (code) => {
          urlResolver(undefined);
        });
      });
    }

    let uiPromise = Promise.resolve();
    if (!options.noui) {
      let port: number;
      if (options.port) {
        port = Number(options.port);
        if (isNaN(port) || port < 0) {
          logger.error(`"${options.port}" is not a valid port number`);
          return;
        }
      } else {
        port = await getPort({ port: makeRange(4000, 4099) });
      }
      uiPromise = startManager(true).then((manager) =>
        startServer(manager, port)
      );
    }

    await Promise.all([processPromise, uiPromise]);
  });
