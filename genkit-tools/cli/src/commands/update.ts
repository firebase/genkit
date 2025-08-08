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
import * as clc from 'colorette';
import { Command } from 'commander';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

interface UpdateOptions {
  force?: boolean;
  check?: boolean;
  list?: boolean;
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
 * Checks if a new version is available (exported for use in other modules)
 */
export async function checkForUpdates(): Promise<UpdateCheckResult> {
  const currentVersion = require('../../package.json').version;
  const latestVersion = await getLatestVersion();

  // Remove 'v' prefix if present for comparison
  const cleanLatestVersion = latestVersion.startsWith('v')
    ? latestVersion.substring(1)
    : latestVersion;

  const hasUpdate = cleanLatestVersion !== currentVersion;

  return {
    hasUpdate,
    currentVersion,
    latestVersion: cleanLatestVersion
  };
}

/**
 * Gets available CLI versions from GitHub tags
 */
async function getAvailableVersions(): Promise<string[]> {
  try {
    const response = await axios.get(
      'https://api.github.com/repos/firebase/genkit/tags?per_page=100'
    );
    const tags: any[] = response.data;
    // Filter tags that contain CLI versions (tools-common-v, telemetry-server-v, or genkit-cli)
    // These tags typically indicate CLI releases
    const cliVersionTags = tags.filter(tag => {
      const tagName = tag.name;
      return tagName.includes('tools-common-v') ||
             tagName.includes('telemetry-server-v') ||
             tagName.includes('genkit-cli');
    });
    // Extract version numbers and deduplicate
    const versions = new Set<string>();
    for (const tag of cliVersionTags) {
      const tagName = tag.name;
      // Extract version from different tag patterns
      if (tagName.includes('tools-common-v')) {
        const version = tagName.replace('tools-common-v', '');
        versions.add(version);
      } else if (tagName.includes('telemetry-server-v')) {
        const version = tagName.replace('telemetry-server-v', '');
        versions.add(version);
      } else if (tagName.includes('genkit-cli')) {
        // Handle genkit-cli specific tags if they exist
        const versionMatch = tagName.match(/(\d+\.\d+\.\d+)/);
        if (versionMatch) {
          versions.add(versionMatch[1]);
        }
      }
    }
    // Convert to array and sort by semantic version (newest first)
    return Array.from(versions).sort((a, b) => {
      const parseVersion = (v: string) => v.split('.').map(Number);
      const [aMajor, aMinor, aPatch] = parseVersion(a);
      const [bMajor, bMinor, bPatch] = parseVersion(b);
      if (bMajor !== aMajor) return bMajor - aMajor;
      if (bMinor !== aMinor) return bMinor - aMinor;
      return bPatch - aPatch;
    });
  } catch (error) {
    throw new Error(`Failed to fetch available versions: ${error}`);
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
 * Gets the latest version from GitHub releases
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
async function downloadAndInstall(version: string, force: boolean): Promise<void> {
  const { platform, arch } = getPlatformInfo();
  const execPath = process.execPath;
  const backupPath = `${execPath}.backup`;

  // Create backup of current binary
  logger.info('Creating backup of current binary...');
  fs.copyFileSync(execPath, backupPath);

  try {
    // Construct machine identifier and download URL
    const machine = `${platform}-${arch}`;
    const fileName = 'genkit'; // All platforms use 'genkit' in the URL path
    const cleanVersion = version.startsWith('v') ? version.substring(1) : version;

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
    const tempBinaryPath = path.join(tempDir, `genkit-update-${Date.now()}${platform === 'win32' ? '.exe' : ''}`);

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

    logger.info(`${clc.green('✓')} Successfully updated to ${clc.bold(version)}`);
    logger.info('Restart your terminal or run the command again to use the new version.');

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

export const update = new Command('update')
  .description('update the genkit CLI to the latest version (binary installations only)')
  .option('-f, --force', 'force update even if already on latest version')
  .option('-l, --list', 'list available versions')
  .option('-c, --check', 'check for updates without installing')
  .action(async (options: UpdateOptions) => {
    // Handle --list flag
    if (options.list) {
      try {
        logger.info('Fetching available versions...');
        const versions = await getAvailableVersions();
        const currentVersion = require('../../package.json').version;
        if (versions.length === 0) {
          logger.info('No versions found.');
          return;
        }
        logger.info(`\nAvailable genkit CLI versions:`);
        logger.info(`${clc.dim('─'.repeat(40))}`);
        for (const version of versions) {
          const isCurrent = version === currentVersion;
          const prefix = isCurrent ? clc.green('●') : ' ';
          const versionText = isCurrent ? clc.bold(clc.green(version)) : version;
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
          logger.info(`Update available: ${clc.bold(result.currentVersion)} → ${clc.bold(result.latestVersion)}`);
          logger.info(`${clc.green('✓')} New version found!`);
        } else {
          logger.info(`${clc.green('✓')} Already on the latest version: ${clc.bold(result.currentVersion)}`);
        }
        return;
      } catch (error: any) {
        logger.error(`${clc.red('Failed to check for updates:')} ${error.message}`);
        process.exit(1);
      }
    }

    try {
      logger.info('Checking for updates...');
      const latestVersion = await getLatestVersion();
      const currentVersion = require('../../package.json').version;

      if (options.force) {
        logger.info(`${clc.yellow('!')} Force updating to ${clc.bold(latestVersion)}...`);
      } else if (latestVersion !== `v${currentVersion}`) {
        logger.info(`Update available: ${clc.bold(currentVersion)} → ${clc.bold(latestVersion)}`);
      } else {
        logger.info(`${clc.green('✓')} Already on the latest version: ${clc.bold(currentVersion)}`);
        return;
      }

      await downloadAndInstall(latestVersion, options.force || false);
    } catch (error: any) {
      logger.error(`${clc.red('Update failed:')} ${error.message}`);
      process.exit(1);
    }
  });
