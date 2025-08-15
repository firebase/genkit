/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import { logger } from '@genkit-ai/tools-common/utils';
import axios from 'axios';
import { execSync } from 'child_process';
import * as clc from 'colorette';
import { Command } from 'commander';
import * as fs from 'fs';
import inquirer from 'inquirer';
import * as os from 'os';
import * as path from 'path';
import { readConfig, writeConfig } from '../utils/config';
import { PACKAGE_MANAGERS, PackageManager } from '../utils/global';
import { detectCLIRuntime } from '../utils/runtime-detector';
import { version as currentVersion, name } from '../utils/version';

interface UpdateOptions {
  reinstall?: boolean;
  check?: boolean;
  version?: string;
  quiet?: boolean;
}

/**
 * Interface for update check result
 */
export interface UpdateCheckResult {
  hasUpdate: boolean;
  currentVersion: string;
  latestVersion: string;
}

/**
 * Validates a version string
 */
function validateVersion(version: string): boolean {
  return /^v?\d+\.\d+\.\d+$/.test(version);
}

/**
 * Checks if a new version is available (exported for use in other modules)
 */
export async function checkForUpdates(): Promise<UpdateCheckResult> {
  const latestVersion = await getLatestVersion();
  const hasUpdate = latestVersion !== currentVersion;

  return {
    hasUpdate,
    currentVersion,
    latestVersion,
  };
}

/**
 * Interface for the Google Cloud Storage latest.json response
 */
interface GCSLatestResponse {
  channel: string;
  latestVersion: string;
  lastUpdated: string;
  platforms: {
    [key: string]: {
      url: string;
      version: string;
      versionedUrl: string;
    };
  };
}

/**
 * Interface for npm registry response
 */
interface NpmRegistryResponse {
  'dist-tags': {
    latest: string;
    [key: string]: string;
  };
  versions: {
    [version: string]: any;
  };
}

/**
 * Gets available CLI versions from npm registry for non-binary installations
 */
export async function getAvailableVersionsFromNpm(
  ignoreRC: boolean = true
): Promise<string[]> {
  try {
    const response = await axios.get(`https://registry.npmjs.org/${name}`);
    const data: NpmRegistryResponse = response.data;

    // Get all version numbers and sort them
    const versions = Object.keys(data.versions);

    // Filter out pre-release versions and sort by semantic version (newest first)
    return versions
      .filter((version) => !/-/.test(version) || !ignoreRC) // Remove pre-release versions
      .sort((a, b) => {
        const parseVersion = (v: string) => v.split('.').map(Number);
        const [aMajor, aMinor, aPatch] = parseVersion(a);
        const [bMajor, bMinor, bPatch] = parseVersion(b);
        if (bMajor !== aMajor) return bMajor - aMajor;
        if (bMinor !== aMinor) return bMinor - aMinor;
        return bPatch - aPatch;
      });
  } catch (error) {
    throw new Error(`Failed to fetch npm versions: ${error}`);
  }
}

/**
 * Gets latest CLI version from Google Cloud Storage for binary installations
 */
export async function getLatestVersionFromGCS(): Promise<string[]> {
  try {
    const response = await axios.get(
      'https://storage.googleapis.com/genkit-assets-cli/latest.json'
    );
    const data: GCSLatestResponse = response.data;

    // For now, we only return the latest version from GCS
    // In the future, we could implement a way to get all available versions
    return [data.latestVersion];
  } catch (error) {
    throw new Error(`Failed to fetch GCS versions: ${error}`);
  }
}

/**
 * Gets latest CLI version based on installation type
 */
async function getLatestVersion(): Promise<string> {
  const runtime = detectCLIRuntime();
  let versions: string[] = [];

  if (runtime.isCompiledBinary) {
    versions = await getLatestVersionFromGCS();
  } else {
    versions = await getAvailableVersionsFromNpm();
  }

  try {
    if (versions.length === 0) {
      throw new Error('No versions found');
    }
    // Return the first version (newest) with 'v' prefix for consistency
    return versions[0];
  } catch (error) {
    throw new Error(`Failed to fetch latest version: ${error}`);
  }
}
/**
 * Gets the current platform and architecture for download URL
 */
