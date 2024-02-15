import * as fs from 'fs';
import * as path from 'path';
import * as process from 'process';
import { ToolPlugin } from './plugins';

const CONFIG_NAME = 'genkit-tools.conf.js';

interface ToolsConfig {
  cliPlugins: ToolPlugin[];
}

/**
 * Searches recursively up the directory structure for the Genkit tools config
 * file.
 */
export async function findToolsConfig(): Promise<ToolsConfig | null> {
  let current = process.cwd();
  while (path.resolve(current, '..') !== current) {
    if (fs.existsSync(path.resolve(current, CONFIG_NAME))) {
      const configPath = path.resolve(current, CONFIG_NAME);
      const config = (await import(configPath)) as { default: ToolsConfig };
      return config.default;
    }
    current = path.resolve(current, '..');
  }

  return null;
}
