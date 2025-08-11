import path from "path";
import * as fs from 'fs';
import * as os from 'os';

/**
 * Gets the path to the genkit config file
 */
export function getConfigFilePath(): string {
  return path.join(os.homedir(), '.genkit-config.json');
}

/**
 * Reads the genkit configuration
 */
export function readConfig(): { notificationsDisabled?: boolean } {
  try {
    const configPath = getConfigFilePath();
    if (fs.existsSync(configPath)) {
      const configData = fs.readFileSync(configPath, 'utf8');
      return JSON.parse(configData);
    }
  } catch {
    // If we can't read the config, return empty object
  }
  return {};
}

/**
 * Writes the genkit configuration
 */
export function writeConfig(config: { notificationsDisabled?: boolean }): void {
  try {
    const configPath = getConfigFilePath();
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  } catch {
    // If we can't write the config, it's not critical
  }
}
