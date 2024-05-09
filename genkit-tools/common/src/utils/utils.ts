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
  dependencies: Record<string, string>;
  devDependencies: Record<string, string>;
}

function getPackageJson(directory: string): PackageJson | undefined {
  const packageJsonPath = path.join(directory, 'package.json');
  if (fs.existsSync(packageJsonPath)) {
    return JSON.parse(
      fs.readFileSync(packageJsonPath, 'utf8')
    ) as PackageJson;
  }
  return undefined;
}

/**
 * Returns the entry point of a Node.js app.
 */
export function getNodeEntryPoint(directory: string): string {
  const packageJson = getPackageJson(directory);
  return packageJson?.main || 'lib/index.js';
}

/**
 * Returns the entry point of any supported runtime.
 */
export function getEntryPoint(directory: string): string | undefined {
  const runtime = detectRuntime(directory);
  switch (runtime) {
    case 'node':
      return getNodeEntryPoint(directory);
    case 'go':
      return '.';
    case 'next.js':
      return path.join(__dirname, '../runner/harness.js');
    default:
      return;
  }
}

/**
 * Detects what runtime is used in the current directory.
 * @returns Runtime of the project directory.
 */
export function detectRuntime(directory: string): Runtime {
  if (fs.existsSync(path.join(directory, 'package.json'))) {
    const packageJson = getPackageJson(directory);
    if (packageJson?.dependencies.next || packageJson?.devDependencies.next) {
      return 'next.js';
    }
    return 'node';
  }
  const files = fs.readdirSync(directory);
  for (const file of files) {
    const filePath = path.join(directory, file);
    const stat = fs.statSync(filePath);
    if (stat.isFile() && path.extname(file) === '.go') {
      return 'go';
    }
  }
  return undefined;
}