function getPlatformInfo(): { platform: string; arch: string } {
  const platform = os.platform();
  const arch = os.arch();

  let platformName: string;
  switch (platform) {
    case 'darwin':
      platformName = 'darwin';
      break;
    case 'win32':
      platformName = 'win32';
      break;
    case 'linux':
      platformName = 'linux';
      break;
    default:
      throw new Error(`Unsupported platform: ${platform}`);
  }

  let archName: string;
  switch (arch) {
    case 'x64':
      archName = 'x64';
      break;
    case 'arm64':
      archName = 'arm64';
      break;
    default:
      throw new Error(`Unsupported architecture: ${arch}`);
  }

  return { platform: platformName, arch: archName };
}

/**
 * Prompts the user to select a package manager for updating Genkit CLI.
 * Returns the selected PackageManager object.
 */
async function inquirePackageManager(): Promise<PackageManager> {
  const choices = Object.keys(PACKAGE_MANAGERS).map((key) => ({
    name: PACKAGE_MANAGERS[key].type,
    value: key,
  }));

  const { selected } = await inquirer.prompt([
    {
      type: 'list',
      name: 'selected',
      message: 'Which package manager do you want to use to update Genkit CLI?',
      choices,
      default: PACKAGE_MANAGERS.npm.type,
    },
  ]);

  return PACKAGE_MANAGERS[selected];
}

/**
 * Checks if the CLI is running from a global package manager install
 */
async function inquireRunningFromGlobalInstall(): Promise<boolean> {
  const { selected } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'selected',
      message: 'Are you running Genkit CLI from a global install?',
      default: true,
    },
  ]);

  return selected;
}

/**
 * Downloads and installs the latest binary
 */
async function downloadAndInstall(version: string): Promise<void> {
  const { platform, arch } = getPlatformInfo();
  const execPath = process.execPath;
  const backupPath = `${execPath}.backup`;
  const runtime = detectCLIRuntime();

  // If not running from a binary, we should install using package manager
  if (!runtime.isCompiledBinary) {
    // Check if the requested version is available on npm
    const availableVersions = await getAvailableVersionsFromNpm();
    if (!availableVersions.includes(version.replace(/^v/, ''))) {
      logger.error(`Version v${clc.bold(version)} is not available on npm.`);
      process.exit(1);
    }

    const pm = await inquirePackageManager();
    let command = '';

    if (await inquireRunningFromGlobalInstall()) {
      command = `${pm?.globalInstallCommand} ${name}@${version}`;
    } else {
      command = `${pm?.localInstallCommand} ${name}@${version}`;
    }

    logger.info(`Running using ${pm?.type}, downloading using ${pm?.type}...`);
    execSync(command, { stdio: 'inherit' });
    logger.info(
      `${clc.green('✓')} Successfully updated to v${clc.bold(version)}`
    );
    return;
  }

  // Create backup of current binary
  logger.info('Creating backup of current binary...');
  fs.copyFileSync(execPath, backupPath);

  try {
    // Construct machine identifier and download URL
    const machine = `${platform}-${arch}`;
    const fileName = 'genkit'; // All platforms use 'genkit' in the URL path
    const cleanVersion = version.startsWith('v')
      ? version.substring(1)
      : version;

    // Use the same URL structure as the install_cli script
    const channel = 'prod'; // Default to prod channel
    const downloadUrl = `https://storage.googleapis.com/genkit-assets-cli/${channel}/${machine}/v${cleanVersion}/${fileName}`;

    logger.info(`Downloading v${clc.bold(version)} for ${machine}...`);

    const response = await axios({
      method: 'GET',
      url: downloadUrl,
      responseType: 'stream',
    });

    // Save directly to a temporary file (no zip extraction needed)
    const tempDir = os.tmpdir();
    const tempBinaryPath = path.join(
      tempDir,
      `genkit-update-${Date.now()}${platform === 'win32' ? '.exe' : ''}`
    );

    const writer = fs.createWriteStream(tempBinaryPath);
    response.data.pipe(writer);

    await new Promise<void>((resolve, reject) => {
      writer.on('finish', () => resolve());
      writer.on('error', reject);
    });

    logger.info('Installing new binary...');

    // Replace current binary
    fs.copyFileSync(tempBinaryPath, execPath);

    // Make sure it's executable (Unix systems)
    if (platform !== 'win32') {
      fs.chmodSync(execPath, '755');
    }

    // Clean up temporary file
    fs.unlinkSync(tempBinaryPath);
    fs.unlinkSync(backupPath);

    logger.info(
      `${clc.green('✓')} Successfully updated to v${clc.bold(version)}`
    );
  } catch (error) {
    // Restore backup if update failed
    if (fs.existsSync(backupPath)) {
      logger.warn('Update failed, restoring backup...');
      fs.copyFileSync(backupPath, execPath);
      fs.unlinkSync(backupPath);
    }
    throw error;
  }
}

