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

import { execSync } from 'child_process';

/**
 * Detects if the CLI is running from a local npm package vs global npm package.
 * When running from a local npm package, process.execPath
 * will point to the node runtime rather than the global node_modules location.
 */
export function runningFromNpmLocally(): boolean {
  // Check if running from a global node_modules location
  const globalNodeModules = execSync('npm root -g').toString().trim();
  const execPath = process.execPath;
  // If the execPath is inside the global node_modules directory, it's global
  if (execPath.startsWith(globalNodeModules)) {
    return false; // running globally, not locally
  }
  // Otherwise, assume it's local (e.g., npx, local install, or dev)
  return true;
}
