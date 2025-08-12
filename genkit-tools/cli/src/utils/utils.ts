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

/**
 * Detects if the CLI is running from a local npm package vs global npm package.
 * When running from a local npm package, process.execPath
 * will point to the node runtime rather than the global node_modules location.
 */
import * as path from 'path';

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
export function runningFromNpmLocally(): Promise<boolean> {
  return new Promise((resolve) => {
    exec('npm root -g', (error, stdout) => {
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
