import { program, Command } from 'commander';
import { example } from './commands/example';
import { start } from './commands/start';
import { logger } from './utils/logger';
import * as clc from 'colorette';
import { getPluginCommands, getPluginSubCommand } from './commands/plugins';
import { flowRun } from './commands/flow-run';
import { evalExtractData } from './commands/eval-extract-data';
import { flowResume } from './commands/flow-resume';
import {
  ToolPluginSubCommandsSchema,
  SpecialAction,
} from '@google-genkit/tools-plugins/plugins';

/**
 * All commands need to be directly registered in this list.
 *
 * To add a new command to the CLI, create a file under src/commands that
 * exports a Command constant, then add it to the list below
 */
const commands: Command[] = [
  example,
  start,
  flowRun,
  flowResume,
  evalExtractData,
];

/** Main entry point for CLI. */
export async function startCLI(): Promise<void> {
  program.name('genkit').description('Google Genkit CLI').version('0.0.1');

  for (const command of commands) program.addCommand(command);
  for (const command of await getPluginCommands()) program.addCommand(command);

  for (const cmd of ToolPluginSubCommandsSchema.keyof().options) {
    program.addCommand(await getPluginSubCommand(cmd));
  }

  // Default action to catch unknown commands.
  program.action((_, { args }: { args: string[] }) => {
    logger.error(`"${clc.bold(args[0])}" is not a known Genkit command.`);
  });

  await program.parseAsync();
}
