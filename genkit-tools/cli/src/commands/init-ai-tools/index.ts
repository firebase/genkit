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

import { logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { InitConfigOptions } from './types';
import { detectSupportedTools } from './utils';

export const init = new Command('init:ai-tools')
  .description(
    'initialize AI tools in a workspace with helpful context related to the Genkit framework'
  )
  .option('-y', '--yes', 'Run in non-interactive mode (experimental)')
  .action(async (options: InitConfigOptions) => {
    const detectedTools = await detectSupportedTools();
    if (detectedTools.length === 0) {
      logger.info('Could not auto-detect any AI tools.');
      // TODO: Start manual init flow
    }
    logger.info(
      'Auto-detected AI tools:\n' +
        detectedTools.map((t) => t.displayName).join('\n')
    );
    try {
      for (const supportedTool of detectedTools) {
        await supportedTool.configure(options);
      }
    } catch (err) {
      logger.error(err);
      process.exit(1);
    }
  });
