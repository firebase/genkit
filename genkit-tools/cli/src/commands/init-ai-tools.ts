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
import { default as commandExists } from 'command-exists';
import { Command } from 'commander';
import { existsSync } from 'fs';
import { mkdir, writeFile } from 'fs/promises';
import * as inquirer from 'inquirer';
import path from 'path';
import { GENKIT_DOCS } from './genkit-docs';

export interface CommandOptions {
  // yes (non-interactive) mode.
  yesMode: boolean;
}

const GENKIT_MCP_CONFIG = {
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
  contextFileName: './GENKIT.md',
};

/** Supported AI tools. */
const SUPPORTED_AI_TOOLS: string[] = ['gemini'];

export const init = new Command('init:ai-tools')
  .description(
    'initialize AI tools in a workspace with helpful context related to the Genkit framework'
  )
  .option('-y', '--yes', 'Run in non-interactive mode (experimental)')
  .action(async (options: CommandOptions) => {
    const detectedTools = await detectAiTools();
    if (detectedTools.length === 0) {
      logger.info('Could not auto-detect any AI tools.');
      // TODO: Start manual init flow
    }
    try {
      for (const supportedTool of detectedTools) {
        switch (supportedTool.name) {
          case 'gemini':
            if (supportedTool.localConfigPath) {
            } else {
              logger.info(
                'Your Gemini CLI has not been setup with workspace configuration. Genkit will attempt to create one now...'
              );
              const genkitConfig = path.join('.gemini', 'extensions', 'genkit');
              await mkdir(genkitConfig, { recursive: true });
              // write extension
              await writeFile(
                path.join(genkitConfig, 'gemini-extension.json'),
                JSON.stringify(GENKIT_MCP_CONFIG, null, 2)
              );
              await writeFile(
                path.join(genkitConfig, 'GENKIT.md'),
                GENKIT_DOCS
              );
              logger.info('Wrote Genkit config for MCP, ready to go!');
            }
        }
      }
    } catch (err) {
      logger.error(err);
      process.exit(1);
    }
  });

/**
 * Shows a confirmation prompt.
 */
export async function confirm(args: {
  default?: boolean;
  message?: string;
}): Promise<boolean> {
  const message = args.message ?? `Do you wish to continue?`;
  const answer = await inquirer.prompt({
    type: 'confirm',
    name: 'confirm',
    message,
    default: args.default,
  });
  return answer.confirm;
}

interface AiToolConfig {
  name: string;
  localConfigPath?: string;
}
/**
 * Detects what AI tools are available in the current directory.
 * @returns List of detected {@link AiToolConfig}
 */
export async function detectAiTools(): Promise<AiToolConfig[]> {
  let tools: AiToolConfig[] = [];
  for (const tool of SUPPORTED_AI_TOOLS) {
    switch (tool) {
      case 'gemini':
        const cliFound = await commandExists('gemini');
        if (cliFound) {
          const hasLocalSettings = existsSync('.gemini');
          tools.push(
            hasLocalSettings
              ? { name: 'gemini', localConfigPath: '.gemini/' }
              : { name: 'gemini' }
          );
        }
      default:
        logger.warn('Unhandled supported tool');
    }
  }
  return tools;
}
