import { findToolsConfig } from '@google-genkit/tools-plugins/config';
import { Command } from 'commander';
import { logger } from '../utils/logger';

/** Gets plugin commands based on the tools config file, if present. */
export async function getPluginCommands(): Promise<Command[]> {
  const config = await findToolsConfig();

  // TODO(sam-gc): Clean this up and make it easy to build plugins
  return (config?.cliPlugins || []).map((p) => {
    return new Command(p.keyword)
      .argument('<string>', 'Action to run')
      .action(async (arg: string) => {
        const action = p.actions.find(({ action }) => action === arg);
        if (!action) {
          logger.error(`Unknown ${p.keyword} action ${arg}`);
          return;
        }
        await action.hook();
      });
  });
}
