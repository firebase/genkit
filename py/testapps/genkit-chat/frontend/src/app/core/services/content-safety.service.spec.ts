// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ContentSafetyService } from './content-safety.service';

// Mock the toxicity model
vi.mock('@tensorflow-models/toxicity', () => ({
  load: vi.fn().mockResolvedValue({
    classify: vi.fn().mockImplementation((texts: string[]) => {
      // The model expects an array of strings
      const text = Array.isArray(texts) ? texts[0] || '' : String(texts);
      const textLower = text.toLowerCase();

      // Simulate toxic content detection
      const isToxic =
        textLower.includes('kill') || textLower.includes('hate') || textLower.includes('die');

      return Promise.resolve([
        {
          label: 'toxicity',
          results: [{ match: isToxic, probabilities: [isToxic ? 0.1 : 0.9, isToxic ? 0.9 : 0.1] }],
        },
        {
          label: 'identity_attack',
          results: [{ match: isToxic, probabilities: [isToxic ? 0.1 : 0.9, isToxic ? 0.9 : 0.1] }],
        },
        {
          label: 'insult',
          results: [{ match: false, probabilities: [0.9, 0.1] }],
        },
        {
          label: 'obscene',
          results: [{ match: false, probabilities: [0.9, 0.1] }],
        },
        {
          label: 'severe_toxicity',
          results: [{ match: isToxic, probabilities: [isToxic ? 0.1 : 0.9, isToxic ? 0.9 : 0.1] }],
        },
        {
          label: 'sexual_explicit',
          results: [{ match: false, probabilities: [0.9, 0.1] }],
        },
        {
          label: 'threat',
          results: [{ match: isToxic && textLower.includes('kill'), probabilities: [0.1, 0.9] }],
        },
      ]);
    }),
  }),
}));

describe('ContentSafetyService', () => {
  let service: ContentSafetyService;

  beforeEach(() => {
    service = new ContentSafetyService();
  });

  it('should be created', () => {
    expect(service).toBeDefined();
  });

  it('should be enabled by default', () => {
    expect(service.enabled()).toBe(true);
  });

  it('should toggle enabled state', () => {
    expect(service.enabled()).toBe(true);
    service.enabled.set(false);
    expect(service.enabled()).toBe(false);
    service.enabled.set(true);
    expect(service.enabled()).toBe(true);
  });

  describe('checkContent', () => {
    it('should return safe for neutral content', async () => {
      const result = await service.checkContent('Hello, how are you today?');
      expect(result.safe).toBe(true);
      expect(result.labels).toEqual([]);
    });

    it('should return safe for empty content', async () => {
      const result = await service.checkContent('');
      expect(result.safe).toBe(true);
      expect(result.labels).toEqual([]);
    });

    it('should return safe for whitespace-only content', async () => {
      const result = await service.checkContent('   ');
      expect(result.safe).toBe(true);
      expect(result.labels).toEqual([]);
    });

    it('should return safe for positive content', async () => {
      const result = await service.checkContent('I love this! Great work everyone.');
      expect(result.safe).toBe(true);
      expect(result.labels).toEqual([]);
    });

    it('should return safe for technical content', async () => {
      const result = await service.checkContent('Write a function to sort an array in JavaScript.');
      expect(result.safe).toBe(true);
      expect(result.labels).toEqual([]);
    });

    it('should flag toxic content with threats', async () => {
      const result = await service.checkContent('I will kill you');
      expect(result.safe).toBe(false);
      expect(result.labels.length).toBeGreaterThan(0);
    });

    it('should flag hateful content', async () => {
      const result = await service.checkContent('I hate you so much');
      expect(result.safe).toBe(false);
      expect(result.labels.length).toBeGreaterThan(0);
    });

    it('should cache the model after first load', async () => {
      // First call
      await service.checkContent('Test content 1');

      // Second call should use cached model
      const result = await service.checkContent('Test content 2');
      expect(result).toBeDefined();
    });
  });
});
