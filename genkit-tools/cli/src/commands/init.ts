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

import { Runtime } from '@genkit-ai/tools-common/runner';
import { detectRuntime, logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import * as inquirer from 'inquirer';
import { initGo } from './init/init-go';
import { initNodejs } from './init/init-nodejs';

export type Platform = 'firebase' | 'other';
export type ModelProvider = 'googleai' | 'vertexai' | 'ollama' | 'none';
export type WriteMode = 'keep' | 'overwrite' | 'merge';

export interface InitOptions {
  // Deployment platform.
  platform: Platform;
  // Model provider.
  model: ModelProvider;
  // Path to local Genkit dist archive.
  distArchive: string;
  // Non-interactive mode.
  nonInteractive: boolean;
}

/** Supported runtimes for the init command. */
const supportedRuntimes: Record<string, string> = {
  nodejs: 'Node.js',
  go: 'Go (preview)',
};

export const init = new Command('init')
  .description('initialize a project directory with Genkit')
  .option(
    '-p, --platform <platform>',
    'Deployment platform (firebase, googlecloud, or other)'
  )
  .option(
    '-m, --model <model>',
    'Model provider (googleai, vertexai, ollama, or none)'
  )
  .option(
    '--non-interactive',
    'Run init in non-interactive mode (experimental)'
  )
  .option(
    '-d, --dist-archive <distArchive>',
    'Path to local Genkit dist archive'
  )
  .action(async (options: InitOptions) => {
    var isNew = false;
    var runtime = detectRuntime(process.cwd());
    if (!runtime) {
      logger.info('No runtime was detected in the current directory.');
      const answer = await inquirer.prompt<{ runtime: Runtime }>([
        {
          type: 'list',
          name: 'runtime',
          message: 'Select a runtime to initialize a Genkit project:',
          choices: Object.keys(supportedRuntimes).map((runtime) => ({
            name: supportedRuntimes[runtime],
            value: runtime,
          })),
        },
      ]);
      runtime = answer.runtime;
      isNew = true;
    } else if (!supportedRuntimes[runtime]) {
      logger.error(
        `The runtime could not be detected or is not supported. Supported runtimes: ${Object.keys(supportedRuntimes)}`
      );
      process.exit(1);
    }
    try {
      switch (runtime) {
        case 'nodejs':
          await initNodejs(options, isNew);
          break;
        case 'go':
          await initGo(options, isNew);
          break;
      }
    } catch (err) {
      logger.error(err);
      process.exit(1);
    }
    logger.info('Genkit successfully initialized.');
  });

/**
 * Displays info about the selected model.
 * @param model selected model
 */
export function showModelInfo(model: ModelProvider) {
  switch (model) {
    case 'googleai':
      logger.warn(
        `Google AI is currently available in limited regions. For a complete list, see https://ai.google.dev/available_regions#available_regions`
      );
      break;
    case 'vertexai':
      logger.info(
        `Run the following command to enable Vertex AI in your Google Cloud project:\n\n  gcloud services enable aiplatform.googleapis.com\n`
      );
      break;
    case 'ollama':
      logger.info(
        `If you don't have Ollama already installed and configured, refer to https://developers.google.com/genkit/plugins/ollama\n`
      );
      break;
  }
}

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
