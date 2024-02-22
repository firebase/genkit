import { findToolsConfig } from '@google-genkit/tools-plugins/config';
import {
  ToolPlugin,
  BaseToolPluginAction,
  SupportedFlagValues,
} from '@google-genkit/tools-plugins/plugins';
import { Command } from 'commander';
import * as clc from 'colorette';

/** Gets plugin commands based on the tools config file, if present. */
export async function getPluginCommands(): Promise<Command[]> {
  const config = await findToolsConfig();
  return (config?.cliPlugins || []).map(pluginToCommander);
}

export function attachPluginActionToCommand(
  cmd: Command,
  action: BaseToolPluginAction
): void {
  for (const o of action.args || []) {
    cmd.option(o.flag, o.description, o.defaultValue);
  }
  cmd.action(async (options: Record<string, SupportedFlagValues>) => {
    await action.hook(options);
  });
}

function pluginToCommander(p: ToolPlugin): Command {
  const cmd = new Command(p.keyword).description(
    p.name + ' ' + clc.italic('(plugin)')
  );
  for (const a of p.actions) {
    const subcmd = cmd.command(a.action).description(a.helpText);
    attachPluginActionToCommand(subcmd, a);
  }
  return cmd;
}
