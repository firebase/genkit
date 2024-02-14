import * as path from 'path';
import * as fs from 'fs';
import { ToolPlugin } from './plugins';

const CONFIG_NAME = 'genkit-tools.conf.js';

interface ToolsConfig {
  cliPlugins: ToolPlugin[];
}

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
