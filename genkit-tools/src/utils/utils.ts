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

import * as path from 'path';
import * as fs from 'fs';

interface PackageJson {
  main: string;
}

/**
 * Returns the entry point of a Node.js app.
 * @param directory directory to check
 */
export function getNodeEntryPoint(directory: string): string {
  const packageJsonPath = path.join(directory, 'package.json');
  const defaultMain = 'lib/index.js';
  if (fs.existsSync(packageJsonPath)) {
    const packageJson = JSON.parse(
      fs.readFileSync(packageJsonPath, 'utf8')
    ) as PackageJson;
    return packageJson.main || defaultMain;
  }
  return defaultMain;
}
