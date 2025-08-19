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
import { getUserSettings, logger } from '@genkit-ai/tools-common/utils';
import axios from 'axios';
import { execSync } from 'child_process';
import * as clc from 'colorette';
import { Command } from 'commander';
import * as fs from 'fs';
import inquirer from 'inquirer';
import * as os from 'os';
import * as path from 'path';
import {
  PACKAGE_MANAGERS,
  PackageManager,
  getPackageManager,
} from '../utils/package-manager';
import { detectCLIRuntime } from '../utils/runtime-detector';
import { UpdateError } from '../utils/utils';
import { version as currentVersion, name } from '../utils/version';
import { UPDATE_NOTIFICATIONS_OPT_OUT_CONFIG_TAG } from './config';

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

export function getCurrentVersion(): string {
  return correctVersion(currentVersion);
}

/**
 * Validates a version string
 */
function validateVersion(version: string): boolean {
  return /^v?\d+\.\d+\.\d+$/.test(version);
}

/**
 * Corrects the version string to remove the 'v' prefix if it exists
 * @param version - The version string to correct
 * @returns The corrected version string
 */
function correctVersion(version: string): string {
  return version.startsWith('v') ? version.substring(1) : version;
}

/**
 * Checks if a new version is available (exported for use in other modules)
 */
export async function checkForUpdates(): Promise<UpdateCheckResult> {
  const latestVersion = correctVersion(await getLatestVersion());
  const hasUpdate = latestVersion !== getCurrentVersion();

  return {
    hasUpdate,
    currentVersion: getCurrentVersion(),
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

async function getGCSLatestData(): Promise<GCSLatestResponse> {
  const response = await axios.get(
    'https://storage.googleapis.com/genkit-assets-cli/latest.json'
  );

  if (response.status !== 200) {
    throw new UpdateError(
      `Failed to fetch GCS latest.json: ${response.statusText}`
    );
  }

  return response.data as GCSLatestResponse;
}

/**
 * Gets available CLI versions from npm registry for non-binary installations
 */
export async function getAvailableVersionsFromNpm(
  ignoreRC: boolean = true
): Promise<string[]> {
  try {
    const response = await axios.get(`https://registry.npmjs.org/${name}`);

    if (response.status !== 200) {
      throw new UpdateError(
        `Failed to fetch npm versions: ${response.statusText}`
      );
    }

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
  } catch (error: any) {
    if (error instanceof UpdateError) {
      throw error;
    }

    throw new UpdateError(`Failed to fetch npm versions: ${error.message}`);
  }
}

/**
 * Gets latest CLI version from Google Cloud Storage for binary installations
 */
export async function getLatestVersionFromGCS(): Promise<string[]> {
  try {
    const data = await getGCSLatestData();

    if (!data.latestVersion) {
      throw new UpdateError('No latest version found');
    }

    // For now, we only return the latest version from GCS
    // In the future, we could implement a way to get all available versions
    return [data.latestVersion];
  } catch (error: any) {
    if (error instanceof UpdateError) {
      throw error;
    }

    throw new UpdateError(`Failed to fetch GCS versions: ${error.message}`);
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
      throw new UpdateError('No versions found');
    }
    // Return the first version (newest) with 'v' prefix for consistency
    return versions[0];
  } catch (error: any) {
    if (error instanceof UpdateError) {
      throw error;
    }

    throw new UpdateError(`Failed to fetch latest version: ${error.message}`);
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
      throw new UpdateError(`Unsupported platform: ${platform}`);
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
      throw new UpdateError(`Unsupported architecture: ${arch}`);
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
      message: 'Which package manager did you use to install Genkit CLI?',
      choices,
      default: PACKAGE_MANAGERS.npm.type,
    },
  ]);

  return getPackageManager(selected);
}

/**
 * Checks if the CLI is running from a global package manager install
 */
