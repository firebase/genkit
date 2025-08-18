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
import { select } from '@inquirer/prompts';
import { existsSync, readFileSync } from 'fs';
import { mkdir, writeFile } from 'fs/promises';
import path from 'path';
import { AIToolConfigResult, AIToolModule, InitConfigOptions } from '../types';
import {
  GENKIT_PROMPT_PATH,
  initGenkitFile,
  initOrReplaceFile,
  updateContentInPlace,
} from '../utils';

// GEMINI specific paths
const GEMINI_DIR = '.gemini';
const GEMINI_SETTINGS_PATH = path.join(GEMINI_DIR, 'settings.json');
const GEMINI_MD_PATH = path.join('GEMINI.md');

// GENKIT specific constants
const GENKIT_EXT_DIR = path.join(GEMINI_DIR, 'extensions', 'genkit');
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

const EXT_INSTALLATION = 'extension';
const MD_INSTALLATION = 'geminimd';
type InstallationType = typeof EXT_INSTALLATION | typeof MD_INSTALLATION;

/** Configuration module for Gemini CLI */
export const gemini: AIToolModule = {
  name: 'gemini',
  displayName: 'Gemini CLI',

  /**
   * Configures the Gemini CLI extension for Genkit.
   */
  async configure(options?: InitConfigOptions): Promise<AIToolConfigResult> {
    let installationMethod: InstallationType = EXT_INSTALLATION;
    if (!options?.yesMode) {
      installationMethod = await select({
        message: 'Select your preferred installation method',
        choices: [
          {
            name: 'Gemini CLI Extension',
            value: 'extension',
            description:
              'Use Gemini Extension to install Genkit context in a modular fashion',
          },
          {
            name: 'GEMINI.md',
            value: 'geminimd',
            description: 'Incorporate Genkit context within the GEMINI.md file',
          },
        ],
      });
    }

    if (installationMethod === EXT_INSTALLATION) {
      logger.info('Installing as part of GEMINI.md');
      return await installAsExtension();
    } else {
      logger.info('Installing as Gemini CLI extension');
      return await installInMdFile();
    }
  },
};

async function installInMdFile(): Promise<AIToolConfigResult> {
  const files: AIToolConfigResult['files'] = [];
  // Part 1: Generate GENKIT.md file.

  logger.info('Installing the Genkit MCP server for Gemini CLI');
  // Handle MCP configuration - merge with existing if present
  let existingConfig: any = {};
  let settingsUpdated = false;
  try {
    const fileExists = existsSync(GEMINI_SETTINGS_PATH);
    if (fileExists) {
      existingConfig = JSON.parse(readFileSync(GEMINI_SETTINGS_PATH, 'utf-8'));
    } else {
      await mkdir(GEMINI_DIR, { recursive: true });
    }
  } catch (e) {
    // File doesn't exist or is invalid JSON, start fresh
  }

  // Check if genkit server already exists
  if (!existingConfig.mcpServers?.genkit) {
    if (!existingConfig.mcpServers) {
      existingConfig.mcpServers = {};
    }
    existingConfig.mcpServers.genkit =
      GENKIT_EXTENSION_CONFIG.mcpServers.genkit;
    await writeFile(
      GEMINI_SETTINGS_PATH,
      JSON.stringify(existingConfig, null, 2)
    );
    settingsUpdated = true;
  }
  files.push({ path: GEMINI_SETTINGS_PATH, updated: settingsUpdated });

  // Copy GENKIT.md file
  logger.info('Copying the GENKIT.md file...');
  const baseResult = await initGenkitFile();
  files.push({ path: GENKIT_PROMPT_PATH, updated: baseResult.updated });

  logger.info('Updating GEMINI.md to include Genkit context');
  const geminiImportTag = `\nGenkit Framework Instructions:\n - @./GENKIT.md\n`;
  const { updated: mdUpdated } = await updateContentInPlace(
    GEMINI_MD_PATH,
    geminiImportTag,
    { hash: baseResult.hash }
  );
  files.push({ path: GEMINI_MD_PATH, updated: mdUpdated });

  return { files };
}

async function installAsExtension(): Promise<AIToolConfigResult> {
  const files: AIToolConfigResult['files'] = [];
  // Part 1: Generate GENKIT.md file.
  const baseResult = await initGenkitFile();
  files.push({ path: GENKIT_PROMPT_PATH, updated: baseResult.updated });

  // Part 2: Configure the main gemini-extension.json file, and gemini config directory if needed.
  logger.info('Configuring extentions files in user workspace');
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
}
