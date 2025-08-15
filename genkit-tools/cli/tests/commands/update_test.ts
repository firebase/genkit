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
    // Clean up environment variables
    delete process.env.GENKIT_QUIET;
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

    it('should handle major version differences correctly', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '2.0.0' },
          versions: { '2.0.0': {}, '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await checkForUpdates();

      expect(result).toEqual({
        hasUpdate: true,
        currentVersion: '1.0.0',
        latestVersion: '2.0.0',
      });
    });
  });

  describe('getAvailableVersionsFromNpm', () => {
    it('should filter out pre-release versions by default', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: {
            '1.0.0': {},
            '1.1.0': {},
            '1.1.0-alpha.1': {},
            '1.1.0-beta.2': {},
            '1.2.0-rc.1': {},
          },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await getAvailableVersionsFromNpm();

      expect(result).toEqual(['1.1.0', '1.0.0']);
      expect(result).not.toContain('1.1.0-alpha.1');
      expect(result).not.toContain('1.1.0-beta.2');
      expect(result).not.toContain('1.2.0-rc.1');
    });

    it('should include pre-release versions when ignoreRC is false', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: {
            '1.0.0': {},
            '1.1.0': {},
            '1.1.0-alpha.1': {},
            '1.2.0-rc.1': {},
          },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await getAvailableVersionsFromNpm(false);

      expect(result).toContain('1.1.0-alpha.1');
      expect(result).toContain('1.2.0-rc.1');
    });

    it('should handle empty versions object', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.0.0' },
          versions: {},
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await getAvailableVersionsFromNpm();

      expect(result).toEqual([]);
    });

    it('should handle malformed npm response', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.0.0' },
          // Missing versions property
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      await expect(getAvailableVersionsFromNpm()).rejects.toThrow(
        'Failed to fetch npm versions'
      );
    });
  });

  describe('getLatestVersionFromGCS', () => {
    it('should return latest version from GCS', async () => {
      const mockGCSResponse = {
        data: {
          channel: 'prod',
          latestVersion: '1.5.0',
          lastUpdated: '2024-01-01T00:00:00Z',
          platforms: {
            'darwin-x64': {
              url: 'https://example.com/genkit',
              version: '1.5.0',
              versionedUrl: 'https://example.com/v1.5.0/genkit',
            },
          },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockGCSResponse);

      const result = await getLatestVersionFromGCS();

      expect(result).toEqual(['1.5.0']);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://storage.googleapis.com/genkit-assets-cli/latest.json'
      );
    });

    it('should handle malformed GCS response', async () => {
      const mockGCSResponse = {
        data: {
          // Missing latestVersion property
          channel: 'prod',
          lastUpdated: '2024-01-01T00:00:00Z',
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockGCSResponse);

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

    it('should not show notification when no update is available', async () => {
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.0.0' },
          versions: { '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await showUpdateNotification();

      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should silently fail on network errors', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await expect(showUpdateNotification()).resolves.toBeUndefined();
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should handle config read errors gracefully', async () => {
      mockedReadConfig.mockImplementation(() => {
        throw new Error('Config read error');
      });
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await expect(showUpdateNotification()).resolves.toBeUndefined();
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should show notification for binary runtime updates', async () => {
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
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      await showUpdateNotification();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Update available')
      );
    });
  });

  describe('error handling and edge cases', () => {
    it('should handle axios timeout errors', async () => {
      const timeoutError = new Error('timeout of 5000ms exceeded');
      timeoutError.name = 'AxiosError';
      mockedAxios.get.mockRejectedValueOnce(timeoutError);

      await expect(getAvailableVersionsFromNpm()).rejects.toThrow(
        'Failed to fetch npm versions'
      );
    });

    it('should handle 404 errors from npm registry', async () => {
      const notFoundError = new Error('Request failed with status code 404');
      mockedAxios.get.mockRejectedValueOnce(notFoundError);

      await expect(getAvailableVersionsFromNpm()).rejects.toThrow(
        'Failed to fetch npm versions'
      );
    });

    it('should handle 404 errors from GCS', async () => {
      const notFoundError = new Error('Request failed with status code 404');
      mockedAxios.get.mockRejectedValueOnce(notFoundError);

      await expect(getLatestVersionFromGCS()).rejects.toThrow(
        'Failed to fetch GCS versions'
      );
    });

    it('should handle malformed JSON responses', async () => {
      const malformedResponse = {
        data: 'not a valid json object',
      };
      mockedAxios.get.mockResolvedValueOnce(malformedResponse);

      await expect(getAvailableVersionsFromNpm()).rejects.toThrow(
        'Failed to fetch npm versions'
      );
    });

    it('should handle empty response data', async () => {
      const emptyResponse = {
        data: null,
      };
      mockedAxios.get.mockResolvedValueOnce(emptyResponse);

      await expect(getAvailableVersionsFromNpm()).rejects.toThrow(
        'Failed to fetch npm versions'
      );
    });
  });

  describe('version comparison edge cases', () => {
    it('should handle version comparison with different formats', async () => {
      // Test when current version has 'v' prefix but latest doesn't
      jest.doMock('../../src/utils/version', () => ({
        version: 'v1.0.0',
        name: 'genkit-cli',
      }));

      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: { '1.1.0': {}, '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await checkForUpdates();

      expect(result.hasUpdate).toBe(true);
    });

    it('should handle identical versions with different prefixes', async () => {
      jest.doMock('../../src/utils/version', () => ({
        version: 'v1.0.0',
        name: 'genkit-cli',
      }));

      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: 'v1.0.0' },
          versions: { '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      const result = await checkForUpdates();

      expect(result.hasUpdate).toBe(false);
    });
  });

  describe('runtime detection integration', () => {
    it('should use npm registry for node runtime', async () => {
      mockedDetectCLIRuntime.mockReturnValue(mockCLIRuntime);
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: { '1.1.0': {}, '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      await checkForUpdates();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://registry.npmjs.org/genkit-cli'
      );
    });

    it('should use GCS for compiled binary runtime', async () => {
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

      await checkForUpdates();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://storage.googleapis.com/genkit-assets-cli/latest.json'
      );
    });

    it('should handle bun runtime like node runtime', async () => {
      const mockBunRuntime = {
        type: 'bun' as const,
        execPath: '/usr/bin/bun',
        scriptPath: '/usr/lib/node_modules/genkit-cli/dist/bin/genkit.js',
        isCompiledBinary: false,
        platform: 'darwin' as const,
      };
      mockedDetectCLIRuntime.mockReturnValue(mockBunRuntime);
      const mockNpmResponse = {
        data: {
          'dist-tags': { latest: '1.1.0' },
          versions: { '1.1.0': {}, '1.0.0': {} },
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockNpmResponse);

      await checkForUpdates();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://registry.npmjs.org/genkit-cli'
      );
    });
  });
});
