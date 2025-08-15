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

import { beforeEach, describe, expect, it, jest } from '@jest/globals';

// Mock all external dependencies before any imports
jest.mock('@genkit-ai/tools-common/utils', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  },
}));

jest.mock('axios', () => ({
  get: jest.fn(),
  default: jest.fn(),
}));

jest.mock('child_process', () => ({
  execSync: jest.fn(),
}));

jest.mock('colorette', () => ({
  yellow: jest.fn((text) => String(text)),
  green: jest.fn((text) => String(text)),
  red: jest.fn((text) => String(text)),
  bold: jest.fn((text) => String(text)),
  dim: jest.fn((text) => String(text)),
}));

jest.mock('fs', () => ({
  copyFileSync: jest.fn(),
  chmodSync: jest.fn(),
  unlinkSync: jest.fn(),
  existsSync: jest.fn(),
  createWriteStream: jest.fn(),
}));

jest.mock('inquirer', () => ({
  prompt: jest.fn(),
  default: {
    prompt: jest.fn(),
  },
}));

jest.mock('os', () => ({
  platform: jest.fn(),
  arch: jest.fn(),
  tmpdir: jest.fn(),
}));

jest.mock('path', () => ({
  join: jest.fn(),
}));

jest.mock('../../src/utils/config', () => ({
  readConfig: jest.fn(),
  writeConfig: jest.fn(),
}));

jest.mock('../../src/utils/runtime-detector', () => ({
  detectCLIRuntime: jest.fn(),
}));

jest.mock('../../src/utils/version', () => ({
  version: '1.0.0',
  name: 'genkit-cli',
}));

// Import after mocking
import axios from 'axios';
import {
  checkForUpdates,
  getAvailableVersionsFromNpm,
  getLatestVersionFromGCS,
  showUpdateNotification,
} from '../../src/commands/update';
import { readConfig } from '../../src/utils/config';
import { detectCLIRuntime } from '../../src/utils/runtime-detector';

const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockedReadConfig = readConfig as jest.MockedFunction<typeof readConfig>;
const mockedDetectCLIRuntime = detectCLIRuntime as jest.MockedFunction<
  typeof detectCLIRuntime
>;

describe('update command', () => {
  const mockCLIRuntime = {
    type: 'node' as const,
    execPath: '/usr/bin/node',
    scriptPath: '/usr/lib/node_modules/genkit-cli/dist/bin/genkit.js',
    isCompiledBinary: false,
    platform: 'darwin' as const,
  };

  const mockBinaryRuntime = {
    type: 'compiled-binary' as const,
    execPath: '/usr/local/bin/genkit',
    isCompiledBinary: true,
    platform: 'darwin' as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockedDetectCLIRuntime.mockReturnValue(mockCLIRuntime);
    mockedReadConfig.mockReturnValue({});
  });

  describe('checkForUpdates', () => {
    it('should return update available when versions differ', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: { '1.1.0': {}, '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await checkForUpdates();

      expect(result).toEqual({
        hasUpdate: true,
        currentVersion: '1.0.0',
        latestVersion: '1.1.0',
      });
    });

    it('should return no update when versions are the same', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.0.0' },
          versions: { '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await checkForUpdates();

      expect(result).toEqual({
        hasUpdate: false,
        currentVersion: '1.0.0',
        latestVersion: '1.0.0',
      });
    });

    it('should handle binary runtime and fetch from GCS', async () => {
      mockedDetectCLIRuntime.mockReturnValue(mockBinaryRuntime);
      const mockGCSResponse = {
        data: {
          channel: 'prod',
          latestVersion: '1.1.0',
          lastUpdated: '2024-01-01',
          platforms: {},
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockGCSResponse);

      const result = await checkForUpdates();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://storage.googleapis.com/genkit-assets-cli/latest.json'
      );
      expect(result.latestVersion).toBe('1.1.0');
    });

    it('should handle errors when fetching npm versions', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));

      await expect(getAvailableVersionsFromNpm()).rejects.toThrow(
        'Failed to fetch npm versions'
      );
    });

    it('should handle errors when fetching GCS versions', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));

      await expect(getLatestVersionFromGCS()).rejects.toThrow(
        'Failed to fetch GCS versions'
      );
    });
  });

  describe('showUpdateNotification', () => {
    it('should not show notification when notifications are disabled in config', async () => {
      mockedReadConfig.mockReturnValue({ notificationsDisabled: true });
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await showUpdateNotification();

      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should show notification when update is available', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: { '1.1.0': {}, '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await showUpdateNotification();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Update available')
      );
    });

    it('should silently fail on network errors', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await expect(showUpdateNotification()).resolves.toBeUndefined();
      expect(consoleSpy).not.toHaveBeenCalled();
    });
  });
});
