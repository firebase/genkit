/**
 * Copyright 2024 The Fire Company
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
import type { GenerateRequest, Genkit } from 'genkit';
import type OpenAI from 'openai';

import { defineCompatOpenAIModel, toOpenAIRequestBody } from '../src/model';
import { gpt41, gpt41Mini, gpt41Nano, gpt4o } from '../src/openai/gpt';

jest.mock('@genkit-ai/ai/model', () => ({
  ...(jest.requireActual('@genkit-ai/ai/model') as Record<string, unknown>),
  defineModel: jest.fn(),
}));

describe('gptModel', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = {
      defineModel: jest.fn(),
    } as unknown as Genkit;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should correctly define supported GPT models', () => {
    jest.spyOn(ai, 'defineModel').mockImplementation((() => ({})) as any);
    defineCompatOpenAIModel({
      ai,
      name: 'openai/gpt-4o',
      client: {} as OpenAI,
      modelRef: gpt4o,
    });
    expect(ai.defineModel).toHaveBeenCalledWith(
      {
        name: gpt4o.name,
        ...gpt4o.info,
        apiVersion: 'v2',
        configSchema: gpt4o.configSchema,
      },
      expect.any(Function)
    );
  });

  it('should correctly define gpt-4.1, gpt-4.1-mini, and gpt-4.1-nano', () => {
    jest.spyOn(ai, 'defineModel').mockImplementation((() => ({})) as any);
    defineCompatOpenAIModel({
      ai,
      name: 'openai/gpt-4.1',
      client: {} as OpenAI,
      modelRef: gpt41,
    });
    expect(ai.defineModel).toHaveBeenCalledWith(
      {
        name: 'openai/gpt-4.1',
        apiVersion: 'v2',
        ...gpt41.info,
        configSchema: gpt41.configSchema,
      },
      expect.any(Function)
    );

    defineCompatOpenAIModel({
      ai,
      name: 'openai/gpt-4.1-mini',
      client: {} as OpenAI,
      modelRef: gpt41Mini,
    });
    expect(ai.defineModel).toHaveBeenCalledWith(
      {
        name: 'openai/gpt-4.1-mini',
        ...gpt41Mini.info,
        apiVersion: 'v2',
        configSchema: gpt41Mini.configSchema,
      },
      expect.any(Function)
    );

    defineCompatOpenAIModel({
      ai,
      name: 'openai/gpt-4.1-nano',
      client: {} as OpenAI,
      modelRef: gpt41Nano,
    });
    expect(ai.defineModel).toHaveBeenCalledWith(
      {
        name: 'openai/gpt-4.1-nano',
        ...gpt41Nano.info,
        apiVersion: 'v2',
        configSchema: gpt41Nano.configSchema,
      },
      expect.any(Function)
    );
  });
});

// Additional test to ensure toOpenAiRequestBody works for new models

describe('toOpenAiRequestBody for new GPT-4.1 variants', () => {
  const baseRequest = { messages: [] } as GenerateRequest;
  it('should not throw for gpt-4.1', () => {
    expect(() => toOpenAIRequestBody('gpt-4.1', baseRequest)).not.toThrow();
  });
  it('should not throw for gpt-4.1-mini', () => {
    expect(() =>
      toOpenAIRequestBody('gpt-4.1-mini', baseRequest)
    ).not.toThrow();
  });
  it('should not throw for gpt-4.1-nano', () => {
    expect(() =>
      toOpenAIRequestBody('gpt-4.1-nano', baseRequest)
    ).not.toThrow();
  });
});
