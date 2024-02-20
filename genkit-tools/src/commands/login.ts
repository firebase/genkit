import { Command } from 'commander';
import { logger } from '../utils/logger';
import { findToolsConfig } from '@google-genkit/tools-plugins/config';
import * as clc from 'colorette';
import { attachPluginActionToCommand } from './plugins';

/** Gets login commands from plugins that support it. */
export async function getLoginCommands(): Promise<Command> {
  const config = await findToolsConfig();
  const actions = (config?.cliPlugins || [])
    .filter((p) => !!p.specialActions?.login)
    .map((p) => ({
      keyword: p.keyword,
      name: p.name,
      ...p.specialActions!.login!,
    }));
  const command = new Command('login').description('Login using tools plugins');

  if (!actions.length) {
    return command.action(() => {
      logger.error(
        'No plugins installed that support login. Add a supported ' +
          `plugin to your ${clc.bold('genkit-tools.conf.js')} file.`,
      );
    });
  }

  for (const a of actions) {
    const subcmd = command
      .command(a.keyword)
      .description(a.name + ' ' + clc.italic('(plugin)'));
    attachPluginActionToCommand(subcmd, a);
  }

  return command;
}