async function inquireRunningFromGlobalInstall(): Promise<boolean> {
  const { selected } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'selected',
      message: 'Is your Genkit CLI installed globally?',
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
    if (!availableVersions.includes(correctVersion(version))) {
      logger.error(`Version v${clc.bold(version)} is not available on npm.`);
      process.exit(1);
    }

    const pm = await inquirePackageManager();
    const isGlobal = await inquireRunningFromGlobalInstall();
    let command: string;

    if (isGlobal) {
      command = `${pm?.globalInstallCommandFunc(name, version)}`;
    } else {
      command = `${pm?.localInstallCommandFunc(name, version)}`;
    }

    logger.info(`Downloading using ${pm?.type}...`);
    try {
      execSync(command, { stdio: 'inherit' });
      logger.info(
        `${clc.green('✓')} Successfully updated to v${clc.bold(version)}`
      );
    } catch (error: any) {
      logger.info(``);
      logger.error(
        `${clc.red('✗')} Failed to update to v${clc.bold(version)}.` +
          `\n\nAlternatively, you can try to update by running:\n` +
          `${clc.bold(isGlobal ? pm?.globalInstallCommandFunc(name, version) : pm?.localInstallCommandFunc(name, version))}`
      );
      process.exit(1);
    }
    return;
  }

  // Construct machine identifier and download URL
  const gcsLatestData = await getGCSLatestData();
  const machine = `${platform}-${arch}`;
  const fileName = gcsLatestData.platforms[machine].versionedUrl
    .split('/')
    .pop();
  const cleanVersion = version.startsWith('v') ? version.substring(1) : version;
  // Use the same URL structure as the install_cli script
  const channel = 'prod'; // Default to prod channel
  const downloadUrl = `https://storage.googleapis.com/genkit-assets-cli/${channel}/${machine}/v${cleanVersion}/${fileName}`;
  try {
    let response;
    try {
      response = await axios({
        method: 'GET',
        url: downloadUrl,
        responseType: 'stream',
        validateStatus: (status) => status >= 200 && status < 300, // Only resolve for 2xx
      });
    } catch (err: any) {
      if (err.response && err.response.status === 404) {
        logger.error(`Version v${clc.bold(version)} can not be found.`);
        process.exit(1);
      }
      throw new UpdateError(`Failed to download binary: ${err.message}`);
    }

    // Create backup of current binary
    logger.info('Creating backup of current binary...');
    fs.copyFileSync(execPath, backupPath);

    logger.info(`Downloading v${clc.bold(version)} for ${machine}...`);

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
    try {
      if (fs.existsSync(backupPath)) {
        logger.warn('Update failed, restoring backup...');
        fs.copyFileSync(backupPath, execPath);
        fs.unlinkSync(backupPath);
      }
    } catch (error) {
      logger.error(`Failed to restore backup: ${error}`);
    }

    const alternativeCommand = `curl -Lo ./genkit_bin ${downloadUrl}`;
    logger.info(``);
    logger.error(
      `${clc.red('✗')} Failed to update to v${clc.bold(version)}.` +
        `\n\nAlternatively, you can try to update by running:\n` +
        `${clc.bold(alternativeCommand)}`
    );
    process.exit(1);
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
    if (process.env.GENKIT_CLI_DISABLE_UPDATE_NOTIFICATIONS === 'true') {
      return;
    }

    // Check if notifications are disabled via config
    const userSettings = getUserSettings();
    if (userSettings[UPDATE_NOTIFICATIONS_OPT_OUT_CONFIG_TAG]) {
      return;
    }

    // Check for updates
    const result = await checkForUpdates();

    if (result.hasUpdate) {
      // Merge all notification lines into a single message for concise output
      console.log(
        `\n${clc.yellow('📦 Update available:')} ${clc.bold(result.currentVersion)} → ${clc.bold(clc.green(result.latestVersion))}\n` +
          `${clc.dim('Run')} ${clc.bold('genkit update')} ${clc.dim('to upgrade')}\n` +
          `${clc.dim('Run')} ${clc.bold('genkit config set updateNotificationsOptOut true')} ${clc.dim('to disable these notifications')}\n`
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
  .action(async (options: UpdateOptions) => {
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
        version = getCurrentVersion();

        logger.info(`${clc.yellow('!')} Reinstalling v${clc.bold(version)}...`);
      } else if (version) {
        if (version === getCurrentVersion()) {
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
            `Update available: v${clc.bold(getCurrentVersion())} → v${clc.bold(version)}`
          );
        } else {
          logger.info(
            `${clc.green('✓')} Already on the latest version: v${clc.bold(getCurrentVersion())}`
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
