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

import { Command } from 'commander';
import { startServer } from '../server';
import { Runner } from '../runner/runner';
import { logger } from '../utils/logger';

interface StartOptions {
  headless?: boolean;
  port: string;
}

/** Command to start GenKit server, optionally without static file serving */
export const start = new Command('start')
  .option(
    '-x, --headless',
    'Do not serve static UI files (for development)',
    false
  )
  .option('-p, --port <number>', 'Port to serve on. Default is 4000', '4000')
  .action(async (options: StartOptions) => {
    const port = Number(options.port);
    if (isNaN(port) || port < 0) {
      logger.error(`"${options.port}" is not a valid port number`);
      return;
    }

    const runner = new Runner();
    await runner.start();
    return startServer(runner, options.headless ?? false, port);
  });
