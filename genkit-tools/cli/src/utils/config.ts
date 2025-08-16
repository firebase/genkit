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

import * as fs from 'fs';
import * as os from 'os';
import path from 'path';

/**
 * Gets the path to the genkit config file
 */
export function getConfigFilePath(): string {
  return path.join(os.homedir(), '.genkit-config.json');
}

/**
 * Reads the genkit configuration
 */
export function readConfig(): { notificationsDisabled?: boolean } {
  try {
    const configPath = getConfigFilePath();
    if (fs.existsSync(configPath)) {
      const configData = fs.readFileSync(configPath, 'utf8');
      return JSON.parse(configData);
    }
  } catch {
    // If we can't read the config, return empty object
  }
  return {};
}

/**
 * Writes the genkit configuration
 */
export function writeConfig(config: { notificationsDisabled?: boolean }): void {
  try {
    const configPath = getConfigFilePath();
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  } catch {
    // If we can't write the config, it's not critical
  }
}
