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

import { afterEach, describe, expect, it, jest } from '@jest/globals';
import type OpenAI from 'openai';
import { defineCompatOpenAIModel } from '../src/model';
import {
  novitaModelRef,
  SUPPORTED_NOVITA_MODELS,
} from '../src/novita/novita';

jest.mock('genkit/model', () => {
  const originalModule =
    jest.requireActual<typeof import('genkit/model')>('genkit/model');
  return {
    ...originalModule,
    defineModel: jest.fn((_, runner) => {
      return runner;
    }),
  };
});

describe('novitaModelRef', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should prefix names with novita namespace', () => {
    const ref = novitaModelRef({ name: 'moonshotai/kimi-k2.5' });
    expect(ref.name).toBe('novita/moonshotai/kimi-k2.5');
  });

  it('should not double-prefix names already in novita namespace', () => {
    const ref = novitaModelRef({ name: 'novita/moonshotai/kimi-k2.5' });
    expect(ref.name).toBe('novita/moonshotai/kimi-k2.5');
  });
});

describe('SUPPORTED_NOVITA_MODELS', () => {
  it('should define all three chat models', () => {
    const keys = Object.keys(SUPPORTED_NOVITA_MODELS);
    expect(keys).toContain('moonshotai/kimi-k2.5');
    expect(keys).toContain('zai-org/glm-5');
    expect(keys).toContain('minimax/minimax-m2.5');
  });

  it('kimi-k2.5 should support vision (media)', () => {
    const ref = SUPPORTED_NOVITA_MODELS['moonshotai/kimi-k2.5'];
    expect(ref.info?.supports?.media).toBe(true);
  });

  it('glm-5 and minimax-m2.5 should not support media', () => {
    expect(
      SUPPORTED_NOVITA_MODELS['zai-org/glm-5'].info?.supports?.media
    ).toBe(false);
    expect(
      SUPPORTED_NOVITA_MODELS['minimax/minimax-m2.5'].info?.supports?.media
    ).toBe(false);
  });

  it('all models should support tools and json output', () => {
    for (const ref of Object.values(SUPPORTED_NOVITA_MODELS)) {
      expect(ref.info?.supports?.tools).toBe(true);
      expect(ref.info?.supports?.output).toContain('json');
    }
  });
});

describe('novita defineCompatOpenAIModel', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should correctly define kimi-k2.5 model', () => {
    const modelRef = SUPPORTED_NOVITA_MODELS['moonshotai/kimi-k2.5'];
    const model = defineCompatOpenAIModel({
      name: modelRef.name,
      client: {} as OpenAI,
      modelRef,
    });
    expect({
      name: model.__action.name,
      supports: model.__action.metadata?.model.supports,
    }).toStrictEqual({
      name: 'novita/moonshotai/kimi-k2.5',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
        constrained: 'all',
      },
    });
  });

  it('should correctly define glm-5 model', () => {
    const modelRef = SUPPORTED_NOVITA_MODELS['zai-org/glm-5'];
    const model = defineCompatOpenAIModel({
      name: modelRef.name,
      client: {} as OpenAI,
      modelRef,
    });
    expect({
      name: model.__action.name,
      supports: model.__action.metadata?.model.supports,
    }).toStrictEqual({
      name: 'novita/zai-org/glm-5',
      supports: {
        multiturn: true,
        tools: true,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
        constrained: 'all',
      },
    });
  });
});

describe('novitaPlugin auth', () => {
  it('should throw if no API key is provided', async () => {
    const savedEnv = process.env.NOVITA_API_KEY;
    delete process.env.NOVITA_API_KEY;
    try {
      const { novitaPlugin } = await import('../src/novita/index.js');
      expect(() => novitaPlugin()).toThrow('NOVITA_API_KEY');
    } finally {
      if (savedEnv !== undefined) {
        process.env.NOVITA_API_KEY = savedEnv;
      }
    }
  });
});
