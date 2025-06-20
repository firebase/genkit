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
import { Command } from 'commander';
import fs from 'fs';
import { startManager } from './manager-utils';

function redirectStdoutToFile(logFile: string) {
  const myLogFileStream = fs.createWriteStream(logFile);

  const originalStdout = process.stdout.write;
  function writeStdout() {
    originalStdout.apply(process.stdout, arguments as any);
    myLogFileStream.write.apply(myLogFileStream, arguments as any);
  }

  process.stdout.write = writeStdout as any;
  process.stderr.write = process.stdout.write;
}

export const uiStartServer = new Command('__ui:start-server')
  .argument('<port>', 'Port to serve on')
  .argument('<logFile>', 'Log file path')
  .action(async (port: string, logFile: string) => {
    redirectStdoutToFile(logFile);

    process.on('error', (error): void => {
      console.log(`Error in tools process: ${error}`);
    });
    process.on('uncaughtException', (err, somethingelse) => {
      console.log(`Uncaught error in tools process: ${err} ${somethingelse}`);
    });
    process.on('unhandledRejection', (reason, p) => {
      console.log(`Unhandled rejection in tools process: ${reason}`);
    });

    const portNum = Number.parseInt(port) || 4100;
    const manager = await startManager(true);
    await startServer(manager, portNum);
  });
