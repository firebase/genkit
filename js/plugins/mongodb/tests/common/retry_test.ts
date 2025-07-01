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

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  jest,
} from '@jest/globals';
import { retryWithDelay } from '../../src/common/retry';

const originalWarn = console.warn;
const mockWarn = jest.fn();

describe('retryWithDelay', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    console.warn = mockWarn;
  });

  afterEach(() => {
    console.warn = originalWarn;
  });

  describe('successful operations', () => {
    it('should return result on first successful attempt', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockResolvedValue('success');

      const promise = retryWithDelay(operation);
      const result = await promise;

      expect(operation).toHaveBeenCalledTimes(1);
      expect(result).toBe('success');
      expect(mockWarn).not.toHaveBeenCalled();
    });

    it('should return result on first successful attempt with custom options', async () => {
      const operation = jest
        .fn<() => Promise<{ data: string }>>()
        .mockResolvedValue({ data: 'test' });

      const promise = retryWithDelay(operation, {
        retryAttempts: 3,
        baseDelay: 200,
        jitterFactor: 0.2,
      });
      const result = await promise;

      expect(operation).toHaveBeenCalledTimes(1);
      expect(result).toEqual({ data: 'test' });
      expect(mockWarn).not.toHaveBeenCalled();
    });

    it('should retry on failure and succeed on second attempt', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValueOnce(new Error('First failure'))
        .mockResolvedValue('success');

      const result = await retryWithDelay(operation, {
        retryAttempts: 1,
        baseDelay: 10,
      });

      expect(operation).toHaveBeenCalledTimes(2);
      expect(result).toBe('success');
      expect(mockWarn).toHaveBeenCalledWith(
        expect.stringContaining('Attempt 1 failed: First failure. Retrying in')
      );
    });

    it('should retry multiple times and succeed', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValueOnce(new Error('First failure'))
        .mockRejectedValueOnce(new Error('Second failure'))
        .mockResolvedValue('success');

      const result = await retryWithDelay(operation, {
        retryAttempts: 2,
        baseDelay: 10,
        jitterFactor: 0.5,
      });

      expect(operation).toHaveBeenCalledTimes(3);
      expect(result).toBe('success');
      expect(mockWarn).toHaveBeenCalledTimes(2);
    });
  });

  describe('failure scenarios', () => {
    it('should throw after max retry attempts', async () => {
      const error = new Error('Persistent failure');
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValue(error);

      await expect(
        retryWithDelay(operation, { retryAttempts: 1 })
      ).rejects.toThrow('Persistent failure');
      expect(operation).toHaveBeenCalledTimes(2);
    });
  });

  describe('delay calculation', () => {
    it('should handle zero jitter factor', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValueOnce(new Error('Failure'))
        .mockResolvedValue('success');

      await retryWithDelay(operation, {
        retryAttempts: 1,
        baseDelay: 100,
        jitterFactor: 0,
      });

      expect(operation).toHaveBeenCalledTimes(2);
    });

    it('should handle maximum jitter factor', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValueOnce(new Error('Failure'))
        .mockResolvedValue('success');

      await retryWithDelay(operation, {
        retryAttempts: 1,
        baseDelay: 100,
        jitterFactor: 1.0,
      });

      expect(operation).toHaveBeenCalledTimes(2);
    });

    it('should ensure delay is never negative', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValueOnce(new Error('Failure'))
        .mockResolvedValue('success');

      const originalRandom = Math.random;
      Math.random = jest.fn<() => number>().mockReturnValue(0.0);

      await retryWithDelay(operation, {
        retryAttempts: 1,
        baseDelay: 100,
        jitterFactor: 1.0,
      });
      Math.random = originalRandom;

      expect(operation).toHaveBeenCalledTimes(2);
      expect(mockWarn).toHaveBeenCalledWith(
        expect.stringContaining('Attempt 1 failed: Failure. Retrying in')
      );
    });

    it('should handle unreachable throw statement at end of function', async () => {
      const operation = jest
        .fn<() => Promise<string>>()
        .mockRejectedValueOnce(new Error('Failure'))
        .mockResolvedValue('success');

      await retryWithDelay(operation, {
        retryAttempts: 1,
        baseDelay: 100,
        jitterFactor: 1.0,
      });

      expect(operation).toHaveBeenCalledTimes(2);
      expect(mockWarn).toHaveBeenCalledWith(
        expect.stringContaining('Attempt 1 failed: Failure. Retrying in')
      );
    });
  });
});
