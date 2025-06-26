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

import type { RuntimeManager } from '@genkit-ai/tools-common/manager';
import { startServer } from '@genkit-ai/tools-common/server';
import { findProjectRoot, logger } from '@genkit-ai/tools-common/utils';
import { spawn } from 'child_process';
import { Command } from 'commander';
import getPort, { makeRange } from 'get-port';
import open from 'open';
import { startManager } from '../utils/manager-utils';

interface RunOptions {
  noui?: boolean;
  port?: string;
  open?: boolean;
}

/** Command to run code in dev mode and/or the Dev UI. */
export const start = new Command('start')
  .description('runs a command in Genkit dev mode')
  .option('-n, --noui', 'do not start the Dev UI', false)
  .option('-p, --port <port>', 'port for the Dev UI')
  .option('-o, --open', 'Open the browser on UI start up')
  .action(async (options: RunOptions) => {
    // Always start the manager.
    let managerPromise: Promise<RuntimeManager> = startManager(
      await findProjectRoot(),
      true
    );
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
      managerPromise = managerPromise.then((manager) => {
        startServer(manager, port);
        return manager;
      });
      if (options.open) {
        open(`http://localhost:${port}`);
      }
    }
    await managerPromise.then((manager: RuntimeManager) => {
      const telemetryServerUrl = manager?.telemetryServerUrl;
      return startRuntime(telemetryServerUrl);
    });
  });

async function startRuntime(telemetryServerUrl?: string) {
  if (start.args.length > 0) {
    return new Promise((urlResolver, reject) => {
      const appProcess = spawn(start.args[0], start.args.slice(1), {
        env: {
          ...process.env,
          GENKIT_TELEMETRY_SERVER: telemetryServerUrl,
          GENKIT_ENV: 'dev',
        },
        shell: process.platform === 'win32',
      });

      const originalStdIn = process.stdin;
      appProcess.stderr?.pipe(process.stderr);
      appProcess.stdout?.pipe(process.stdout);
      process.stdin?.pipe(appProcess.stdin);

      appProcess.on('error', (error): void => {
        logger.error(`Error in app process: ${error}`);
        reject(error);
        process.exitCode = 1;
      });
      appProcess.on('exit', (code) => {
        process.stdin?.pipe(originalStdIn);
        if (code === 0) {
          urlResolver(undefined);
        } else {
          reject(new Error(`app process exited with code ${code}`));
        }
      });
    });
  }
  return new Promise(() => {}); // no runtime, return a hanging promise.
}
