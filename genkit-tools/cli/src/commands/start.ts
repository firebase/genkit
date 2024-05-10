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

import { Runner } from '@genkit-ai/tools-common/runner';
import { startServer } from '@genkit-ai/tools-common/server';
import { logger } from '@genkit-ai/tools-common/utils';
import * as clc from 'colorette';
import { Command } from 'commander';

interface StartOptions {
  headless?: boolean;
  port: string;
  attach?: string;
  open?: boolean;
}

/** Command to start GenKit server, optionally without static file serving */
export const start = new Command('start')
  .description('run the app in dev mode and start a Developer UI')
  .option(
    '-x, --headless',
    'Do not serve static UI files (for development)',
    false
  )
  .option('-p, --port <number>', 'Port to serve on. Default is 4000', '4000')
  .option('-o, --open', 'Open the browser with the Developer UI')
  .option(
    '-a, --attach <number>',
    'Externally running dev process address to attach to'
  )
  .action(async (options: StartOptions) => {
    const port = Number(options.port);
    if (isNaN(port) || port < 0) {
      logger.error(`"${options.port}" is not a valid port number`);
      return;
    }

    const runner = new Runner();
    if (options.attach) {
      try {
        await runner.attach(options.attach);
      } catch (e) {
        logger.error(clc.red(clc.bold((e as Error).message)));
        return;
      }
    } else {
      await runner.start();
    }
    return startServer(runner, options.headless ?? false, port, !!options.open);
  });
