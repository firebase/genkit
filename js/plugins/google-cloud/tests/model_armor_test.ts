/**
 * Copyright 2025 Google LLC
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

import { beforeEach, describe, expect, it } from '@jest/globals';
import { genkit } from 'genkit';
import { modelArmor } from '../src/model-armor.js';

// Mock ModelArmorClient
class MockModelArmorClient {
  sanitizeUserPrompt = async () => [{}];
  sanitizeModelResponse = async () => [{}];
}

function createEmptyResult() {
  return { sanitizationResult: {} };
}

function createSdpResult(replacementText: string) {
  return {
    sanitizationResult: {
      filterResults: {
        sdp: {
          sdpFilterResult: {
            deidentifyResult: {
              data: { text: replacementText },
            },
          },
        },
      },
    },
  };
}

function createRaiBlockResult() {
  return {
    sanitizationResult: {
      filterMatchState: 'MATCH_FOUND',
      filterResults: {
        rai: { raiFilterResult: { matchState: 'MATCH_FOUND' } },
      },
    },
  };
}

function createSdpBlockResult(replacementText: string) {
  const res = createSdpResult(replacementText);
  (res.sanitizationResult as any).filterMatchState = 'MATCH_FOUND';
  return res;
}

describe('modelArmor', () => {
  let ai: any;
  let mockClient: any;

  beforeEach(() => {
    ai = genkit({});
    ai.defineModel({ name: 'echoModel' }, async (req: any) => {
      return {
        message: {
          role: 'model',
          content: [{ text: `Echo: ${req.messages[0].content[0].text}` }],
        },
      };
    });
    mockClient = new MockModelArmorClient();
  });

  it('passes through when no sanitization triggers', async () => {
    mockClient.sanitizeUserPrompt = async () => [createEmptyResult()];
    mockClient.sanitizeModelResponse = async () => [createEmptyResult()];

    const response = await ai.generate({
      model: 'echoModel',
      prompt: 'hello',
      use: [modelArmor({ templateName: 'test', client: mockClient as any })],
    });

    expect(response.text).toMatch(/Echo: hello/);
  });

  it('replaces user prompt on SDP match', async () => {
    mockClient.sanitizeUserPrompt = async () => [
      createSdpResult('sanitized_hello'),
    ];
    mockClient.sanitizeModelResponse = async () => [createEmptyResult()];

    const response = await ai.generate({
      model: 'echoModel',
      prompt: 'hello',
      use: [modelArmor({ templateName: 'test', client: mockClient as any })],
    });

    // The echo model should receive the SANITIZED prompt
    expect(response.text).toMatch(/Echo: sanitized_hello/);
  });

  it('blocks user prompt on RAI match', async () => {
    mockClient.sanitizeUserPrompt = async () => [createRaiBlockResult()];

    await expect(
      ai.generate({
        model: 'echoModel',
        prompt: 'bad stuff',
        use: [modelArmor({ templateName: 'test', client: mockClient as any })],
      })
    ).rejects.toThrow(
      expect.objectContaining({
        status: 'PERMISSION_DENIED',
        message: expect.stringContaining('Model Armor blocked user prompt.'),
      })
    );
  });

  it('replaces model response on SDP match', async () => {
    mockClient.sanitizeUserPrompt = async () => [createEmptyResult()];
    mockClient.sanitizeModelResponse = async () => [
      createSdpResult('sanitized_response'),
    ];

    const response = await ai.generate({
      model: 'echoModel',
      prompt: 'hello',
      use: [modelArmor({ templateName: 'test', client: mockClient as any })],
    });

    expect(response.text).toBe('sanitized_response');
  });

  it('blocks model response on RAI match', async () => {
    mockClient.sanitizeUserPrompt = async () => [createEmptyResult()];
    mockClient.sanitizeModelResponse = async () => [createRaiBlockResult()];

    await expect(
      ai.generate({
        model: 'echoModel',
        prompt: 'hello',
        use: [modelArmor({ templateName: 'test', client: mockClient as any })],
      })
    ).rejects.toThrow(
      expect.objectContaining({
        status: 'PERMISSION_DENIED',
        message: expect.stringContaining('Model Armor blocked model response.'),
      })
    );
  });

  it('respects protectionTarget=userPrompt', async () => {
    // Should sanitize prompt but NOT response
    mockClient.sanitizeUserPrompt = async () => [createSdpResult('sanitized')];
    // This one would block if called
    mockClient.sanitizeModelResponse = async () => [createRaiBlockResult()];

    const response = await ai.generate({
      model: 'echoModel',
      prompt: 'hello',
      use: [
        modelArmor({
          templateName: 'test',
          client: mockClient as any,
          protectionTarget: 'userPrompt',
        }),
      ],
    });

    expect(response.text).toMatch(/Echo: sanitized/);
  });

  it('strictSdpEnforcement blocks even if remediated', async () => {
    mockClient.sanitizeUserPrompt = async () => [
      createSdpBlockResult('sanitized_hello'),
    ];

    await expect(
      ai.generate({
        model: 'echoModel',
        prompt: 'sensitive',
        use: [
          modelArmor({
            templateName: 'test',
            client: mockClient as any,
            strictSdpEnforcement: true,
          }),
        ],
      })
    ).rejects.toThrow(
      expect.objectContaining({
        status: 'PERMISSION_DENIED',
        message: expect.stringContaining('Model Armor blocked user prompt.'),
      })
    );
  });

  it('respects filters option', async () => {
    // RAI match found, but we only filter 'csam'
    mockClient.sanitizeUserPrompt = async () => [
      {
        sanitizationResult: {
          filterMatchState: 'MATCH_FOUND',
          filterResults: {
            rai: { raiFilterResult: { matchState: 'MATCH_FOUND' } },
          },
        },
      },
    ];

    const response = await ai.generate({
      model: 'echoModel',
      prompt: 'bad stuff',
      use: [
        modelArmor({
          templateName: 'test',
          client: mockClient as any,
          filters: ['csam'],
        }),
      ],
    });

    expect(response.text).toMatch(/Echo: bad stuff/);
  });
});
