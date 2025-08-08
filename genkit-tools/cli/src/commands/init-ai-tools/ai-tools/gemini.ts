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
import { mkdir } from 'fs/promises';
import path from 'path';
import { GENKIT_PROMPT_PATH } from '../constants';
import { AIToolConfigResult, AIToolModule, InitConfigOptions } from '../types';
import { getGenkitContext, initOrReplaceFile } from '../utils';

// Define constants at the module level for clarity and reuse.
const GENKIT_EXT_DIR = path.join('.gemini', 'extensions', 'genkit');
const GENKIT_MD_REL_PATH = path.join('..', '..', '..', GENKIT_PROMPT_PATH);
const GENKIT_EXTENSION_CONFIG = {
  name: 'genkit',
  version: '1.0.0',
  mcpServers: {
    genkit: {
      command: 'npx',
      args: ['genkit', 'mcp'],
      cwd: '.',
      timeout: 30000,
      trust: false,
      excludeTools: [
        'run_shell_command(genkit start)',
        'run_shell_command(npx genkit start)',
      ],
    },
  },
  contextFileName: GENKIT_MD_REL_PATH,
};

/** Configuration module for Gemini CLI */
export const gemini: AIToolModule = {
  name: 'gemini',
  displayName: 'Gemini CLI',

  /**
   * Configures the Gemini CLI extension for Genkit.
   */
  async configure(options?: InitConfigOptions): Promise<AIToolConfigResult> {
    // TODO(ssbushi): Support option to install as file import vs extension
    const files: AIToolConfigResult['files'] = [];

    // Part 1: Generate GENKIT.md file.

    logger.info('Copying the GENKIT.md file...');
    const genkitContext = getGenkitContext();
    const baseResult = await initOrReplaceFile(
      GENKIT_PROMPT_PATH,
      genkitContext
    );
    files.push({ path: GENKIT_PROMPT_PATH, updated: baseResult.updated });

    // Part 2: Configure the main gemini-extension.json file, and gemini config directory if needed.
    logger.info('Configuring extentions files in user workspace...');
    await mkdir(GENKIT_EXT_DIR, { recursive: true });
    const extensionPath = path.join(GENKIT_EXT_DIR, 'gemini-extension.json');

    let extensionUpdated = false;
    try {
      const { updated } = await initOrReplaceFile(
        extensionPath,
        JSON.stringify(GENKIT_EXTENSION_CONFIG, null, 2)
      );
      extensionUpdated = updated;
      if (extensionUpdated) {
        logger.info(
          `Genkit extension for Gemini CLI initialized at ${extensionPath}`
        );
      }
    } catch (err) {
      logger.error(err);
      process.exit(1);
    }
    files.push({ path: extensionPath, updated: extensionUpdated });

    return { files };
  },
};
