import { findToolsConfig } from '@google-genkit-tools/common/config';
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
        const action = p.actions.find((a) => a.name === arg);
        if (!action) {
          logger.error(`Unknown ${p.keyword} action ${arg}`);
          return;
        }
        await action.hook();
      });
  });
}
