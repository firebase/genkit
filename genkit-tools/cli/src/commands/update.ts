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
import * as os from 'os';
import * as path from 'path';
import { readConfig, writeConfig } from '../utils/config';
import { detectCLIRuntime } from '../utils/runtime-detector';
import { runningFromNpmLocally } from '../utils/utils';
import { name, version as currentVersion } from '../utils/version';

interface UpdateOptions {
  force?: boolean;
  check?: boolean;
  list?: boolean;
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

  // Remove 'v' prefix if present for comparison
  const cleanLatestVersion = latestVersion.startsWith('v')
    ? latestVersion.substring(1)
    : latestVersion;

  const hasUpdate = cleanLatestVersion !== currentVersion;

  return {
    hasUpdate,
    currentVersion,
    latestVersion: cleanLatestVersion,
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
async function getAvailableVersionsFromNpm(): Promise<string[]> {
  try {
    const response = await axios.get(`https://registry.npmjs.org/${name}`);
    const data: NpmRegistryResponse = response.data;

    // Get all version numbers and sort them
    const versions = Object.keys(data.versions);

    // Filter out pre-release versions and sort by semantic version (newest first)
    return versions
      .filter((version) => !/-/.test(version)) // Remove pre-release versions
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
 * Gets available CLI versions from Google Cloud Storage for binary installations
 */
async function getAvailableVersionsFromGCS(): Promise<string[]> {
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
 * Gets available CLI versions based on installation type
 */
async function getAvailableVersions(skipRC: boolean = true): Promise<string[]> {
  const runtime = detectCLIRuntime();
  if (runtime.isCompiledBinary) {
    return await getAvailableVersionsFromGCS();
  } else {
    return await getAvailableVersionsFromNpm();
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
 * Gets the latest version based on installation type
 */
async function getLatestVersion(): Promise<string> {
  try {
    const versions = await getAvailableVersions();
    if (versions.length === 0) {
      throw new Error('No versions found');
    }
    // Return the first version (newest) with 'v' prefix for consistency
    return `v${versions[0]}`;
  } catch (error) {
    throw new Error(`Failed to fetch latest version: ${error}`);
  }
}

/**
 * Downloads and installs the latest binary
 */
async function downloadAndInstall(
  version: string,
  force: boolean
): Promise<void> {
  const { platform, arch } = getPlatformInfo();
  const execPath = process.execPath;
  const backupPath = `${execPath}.backup`;
  const runtime = detectCLIRuntime();

  // If not running from a binary, we should install using npm
  if (!runtime.isCompiledBinary) {
    let command = '';

    if (await runningFromNpmLocally()) {
      command = `npm install ${name}@${version}`;
    } else {
      command = `npm install -g ${name}@${version}`;
    }

    logger.info('Running using npm, downloading using npm...');
    execSync(command);
    logger.info(
      `${clc.green('✓')} Successfully updated to ${clc.bold(version)}`
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

    logger.info(`Downloading ${clc.bold(version)} for ${machine}...`);

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
      `${clc.green('✓')} Successfully updated to ${clc.bold(version)}`
    );
    logger.info(
      'Restart your terminal or run the command again to use the new version.'
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
      const runtime = detectCLIRuntime();
      const isBinary = runtime.isCompiledBinary;

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
  .option('-f, --force', 'force update even if already on latest version')
  .option('-l, --list', 'list available versions')
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

    // Handle --list flag
    if (options.list) {
      try {
        logger.info('Fetching available versions...');
        const versions = await getAvailableVersions();
        if (versions.length === 0) {
          logger.info('No versions found.');
          return;
        }
        logger.info(`\nAvailable genkit CLI versions:`);
        logger.info(`${clc.dim('─'.repeat(40))}`);
        for (const version of versions) {
          const isCurrent = version === currentVersion;
          const prefix = isCurrent ? clc.green('●') : ' ';
          const versionText = isCurrent
            ? clc.bold(clc.green(version))
            : version;
          const suffix = isCurrent ? clc.dim(' (current)') : '';
          logger.info(`${prefix} ${versionText}${suffix}`);
        }
        logger.info(`${clc.dim('─'.repeat(40))}`);
        logger.info(`Found ${clc.bold(versions.length.toString())} versions`);
        return;
      } catch (error: any) {
        logger.error(`${clc.red('Failed to list versions:')} ${error.message}`);
        process.exit(1);
      }
    }

    // Handle --check flag
    if (options.check) {
      try {
        const result = await checkForUpdates();
        if (result.hasUpdate) {
          logger.info(
            `Update available: ${clc.bold(result.currentVersion)} → ${clc.bold(result.latestVersion)}`
          );
          logger.info(`${clc.green('✓')} New version found!`);
        } else {
          logger.info(
            `${clc.green('✓')} You're using the latest version: ${clc.bold(result.currentVersion)}`
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
      logger.info('Checking for updates...');

      let version = options.version || (await getLatestVersion());
      const currentVersion = version;

      if (options.force) {
        logger.info(
          `${clc.yellow('!')} Force updating to ${clc.bold(version)}...`
        );
      } else if ((await checkForUpdates()).hasUpdate) {
        logger.info(
          `Update available: ${clc.bold(currentVersion)} → ${clc.bold(version)}`
        );
      } else {
        logger.info(
          `${clc.green('✓')} Already on the latest version: ${clc.bold(currentVersion)}`
        );
        return;
      }

      await downloadAndInstall(version, options.force || false);
    } catch (error: any) {
      logger.error(`${clc.red('Update failed:')} ${error.message}`);
      process.exit(1);
    }
  });
