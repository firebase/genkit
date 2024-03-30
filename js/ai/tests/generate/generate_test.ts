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

import assert from 'node:assert';
import { describe, it } from 'node:test';
import { z } from 'zod';
import {
  Candidate,
  GenerateOptions,
  Message,
  toGenerateRequest,
} from '../../src/generate.js';
import { CandidateData } from '../../src/model.js';
import { defineTool } from '../../src/tool.js';

describe('Candidate toJSON() tests', () => {
  const testCases = [
    {
      should: 'serialize correctly when custom is undefined',
      candidateData: {
        message: new Message({
          role: 'model',
          content: [{ text: '{"name": "Bob"}' }],
        }),
        index: 0,
        usage: {},
        finishReason: 'stop',
        finishMessage: '',
        // No 'custom' property
      },
      expectedOutput: {
        message: { content: [{ text: '{"name": "Bob"}' }], role: 'model' }, // NOTE THIS IS WRONG??
        index: 0,
        usage: {},
        finishReason: 'stop',
        finishMessage: '',
        custom: undefined, // Or omit this if appropriate
      },
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const candidate = new Candidate(test.candidateData as Candidate);
      assert.deepStrictEqual(candidate.toJSON(), test.expectedOutput);
    });
  }
});

describe('Candidate output() tests', () => {
  const testCases = [
    {
      should: 'return structured data from the data part',
      candidateData: {
        message: new Message({
          role: 'model',
          content: [{ data: { name: 'Alice', age: 30 } }],
        }),
        index: 0,
        usage: {},
        finishReason: 'stop',
        finishMessage: '',
        custom: {},
      },
      expectedOutput: { name: 'Alice', age: 30 },
    },
    {
      should: 'parse JSON from text when the data part is absent',
      candidateData: {
        message: new Message({
          role: 'model',
          content: [{ text: '{"name": "Bob"}' }],
        }),
        index: 0,
        usage: {},
        finishReason: 'stop',
        finishMessage: '',
        custom: {},
      },
      expectedOutput: { name: 'Bob' },
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const candidate = new Candidate(test.candidateData as CandidateData);
      assert.deepStrictEqual(candidate.output(), test.expectedOutput);
    });
  }
});

describe('toGenerateRequest', () => {
  // register tools
  const tellAFunnyJoke = defineTool({
    name: 'tellAFunnyJoke',
    description:
      'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
    input: z.object({ topic: z.string() }),
    output: z.string(),
    fn: async (input) => {
      return `Why did the ${input.topic} cross the road?`;
    },
  });

  const testCases = [
    {
      should: 'translate a string prompt correctly',
      prompt: {
        model: 'vertex-ai/gemini-1.0-pro',
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        tools: [],
        output: { format: 'text', schema: undefined },
      },
    },
    {
      should:
        'translate a string prompt correctly with tools referenced by their name',
      prompt: {
        model: 'vertex-ai/gemini-1.0-pro',
        tools: ['tellAFunnyJoke'],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text', schema: undefined },
      },
    },
    {
      should:
        'translate a string prompt correctly with tools referenced by their action',
      prompt: {
        model: 'vertex-ai/gemini-1.0-pro',
        tools: [tellAFunnyJoke],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text', schema: undefined },
      },
    },
    {
      should: 'translate a media prompt correctly',
      prompt: {
        model: 'vertex-ai/gemini-1.0-pro',
        prompt: [
          { text: 'describe the following image:' },
          {
            media: {
              url: 'https://picsum.photos/200',
              contentType: 'image/jpeg',
            },
          },
        ],
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: [
              { text: 'describe the following image:' },
              {
                media: {
                  url: 'https://picsum.photos/200',
                  contentType: 'image/jpeg',
                },
              },
            ],
          },
        ],
        candidates: undefined,
        config: undefined,
        tools: [],
        output: { format: 'text', schema: undefined },
      },
    },
    {
      should: 'translate a prompt with history correctly',
      prompt: {
        model: 'vertex-ai/gemini-1.0-pro',
        history: [
          { content: [{ text: 'hi' }], role: 'user' },
          { content: [{ text: 'how can I help you' }], role: 'model' },
        ],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { content: [{ text: 'hi' }], role: 'user' },
          { content: [{ text: 'how can I help you' }], role: 'model' },
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        tools: [],
        output: { format: 'text', schema: undefined },
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, async () => {
      assert.deepStrictEqual(
        await toGenerateRequest(test.prompt as GenerateOptions),
        test.expectedOutput
      );
    });
  }
});
