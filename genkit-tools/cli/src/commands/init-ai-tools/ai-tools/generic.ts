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
import { AIToolConfigResult, AIToolModule, InitConfigOptions } from '../types';
import {
  GENKIT_PROMPT_PATH,
  getGenkitContext,
  initOrReplaceFile,
} from '../utils';

/** Configuration module for GENKIT.md context file for generic use */
export const generic: AIToolModule = {
  name: 'generic',
  displayName: 'GENKIT.md file for generic use',

  /**
   * Configures a GENKIT.md file for Genkit.
   */
  async configure(options?: InitConfigOptions): Promise<AIToolConfigResult> {
    const files: AIToolConfigResult['files'] = [];

    // Generate GENKIT.md file.
    logger.info('Updating GENKIT.md...');
    const genkitContext = getGenkitContext();
    const baseResult = await initOrReplaceFile(
      GENKIT_PROMPT_PATH,
      genkitContext
    );
    files.push({ path: GENKIT_PROMPT_PATH, updated: baseResult.updated });
    logger.info('\n');
    logger.info(
      'GENKIT.md updated. Provide this file as context with your AI tool.'
    );
    return { files };
  },
};
