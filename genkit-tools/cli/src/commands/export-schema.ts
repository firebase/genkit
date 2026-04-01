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

import { logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import * as fs from 'fs';
import * as path from 'path';

export const exportSchema = new Command('schema:export')
  .description('export the Genkit schema (genkit-schema.json) to a file path')
  .argument(
    '[outputPath]',
    'directory to export the schema to (defaults to current directory)',
    '.'
  )
  .action(async (outputPath: string) => {
    const schemaSource = path.resolve(__dirname, '..', 'genkit-schema.json');

    if (!fs.existsSync(schemaSource)) {
      logger.error(
        'Schema file not found. The CLI package may not have been built correctly.'
      );
      process.exit(1);
    }

    const resolvedOutput = path.resolve(outputPath);

    if (!fs.existsSync(resolvedOutput)) {
      logger.error(`Output directory does not exist: ${resolvedOutput}`);
      process.exit(1);
    }

    if (!fs.statSync(resolvedOutput).isDirectory()) {
      logger.error(`Output path is not a directory: ${resolvedOutput}`);
      process.exit(1);
    }

    const destFile = path.join(resolvedOutput, 'genkit-schema.json');
    fs.copyFileSync(schemaSource, destFile);
    logger.info(`Schema exported to ${destFile}`);
  });
