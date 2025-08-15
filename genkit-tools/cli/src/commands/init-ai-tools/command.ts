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
import { checkbox } from '@inquirer/prompts';
import * as clc from 'colorette';
import { Command } from 'commander';
import { AI_TOOLS } from './constants';
import { AIToolChoice, InitConfigOptions } from './types';

const AGENT_CHOICES: AIToolChoice[] = Object.values(AI_TOOLS).map((tool) => ({
  value: tool.name,
  name: tool.displayName,
  checked: false,
}));

/**
 * Initializes selected AI tools with Genkit MCP server and Genkit framework
 * context to improve output quality when using those tools.
 */
export const initAiTools = new Command('init:ai-tools')
  .description(
    'initialize AI tools in a workspace with helpful context related to the Genkit framework (EXPERIMENTAL, subject to change)'
  )
  .option('-y', '--yes', 'Run in non-interactive mode')
  .action(async (options: InitConfigOptions) => {
    logger.info('\n');
    logger.info(
      'This command will configure AI coding assistants to work with your Genkit app by:'
    );
    logger.info(
      '• Configuring the Genkit MCP server for direct Genkit operations'
    );
    logger.info('• Installing context files that help AI understand:');
    logger.info('  - Genkit app structure and common design patterns');
    logger.info('  - Common Genkit features and how to use them');
    logger.info('\n');
    const selections = await checkbox({
      message: 'Which tools would you like to configure?',
      choices: AGENT_CHOICES,
      validate: (choices) => {
        if (choices.length === 0) {
          return 'Must select at least one tool.';
        }
        return true;
      },
      loop: true,
    });

    logger.info('\n');
    logger.info('Configuring selected tools...');
    await configureTools(selections, options);
  });

async function configureTools(tools: string[], options: InitConfigOptions) {
  // Configure each selected tool
  let anyUpdates = false;

  for (const toolName of tools) {
    const tool = AI_TOOLS[toolName];
    if (!tool) {
      logger.warn(`Unknown tool: ${toolName}`);
      continue;
    }

    const result = await tool.configure(options);

    // Count updated files
    const updatedCount = result.files.filter((f) => f.updated).length;
    const hasChanges = updatedCount > 0;

    if (hasChanges) {
      anyUpdates = true;
      logger.info('\n');
      logger.info(
        clc.green(
          `${tool.displayName} configured - ${updatedCount} file${updatedCount > 1 ? 's' : ''} updated:`
        )
      );
    } else {
      logger.info('\n');
      logger.info(`${tool.displayName} - all files up to date`);
    }

    // Always show the file list
    for (const file of result.files) {
      const status = file.updated ? '(updated)' : '(unchanged)';
      logger.info(`•  ${file.path} ${status}`);
    }
  }
  logger.info('\n');

  if (anyUpdates) {
    logger.info(clc.green('AI tools configuration complete!'));
    logger.info('\n');
    logger.info('Next steps:');
    logger.info('•  Restart your AI tools to load the new configuration');
    logger.info(
      '•  Your AI tool should have access to Genkit documentation and tools for greater access and understanding of your app.'
    );
  } else {
    logger.info(clc.green('All AI tools are already up to date.'));
  }
}
