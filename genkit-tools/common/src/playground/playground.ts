/**
 * Copyright 2025 Google LLC
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
import { spawn } from 'child_process';
import fs from 'fs/promises';
import path from 'path';
import { findPlaygroundDir, logger, writeFileIfNotExists } from '../utils';
import {
  playgroundStarterScript,
  playgroundStarterScriptName,
} from './starter';

export class PlaygroundManager {
  constructor(readonly projectRoot: string) {}

  private packageJsonName = 'package.json';

  /**
   * Writes a Genkit Typescript project to disk that can be used as a
   * playground starting point. Does nothing if one exists already.
   *
   * @return The path to the starter script.
   */
  async createPlayground(): Promise<string> {
    // Initialize a project in the root directory if one doesn't exist.
    await this.npmInitIfNeeded(this.projectRoot);

    // Install the minimum dependencies.
    logger.debug(`Installing dependencies...`);
    await this.runCommand(this.projectRoot, 'npm', [
      'install',
      'genkit',
      '@genkit-ai/googleai',
    ]);

    // Generate the starter script.
    const playgroundDir = await findPlaygroundDir(this.projectRoot);
    await fs.mkdir(playgroundDir, { recursive: true });
    const scriptFilePath = path.join(
      playgroundDir,
      playgroundStarterScriptName
    );
    await writeFileIfNotExists(scriptFilePath, playgroundStarterScript);

    return scriptFilePath;
  }

  /**
   * Spawns a child process to run `npm init -y` in the given directory if
   * `package.json` doesn't exist already.
   *
   * @param directory The absolute path to the directory where it should be run.
   * @returns A Promise that resolves when the installation is successful and rejects on error.
   */
  async npmInitIfNeeded(directory: string): Promise<void> {
    const packageFilePath = path.join(directory, this.packageJsonName);
    try {
      await fs.access(packageFilePath);
      logger.debug(`Found an existing project.`);
    } catch (error: any) {
      // File didn't exist. Create one.
      if (error.code === 'ENOENT') {
        logger.debug(`Creating a new project...`);
        await this.runCommand(directory, 'npm', ['init', '-y']);
      } else {
        // For other errors such as permissions, rethrow to reject the Promise.
        throw error;
      }
    }
  }

  /**
   * Spawns a child process to run the given command with the given arguments in
   * the given directory.
   *
   * @param directory The directory where the command should be run.
   * @param command The command to run (e.g., 'npm').
   * @param args An array of arguments for the command (e.g., ['install', 'foo']).
   * @returns A Promise that resolves on success and rejects on error.
   */
  async runCommand(
    directory: string,
    command: string,
    args: string[]
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const fullCommand =
        process.platform === 'win32' ? `${command}.cmd` : command;
      const childProcess = spawn(fullCommand, args, {
        cwd: directory,
        stdio: 'inherit',
      });

      // The 'close' event signals that the process has finished.
      childProcess.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(
            new Error(
              `Command '${command} ${args.join(' ')}' failed with exit code ${code}`
            )
          );
        }
      });

      // The 'error' event is for errors spawning the process itself. For
      // example if `npm` command is not found on the PATH.
      childProcess.on('error', (err) => {
        reject(err);
      });
    });
  }
}
