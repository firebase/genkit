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
import { logger } from './logger';

interface PackageJson {
  main?: string;
  scripts?: Record<string, string>;
}

/**
 * Reads and parses the package.json file from the given directory.
 * @param directory The directory containing the package.json file.
 * @returns The parsed package.json object or null if not found.
 */
export function getPackageJson(
  directory: string = process.cwd()
): PackageJson | null {
  const packageJsonPath = path.join(directory, 'package.json');
  if (fs.existsSync(packageJsonPath)) {
    try {
      return JSON.parse(
        fs.readFileSync(packageJsonPath, 'utf8')
      ) as PackageJson;
    } catch (error) {
      logger.error('Error parsing package.json:', error);
    }
  }
  return null;
}

/**
 * Returns the entry point of a Node.js app.
 */
export function getNodeEntryPoint(directory: string = process.cwd()): string {
  const packageJson = getPackageJson(directory);
  return packageJson?.main || 'lib/index.js';
}

/**
 * Detects what runtime is used in the current directory.
 * @returns Runtime of the project directory.
 */
export function detectRuntime(directory: string = process.cwd()): Runtime {
  const files = fs.readdirSync(directory);
  for (const file of files) {
    const filePath = path.join(directory, file);
    const stat = fs.statSync(filePath);
    if (stat.isFile() && (path.extname(file) === '.go' || file === 'go.mod')) {
      return 'go';
    }
  }
  return getPackageJson(directory) ? 'nodejs' : undefined;
}

/**
 * Returns the path to the tsx binary.
 */
export function getTsxBinaryPath(): string {
  const localLinkedTsxPath = path.join(
    __dirname,
    '../../../node_modules/.bin/tsx'
  );
  const globallyInstalledTsxPath = path.join(
    __dirname,
    '../../../../../.bin/tsx'
  );
  if (fs.existsSync(localLinkedTsxPath)) {
    return localLinkedTsxPath;
  } else if (fs.existsSync(globallyInstalledTsxPath)) {
    return globallyInstalledTsxPath;
  } else {
    throw new Error('Failed to find tsx binary.');
  }
}
