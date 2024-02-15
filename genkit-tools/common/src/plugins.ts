import * as clc from 'colorette';
import { execSync } from 'child_process';
import { createInterface } from 'readline/promises';

const SEPARATOR = '===========================';

const readline = createInterface({
  input: process.stdin,
  output: process.stdout,
});

export interface ToolPlugin {
  name: string;
  keyword: string;
  actions: ToolPluginAction[];
}

export interface ToolPluginAction {
  action: string;
  hook: () => unknown;
}

/**
 * Executes the command given, returning the contents of STDOUT.
 *
 * The contents of STDOUT are hidden during execution. This function will
 * also print out the commands that will be run for transparency to the user.
 */
export function cliCommand(command: string, options?: string): void {
  const commandString = command + (options ? ` ${options}` : '');
  console.log(`Running ${clc.bold(commandString)}...\n${SEPARATOR}`);

  try {
    execSync(commandString, { stdio: 'inherit', encoding: 'utf8' });
  } catch (e) {
    console.log(`${SEPARATOR}\n`);
    throw e;
  }

  console.log(`${SEPARATOR}\n`);
}

/**
 * Utility function to prompt user for sensitive operations.
 */
export async function promptContinue(
  message: string,
  dfault: boolean,
): Promise<boolean> {
  console.log(message);
  const opts = dfault ? 'Y/n' : 'y/N';
  const r = await readline.question(`${clc.bold('Continue')}? (${opts}) `);
  if (r === '') {
    return dfault;
  }

  return r.toLowerCase() === 'y';
}
