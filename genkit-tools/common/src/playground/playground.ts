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
import { findPlaygroundDir, writeFileIfNotExists } from '../utils';
import {
  playgroundPackagesName,
  playgroundStarterPackages,
  playgroundStarterScript,
  playgroundStarterScriptName,
} from './starter';

export class PlaygroundManager {
  constructor(readonly projectRoot: string) {}

  /**
   * Writes a Genkit Typescript project to disk that can be used as a
   * playground starting point. Does nothing if one exists already.
   *
   * @return The path to the starter script.
   */
  async createPlayground(): Promise<string> {
    const playgroundDir = await findPlaygroundDir(this.projectRoot);
    await fs.mkdir(playgroundDir, { recursive: true });

    // Generate the files
    const scriptFilePath = path.join(
      playgroundDir,
      playgroundStarterScriptName
    );
    await writeFileIfNotExists(scriptFilePath, playgroundStarterScript);
    const packagesFilePath = path.join(playgroundDir, playgroundPackagesName);
    await writeFileIfNotExists(packagesFilePath, playgroundStarterPackages);

    // Run npm install
    await this.runNpmInstall(playgroundDir);

    return scriptFilePath;
  }

  /**
   * Spawns a child process to run `npm install` in a specified directory.
   *
   * @param directory The absolute path to the directory where `npm install` should be run.
   * @returns A Promise that resolves when the installation is successful and rejects on error.
   */
  runNpmInstall(directory: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const command = process.platform === 'win32' ? 'npm.cmd' : 'npm';
      const args = ['install'];

      // Spawn the child process.
      const childProcess = spawn(command, args, {
        cwd: directory,
        stdio: 'inherit',
      });

      // The 'close' event signals that the process has finished.
      childProcess.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`npm install failed with exit code ${code}`));
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
