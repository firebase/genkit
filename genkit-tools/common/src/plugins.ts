import * as clc from 'colorette';
import { execSync } from 'child_process';
import { createInterface } from 'readline/promises';
import { z } from 'zod';

const SupportedFlagValuesSchema = z.union([
  z.undefined(),
  z.string(),
  z.boolean(),
  z.array(z.string()),
]);

export const BaseToolPluginActionSchema = z.object({
  args: z.optional(
    z.array(
      z.object({
        description: z.string(),
        flag: z.string(), // Flag uses Commander syntax; i.e. '-q, --quiet'
        defaultValue: SupportedFlagValuesSchema,
      }),
    ),
  ),
  hook: z
    .function()
    .args(z.optional(z.record(z.string(), SupportedFlagValuesSchema)))
    .returns(z.union([z.void(), z.promise(z.void())])),
});

export const ToolPluginActionSchema = BaseToolPluginActionSchema.extend({
  action: z.string(),
  helpText: z.string(),
});

export const ToolPluginSchema = z.object({
  name: z.string(),
  keyword: z.string(),
  actions: z.array(ToolPluginActionSchema),
  specialActions: z.optional(
    z.object({
      login: z.optional(BaseToolPluginActionSchema),
    }),
  ),
});

export type SupportedFlagValues = z.infer<typeof SupportedFlagValuesSchema>;
export type BaseToolPluginAction = z.infer<typeof BaseToolPluginActionSchema>;
export type ToolPluginAction = z.infer<typeof ToolPluginActionSchema>;
export type ToolPlugin = z.infer<typeof ToolPluginSchema>;

const SEPARATOR = '===========================';

const readline = createInterface({
  input: process.stdin,
  output: process.stdout,
});

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
