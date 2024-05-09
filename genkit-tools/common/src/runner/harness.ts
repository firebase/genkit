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

import { glob } from 'glob';
import * as path from 'path';
import { logger } from '../utils';

async function main() {
  logger.info(`Loading file paths: ${process.argv[2]}`);
  const files = await glob(process.argv[2].split(','));
  for (const file of files) {
    logger.info(`Loading \`${file}\`...`);
    await import(path.join(process.cwd(), file));
  }
}

main();
