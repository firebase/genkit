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

import { ToolPluginSubCommandsSchema } from '@genkit-ai/tools-common/plugin';
import {
  RunCommandEvent,
  logger,
  notifyAnalyticsIfFirstRun,
  record,
} from '@genkit-ai/tools-common/utils';
import { Command, program } from 'commander';
import { config } from './commands/config';
import { evalExtractData } from './commands/eval-extract-data';
import { evalFlow } from './commands/eval-flow';
import { evalRun } from './commands/eval-run';
import { flowBatchRun } from './commands/flow-batch-run';
import { flowRun } from './commands/flow-run';
import { mcp } from './commands/mcp';
import { getPluginCommands, getPluginSubCommand } from './commands/plugins';
import {
  SERVER_HARNESS_COMMAND,
  serverHarness,
} from './commands/server-harness';
import { start } from './commands/start';
import { uiStart } from './commands/ui-start';
import { uiStop } from './commands/ui-stop';
import { version } from './utils/version';

/**
 * All commands need to be directly registered in this list.
 *
 * To add a new command to the CLI, create a file under src/commands that
 * exports a Command constant, then add it to the list below
 */
const commands: Command[] = [
  uiStart,
  uiStop,
  flowRun,
  flowBatchRun,
  evalExtractData,
  evalRun,
  evalFlow,
  config,
  start,
  mcp,
];

/** Main entry point for CLI. */
export async function startCLI(): Promise<void> {
  program
    .name('genkit')
    .description('Genkit CLI')
    .version(version)
    .hook('preAction', async (_, actionCommand) => {
      await notifyAnalyticsIfFirstRun();

      // For now only record known command names, to avoid tools plugins causing
      // arbitrary text to get recorded. Once we launch tools plugins, we'll have
      // to give this more thought
      const commandNames = commands.map((c) => c.name());
      let commandName: string;
      if (commandNames.includes(actionCommand.name())) {
        commandName = actionCommand.name();
      } else if (
        actionCommand.parent &&
        commandNames.includes(actionCommand.parent.name())
      ) {
        commandName = actionCommand.parent.name();
      } else {
        commandName = 'unknown';
      }
      await record(new RunCommandEvent(commandName));
    });

  // When running as a spawned UI server process, argv[1] will be '__server-harness'
  // instead of a normal command. This allows the same binary to serve both CLI and server roles.
  if (process.argv[2] === SERVER_HARNESS_COMMAND) {
    program.addCommand(serverHarness);
  }

  for (const command of commands) program.addCommand(command);
  for (const command of await getPluginCommands()) program.addCommand(command);

  for (const cmd of ToolPluginSubCommandsSchema.keyof().options) {
    const command = await getPluginSubCommand(cmd);
    if (command) {
      program.addCommand(command);
    }
  }
  program.addCommand(
    new Command('help').action(() => {
      logger.info(program.help());
    })
  );
  // Default action to catch unknown commands.
  program.action(() => {
    // print help
    logger.info(program.help());
  });

  await program.parseAsync();
}
