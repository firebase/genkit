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

import { exec } from 'child_process';
import * as path from 'path';

interface PackageManager {
  type: string;
  localInstallCommand: string;
  globalInstallCommand: string;
  globalRootCommand: string;
}

export const PACKAGE_MANAGERS: Record<string, PackageManager> = {
  npm: {
    type: 'npm',
    localInstallCommand: 'npm install',
    globalInstallCommand: 'npm install -g',
    globalRootCommand: 'npm root -g',
  },
  pnpm: {
    type: 'pnpm',
    localInstallCommand: 'pnpm install',
    globalInstallCommand: 'pnpm install -g',
    globalRootCommand: 'pnpm root -g',
  },
  yarn: {
    type: 'yarn',
    localInstallCommand: 'yarn install',
    globalInstallCommand: 'yarn install -g',
    globalRootCommand: 'yarn global bin',
  },
};

/**
 * Caches the package manager type to avoid multiple calls to the same command.
 */
let detectedPackageManager: PackageManager | undefined;

/**
 * Detects which global package manager (npm, pnpm, yarn) was used to install the CLI,
 * based on the location of the entry script.
 *
 * @returns The detected global package manager, or undefined if not found.
 */
export async function detectGlobalPackageManager(): Promise<PackageManager | undefined> {
  // Return cached value if available
  if (detectedPackageManager) {
    return detectedPackageManager;
  }

  const entryScript = process.argv[1] ? path.resolve(process.argv[1]) : '';

  for (const key of Object.keys(PACKAGE_MANAGERS)) {
    const pm = PACKAGE_MANAGERS[key];
    const globalPath = await getGlobalPath(pm.globalRootCommand);
    if (globalPath && entryScript.startsWith(globalPath)) {
      detectedPackageManager = pm;
      break;
    }
  }

  return detectedPackageManager;

  function getGlobalPath(command: string): Promise<string | undefined> {
    return new Promise((resolve) => {
      exec(command, (error, stdout) => {
        if (error) {
          resolve(undefined);
        } else {
          resolve(stdout.toString().trim());
        }
      });
    });
  }
}

/**
 * Determines if the CLI is running from a local npm install (e.g., npx, local node_modules/.bin)
 * vs a global npm install. This checks the location of the entry script (process.argv[1])
 * to see if it resides within the global node_modules directory.
 *
 * Returns:
 *   - true: if running from a local install (including npx, local node_modules, or dev)
 *   - false: if running from a global npm install
 *
 * Note: This is a heuristic and may not be 100% accurate in all edge cases.
 */
export async function runningFromNpmLocally(): Promise<boolean> {
  const pm = await detectGlobalPackageManager();
  const globalRootCmd = pm ? pm.globalRootCommand : PACKAGE_MANAGERS.npm.globalRootCommand;
  return new Promise((resolve) => {
    exec(globalRootCmd, (error, stdout) => {
      if (error) {
        // If we can't determine, assume local for safety
        resolve(true);
        return;
      }
      const globalNodeModules = stdout.toString().trim();

      // process.argv[1] is the entry script (e.g., .../node_modules/.bin/genkit or .../bin/genkit.js)
      const entryScript = process.argv[1] ? path.resolve(process.argv[1]) : '';

      // If the entry script is inside the global node_modules directory, it's global
      if (entryScript && entryScript.startsWith(globalNodeModules)) {
        resolve(false); // running globally, not locally
      } else {
        // Otherwise, assume it's local (e.g., npx, local install, or dev)
        resolve(true);
      }
    });
  });
}
