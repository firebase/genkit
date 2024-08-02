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

import * as fs from 'fs';
import * as path from 'path';
import { Runtime } from '../runner/types';

interface PackageJson {
  main: string;
}

/**
 * Returns the entry point of a Node.js app.
 */
export function getNodeEntryPoint(directory: string): string {
  const packageJsonPath = path.join(directory, 'package.json');
  let entryPoint = 'lib/index.js';
  if (fs.existsSync(packageJsonPath)) {
    const packageJson = JSON.parse(
      fs.readFileSync(packageJsonPath, 'utf8')
    ) as PackageJson;
    entryPoint = packageJson.main;
  }
  return entryPoint;
}

/**
 * Returns the entry point of any supported runtime.
 */
export function getEntryPoint(directory: string): string | undefined {
  const runtime = detectRuntime(directory);
  switch (runtime) {
    case 'nodejs':
      return getNodeEntryPoint(directory);
    case 'go':
      return '.';
    default:
      return;
  }
}

/**
 * Detects what runtime is used in the current directory.
 * @returns Runtime of the project directory.
 */
export function detectRuntime(directory: string): Runtime {
  const files = fs.readdirSync(directory);
  for (const file of files) {
    const filePath = path.join(directory, file);
    const stat = fs.statSync(filePath);
    if (stat.isFile() && (path.extname(file) === '.go' || file === 'go.mod')) {
      return 'go';
    }
  }
  if (fs.existsSync(path.join(directory, 'package.json'))) {
    return 'nodejs';
  }
  return undefined;
}
