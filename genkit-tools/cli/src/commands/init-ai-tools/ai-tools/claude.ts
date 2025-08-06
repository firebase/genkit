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
import commandExists from 'command-exists';
import { existsSync, readFileSync } from 'fs';
import { writeFile } from 'fs/promises';
import { AIToolConfigResult, AIToolModule, InitConfigOptions } from '../types';
import {
  calculateHash,
  getGenkitContext,
  initOrReplaceFile,
  updateContentInPlace,
} from '../utils';

const CLAUDE_MCP_PATH = '.mcp.json';
const CLAUDE_PROMPT_PATH = 'CLAUDE.md';
const GENKIT_PROMPT_PATH = 'GENKIT.md';

export const claude: AIToolModule = {
  name: 'claude',
  displayName: 'Claude Code',

  async detect(): Promise<boolean> {
    const cliFound = await commandExists('claude');
    return !!cliFound;
  },

  /**
   * Configures Claude Code with Genkit context.
   *
   * - .claude/settings.local.json: Merges with existing config (preserves user settings)
   * - CLAUDE.local.md: Updates Firebase section only (preserves user content)
   */
  async configure(options?: InitConfigOptions): Promise<AIToolConfigResult> {
    const files: AIToolConfigResult['files'] = [];

    // Handle MCP configuration - merge with existing if present
    let existingConfig: any = {};
    let settingsUpdated = false;
    try {
      const fileExists = existsSync(CLAUDE_MCP_PATH);
      if (fileExists) {
        existingConfig = JSON.parse(readFileSync(CLAUDE_MCP_PATH, 'utf-8'));
      }
    } catch (e) {
      // File doesn't exist or is invalid JSON, start fresh
    }

    // Check if firebase server already exists
    if (!existingConfig.mcpServers?.genkit) {
      if (!existingConfig.mcpServers) {
        existingConfig.mcpServers = {};
      }
      existingConfig.mcpServers.genkit = {
        command: 'npx',
        args: ['genkit', 'mcp'],
      };
      await writeFile(CLAUDE_MCP_PATH, JSON.stringify(existingConfig, null, 2));
      settingsUpdated = true;
    }

    files.push({ path: CLAUDE_MCP_PATH, updated: settingsUpdated });

    logger.info('Copying the Genkit context to GENKIT.md...');
    const genkitContext = getGenkitContext();
    const { updated: genkitContextUpdated } = await initOrReplaceFile(
      GENKIT_PROMPT_PATH,
      genkitContext
    );
    files.push({ path: GENKIT_PROMPT_PATH, updated: genkitContextUpdated });

    logger.info('Updating CLAUDE.md to include Genkit context...');
    const claudeImportTag = `\nGenkit Framework Instructions:\n - @GENKIT.md\n`;
    const baseResult = await updateContentInPlace(
      CLAUDE_PROMPT_PATH,
      claudeImportTag,
      { hash: calculateHash(genkitContext) }
    );

    files.push({ path: CLAUDE_PROMPT_PATH, updated: baseResult.updated });
    return { files };
  },
};
