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

import * as assert from 'assert';
import { genkit, z } from 'genkit';
import { describe, test } from 'node:test';
import { anthropic } from '../src/index.js';
import { __testClient } from '../src/types.js';
import {
  createMockAnthropicClient,
  createMockAnthropicMessage,
} from './mocks/anthropic-client.js';

describe('Structured Output Tests', () => {
  test('should pass output_format to API when using beta API with constrained output', async () => {
    // Set up mock client to return a mock response
    const mockClient = createMockAnthropicClient({
      messageResponse: createMockAnthropicMessage({
        text: '{"name":"Alice","age":30,"city":"New York","isStudent":false,"isEmployee":true,"isRetired":false,"isUnemployed":false,"isDisabled":false}',
      }),
    });

    // Set up plugin with beta API enabled
    const plugin = anthropic({
      apiKey: 'test-key',
      apiVersion: 'beta',
      // @ts-ignore
      [__testClient]: mockClient,
    });

    // Create Genkit instance with the plugin
    const ai = genkit({
      plugins: [plugin],
    });

    // Call generate with sonnet 4.5 (supports native constrained output)
    await ai.generate({
      model: 'anthropic/claude-sonnet-4-5',
      prompt:
        'Generate a fictional person with name "Alice", age 30, and city "New York". Return only the JSON.',
      output: {
        schema: z.object({
          name: z.string(),
          age: z.number(),
          city: z.string(),
          isStudent: z.boolean(),
          isEmployee: z.boolean(),
          isRetired: z.boolean(),
          isUnemployed: z.boolean(),
          isDisabled: z.boolean(),
        }),
        format: 'json',
        constrained: true,
      },
    });

    // Verify the beta API was called with output_format
    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(
      betaCreateStub.mock.calls.length,
      1,
      'Beta API should be called once'
    );

    const apiRequest = betaCreateStub.mock.calls[0].arguments[0];
    assert.ok(apiRequest.output_format, 'Request should have output_format');
    assert.strictEqual(
      apiRequest.output_format.type,
      'json_schema',
      'output_format type should be json_schema'
    );
    assert.ok(
      apiRequest.output_format.schema,
      'output_format should have schema'
    );

    // Verify schema transformation: additionalProperties should be false
    assert.strictEqual(
      apiRequest.output_format.schema.additionalProperties,
      false,
      'Schema should have additionalProperties: false'
    );
  });

  // TODO: finish off this test suite
  // test('should NOT pass output_format when constrained is false', async () => {
  //   const mockClient = createMockAnthropicClient({
  //     messageResponse: createMockAnthropicMessage({
  //       text: '{"name":"Alice"}',
  //     }),
  //   });

  //   const plugin = anthropic({
  //     apiKey: 'test-key',
  //     apiVersion: 'beta',
  //     // @ts-ignore
  //     [__testClient]: mockClient,
  //   });

  //   // @ts-ignore
  //   const modelAction = plugin.resolve(
  //     'model',
  //     'claude-3-5-sonnet-20241022'
  //   ) as ModelAction;

  //   const request: GenerateRequest = {
  //     messages: [
  //       {
  //         role: 'user',
  //         content: [{ text: 'Generate JSON' }],
  //       },
  //     ],
  //     output: {
  //       format: 'json',
  //       constrained: false,
  //       schema: {
  //         type: 'object',
  //         properties: {
  //           name: { type: 'string' },
  //         },
  //       },
  //     },
  //   };

  //   await modelAction(request, {
  //     streamingRequested: false,
  //     sendChunk: mock.fn(),
  //     abortSignal: new AbortController().signal,
  //   });

  //   const betaCreateStub = mockClient.beta.messages.create as any;
  //   const apiRequest = betaCreateStub.mock.calls[0].arguments[0];
  //   assert.strictEqual(
  //     apiRequest.output_format,
  //     undefined,
  //     'Request should NOT have output_format when constrained is false'
  //   );
  // });

  // test('should NOT pass output_format when using stable API', async () => {
  //   const mockClient = createMockAnthropicClient({
  //     messageResponse: createMockAnthropicMessage({
  //       text: '{"name":"Alice","age":30,"city":"New York"}',
  //     }),
  //   });

  //   const plugin = anthropic({
  //     apiKey: 'test-key',
  //     apiVersion: 'stable',
  //     // @ts-ignore
  //     [__testClient]: mockClient,
  //   });

  //   const modelAction = plugin.resolve(
  //     'model',
  //     'claude-3-5-sonnet-20241022'
  //   ) as ModelAction;

  //   const request: GenerateRequest = {
  //     messages: [
  //       {
  //         role: 'user',
  //         content: [{ text: 'Generate JSON' }],
  //       },
  //     ],
  //     output: {
  //       format: 'json',
  //       constrained: true,
  //       schema: {
  //         type: 'object',
  //         properties: {
  //           name: { type: 'string' },
  //           age: { type: 'number' },
  //           city: { type: 'string' },
  //         },
  //       },
  //     },
  //   };

  //   await modelAction(request, {
  //     streamingRequested: false,
  //     sendChunk: mock.fn(),
  //     abortSignal: new AbortController().signal,
  //   });

  //   // Stable API should be called, not beta
  //   const stableCreateStub = mockClient.messages.create as any;
  //   assert.strictEqual(
  //     stableCreateStub.mock.calls.length,
  //     1,
  //     'Stable API should be called once'
  //   );

  //   const apiRequest = stableCreateStub.mock.calls[0].arguments[0];
  //   assert.strictEqual(
  //     apiRequest.output_format,
  //     undefined,
  //     'Stable API request should NOT have output_format'
  //   );
  // });

  // test('should NOT pass output_format when format is not json', async () => {
  //   const mockClient = createMockAnthropicClient({
  //     messageResponse: createMockAnthropicMessage({
  //       text: 'Some text response',
  //     }),
  //   });

  //   const plugin = anthropic({
  //     apiKey: 'test-key',
  //     apiVersion: 'beta',
  //     [__testClient]: mockClient,
  //   });

  //   const modelAction = plugin.resolve(
  //     'model',
  //     'claude-3-5-sonnet-20241022'
  //   ) as ModelAction;

  //   const request: GenerateRequest = {
  //     messages: [
  //       {
  //         role: 'user',
  //         content: [{ text: 'Generate text' }],
  //       },
  //     ],
  //     output: {
  //       format: 'text',
  //       constrained: true,
  //     },
  //   };

  //   await modelAction(request, {
  //     streamingRequested: false,
  //     sendChunk: mock.fn(),
  //     abortSignal: new AbortController().signal,
  //   });

  //   const betaCreateStub = mockClient.beta.messages.create as any;
  //   const apiRequest = betaCreateStub.mock.calls[0].arguments[0];
  //   assert.strictEqual(
  //     apiRequest.output_format,
  //     undefined,
  //     'Request should NOT have output_format when format is text'
  //   );
  // });

  // test('should NOT pass output_format when schema is not provided', async () => {
  //   const mockClient = createMockAnthropicClient({
  //     messageResponse: createMockAnthropicMessage({
  //       text: '{"anything": "goes"}',
  //     }),
  //   });

  //   const plugin = anthropic({
  //     apiKey: 'test-key',
  //     apiVersion: 'beta',
  //     [__testClient]: mockClient,
  //   });

  //   const modelAction = plugin.resolve(
  //     'model',
  //     'claude-3-5-sonnet-20241022'
  //   ) as ModelAction;

  //   const request: GenerateRequest = {
  //     messages: [
  //       {
  //         role: 'user',
  //         content: [{ text: 'Generate JSON' }],
  //       },
  //     ],
  //     output: {
  //       format: 'json',
  //       constrained: true,
  //       // No schema provided
  //     },
  //   };

  //   await modelAction(request, {
  //     streamingRequested: false,
  //     sendChunk: mock.fn(),
  //     abortSignal: new AbortController().signal,
  //   });

  //   const betaCreateStub = mockClient.beta.messages.create as any;
  //   const apiRequest = betaCreateStub.mock.calls[0].arguments[0];
  //   assert.strictEqual(
  //     apiRequest.output_format,
  //     undefined,
  //     'Request should NOT have output_format when schema is not provided'
  //   );
  // });
});
