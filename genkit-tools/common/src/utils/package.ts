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

import { readFileSync } from 'fs';
import { join } from 'path';

const packagePath = join(__dirname, '../../../package.json'); 
                                    
interface MinimalPackageJson {
  name: string;
  version: string;
  [key: string]: any;
}

// Attempt to read package.json, with a fallback for safety,
// though Bun's bundling should make this reliable.
let pkg: MinimalPackageJson;
try {
  pkg = JSON.parse(readFileSync(packagePath, 'utf8')) as MinimalPackageJson;
} catch (e) {
  // This fallback should ideally not be hit if Bun bundles the package.json correctly.
  // Logging a warning if it does get hit during development or in a strange environment.
  console.warn(`[genkit-tools-common] Warning: Could not read package.json at '${packagePath}'. Using fallback values. Error: ${e}`);
  pkg = { name: 'genkit-tools', version: '0.0.0-fallback' };
}

export const toolsPackage = pkg;