/**
 * Shows an update notification if a new version is available.
 * This function is designed to be called from the CLI entry point.
 * It can be disabled by the user's configuration or environment variable.
 */
export async function showUpdateNotification(): Promise<void> {
  try {
    // Check if notifications are disabled via environment variable or config
    if (process.env.GENKIT_QUIET === 'true') {
      return;
    }

    const config = readConfig();
    if (config.notificationsDisabled) {
      return;
    }

    // Check for updates
    const result = await checkForUpdates();

    if (result.hasUpdate) {
      // Merge all notification lines into a single message for concise output
      console.log(
        `\n${clc.yellow('📦 Update available:')} ${clc.bold(result.currentVersion)} → ${clc.bold(clc.green(result.latestVersion))}\n` +
          `${clc.dim('Run')} ${clc.bold('genkit update')} ${clc.dim('to upgrade')}\n` +
          `${clc.dim('Run')} ${clc.bold('genkit update --quiet')} ${clc.dim('to disable these notifications')}\n`
      );
    }
  } catch {
    // Silently fail - update notifications shouldn't break the CLI
    // We don't want to show errors for network issues, etc.
  }
}

export const update = new Command('update')
  .description('update the genkit CLI to the latest version')
  .option('-r, --reinstall', 'reinstall current version')
  .option('-c, --check', 'check for updates without installing')
  .option('-v, --version <version>', 'install a specific version', (value) => {
    if (!validateVersion(value)) {
      logger.error(`Invalid version format: ${value}`);
      process.exit(1);
    }
    return value;
  })
  .option('--quiet', 'toggle update notifications on/off')
  .action(async (options: UpdateOptions) => {
    // Handle --quiet flag
    if (options.quiet) {
      const config = readConfig();
      const wasDisabled = config.notificationsDisabled;

      // Toggle the notification setting
      config.notificationsDisabled = !wasDisabled;
      writeConfig(config);

      if (config.notificationsDisabled) {
        logger.info(
          `${clc.green('✓')} Update notifications have been ${clc.bold('disabled')}`
        );
        logger.info(
          `${clc.dim('Run')} ${clc.bold('genkit update --quiet')} ${clc.dim('again to re-enable them')}`
        );
      } else {
        logger.info(
          `${clc.green('✓')} Update notifications have been ${clc.bold('enabled')}`
        );
        logger.info(
          `${clc.dim('Run')} ${clc.bold('genkit update --quiet')} ${clc.dim('to disable them')}`
        );
      }
      return;
    }

    // Handle --check flag
    if (options.check) {
      try {
        const result = await checkForUpdates();
        if (result.hasUpdate) {
          logger.info(
            `Update available: v${clc.bold(result.currentVersion)} → v${clc.bold(result.latestVersion)}`
          );
        } else {
          logger.info(
            `${clc.green('✓')} You're using the latest version: v${clc.bold(result.currentVersion)}`
          );
        }
        return;
      } catch (error: any) {
        logger.error(
          `${clc.red('Failed to check for updates:')} ${error.message}`
        );
        process.exit(1);
      }
    }

    try {
      let version = options.version;

      if (options.reinstall) {
        version = currentVersion;

        logger.info(`${clc.yellow('!')} Reinstalling v${clc.bold(version)}...`);
      } else if (version) {
        if (version === currentVersion) {
          logger.info(
            `${clc.green('✓')} Already using version v${clc.bold(version)}.`
          );
          return;
        }

        logger.info(`Installing v${clc.bold(version)}...`);
      } else {
        logger.info('Checking for updates...');
        if ((await checkForUpdates()).hasUpdate) {
          version = await getLatestVersion();

          logger.info(
            `Update available: v${clc.bold(currentVersion)} → v${clc.bold(version)}`
          );
        } else {
          logger.info(
            `${clc.green('✓')} Already on the latest version: v${clc.bold(currentVersion)}`
          );
          return;
        }
      }

      await downloadAndInstall(version);
    } catch (error: any) {
      logger.error(`${clc.red('Update failed:')} ${error.message}`);
      process.exit(1);
    }
  });
