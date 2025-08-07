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
import { getGenkitContext, initOrReplaceFile } from '../utils';

// Define constants at the module level for clarity and reuse.
const GENKIT_MD_PATH = 'GENKIT.md';

export const generic: AIToolModule = {
  name: 'generic',
  displayName: 'Simple GENKIT.md file',

  /**
   * Configures the Gemini CLI extension for Genkit.
   */
  async configure(options?: InitConfigOptions): Promise<AIToolConfigResult> {
    const files: AIToolConfigResult['files'] = [];

    // Generate GENKIT.md file.
    logger.info('Updating GENKIT.md...');
    const genkitContext = getGenkitContext();
    const baseResult = await initOrReplaceFile(GENKIT_MD_PATH, genkitContext);
    files.push({ path: GENKIT_MD_PATH, updated: baseResult.updated });
    logger.info('\n');
    logger.info(
      'GENKIT.md updated. Provide this file as context with your AI tool.'
    );
    return { files };
  },
};
