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
import { GenerateResponseChunk } from '../../src/generate';
import {
  Candidate,
  GenerateOptions,
  GenerateResponse,
  Message,
  toGenerateRequest,
} from '../../src/generate.js';
import { GenerateResponseChunkData } from '../../src/model';
import {
  CandidateData,
  GenerateRequest,
  MessageData,
} from '../../src/model.js';
import { defineTool } from '../../src/tool.js';

describe('Candidate', () => {
  describe('#toJSON()', () => {
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

  describe('#output()', () => {
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

  describe('#hasValidOutput()', () => {
    const good: MessageData = {
      role: 'model',
      content: [{ text: '{"abc": 123}' }],
    };
    const bad: MessageData = {
      role: 'model',
      content: [{ text: '{"abc": "123"}' }],
    };
    const goodData: MessageData = {
      role: 'model',
      content: [{ data: { abc: 123 } }],
    };
    const badData: MessageData = {
      role: 'model',
      content: [{ data: { abc: '123' } }],
    };
    const schemaRequest = {
      output: {
        schema: { type: 'object', properties: { abc: { type: 'number' } } },
      },
    } as unknown as GenerateRequest;

    it('returns true if no schema', () => {
      assert(
        new Candidate<any>({
          index: 0,
          message: bad,
          finishReason: 'stop',
        }).hasValidOutput()
      );
    });

    it('returns correctly based on validation from data', () => {
      assert(
        !new Candidate<any>({
          index: 0,
          message: badData,
          finishReason: 'stop',
        }).hasValidOutput(schemaRequest)
      );
      assert(
        !new Candidate<any>(
          { index: 0, message: badData, finishReason: 'stop' },
          schemaRequest
        ).hasValidOutput()
      );
      assert(
        new Candidate<any>({
          index: 0,
          message: goodData,
          finishReason: 'stop',
        }).hasValidOutput(schemaRequest)
      );
      assert(
        new Candidate<any>(
          { index: 0, message: goodData, finishReason: 'stop' },
          schemaRequest
        ).hasValidOutput()
      );
    });

    it('returns correctly based on validation from output', () => {
      assert(
        !new Candidate<any>({
          index: 0,
          message: bad,
          finishReason: 'stop',
        }).hasValidOutput(schemaRequest)
      );
      assert(
        !new Candidate<any>(
          { index: 0, message: bad, finishReason: 'stop' },
          schemaRequest
        ).hasValidOutput()
      );
      assert(
        new Candidate<any>({
          index: 0,
          message: good,
          finishReason: 'stop',
        }).hasValidOutput(schemaRequest)
      );
      assert(
        new Candidate<any>(
          { index: 0, message: good, finishReason: 'stop' },
          schemaRequest
        ).hasValidOutput()
      );
    });
  });
});

describe('GenerateResponse', () => {
  describe('#output()', () => {
    it('picks the first candidate with valid output if no index provided', () => {
      const schemaRequest = {
        output: {
          schema: { type: 'object', properties: { abc: { type: 'number' } } },
        },
      } as unknown as GenerateRequest;
      const response = new GenerateResponse(
        {
          candidates: [
            {
              index: 0,
              finishReason: 'stop',
              message: { role: 'model', content: [{ text: '{"abc":"123"}' }] },
            },
            {
              index: 0,
              finishReason: 'stop',
              message: { role: 'model', content: [{ text: '{"abc":123}' }] },
            },
          ],
        },
        schemaRequest
      );
      assert.deepStrictEqual(response.output(), { abc: 123 });
      assert.deepStrictEqual(response.output(0), { abc: '123' });
    });
  });
  describe('#toolRequests()', () => {
    it('returns empty array if no tools requests found', () => {
      const response = new GenerateResponse({
        candidates: [
          {
            index: 0,
            finishReason: 'stop',
            message: { role: 'model', content: [{ text: '{"abc":"123"}' }] },
          },
          {
            index: 0,
            finishReason: 'stop',
            message: { role: 'model', content: [{ text: '{"abc":123}' }] },
          },
        ],
      });
      assert.deepStrictEqual(response.toolRequests(), []);
      assert.deepStrictEqual(response.toolRequests(0), []);
    });
    it('picks the first candidate if no index provided', () => {
      const toolCall = {
        toolRequest: {
          name: 'foo',
          ref: 'abc',
          input: 'banana',
        },
      };
      const response = new GenerateResponse({
        candidates: [
          {
            index: 0,
            finishReason: 'stop',
            message: {
              role: 'model',
              content: [toolCall],
            },
          },
          {
            index: 0,
            finishReason: 'stop',
            message: { role: 'model', content: [{ text: '{"abc":123}' }] },
          },
        ],
      });
      assert.deepStrictEqual(response.toolRequests(), [toolCall]);
      assert.deepStrictEqual(response.toolRequests(0), [toolCall]);
    });
    it('returns all tool call', () => {
      const toolCall1 = {
        toolRequest: {
          name: 'foo',
          ref: 'abc',
          input: 'banana',
        },
      };
      const toolCall2 = {
        toolRequest: {
          name: 'bar',
          ref: 'bcd',
          input: 'apple',
        },
      };
      const response = new GenerateResponse({
        candidates: [
          {
            index: 0,
            finishReason: 'stop',
            message: {
              role: 'model',
              content: [toolCall1, toolCall2],
            },
          },
          {
            index: 0,
            finishReason: 'stop',
            message: { role: 'model', content: [{ text: '{"abc":123}' }] },
          },
        ],
      });
      assert.deepStrictEqual(response.toolRequests(), [toolCall1, toolCall2]);
    });
  });
});

describe('toGenerateRequest', () => {
  // register tools
  const tellAFunnyJoke = defineTool(
    {
      name: 'tellAFunnyJoke',
      description:
        'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
      inputSchema: z.object({ topic: z.string() }),
      outputSchema: z.string(),
    },
    async (input) => {
      return `Why did the ${input.topic} cross the road?`;
    }
  );

  const testCases = [
    {
      should: 'translate a string prompt correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        context: undefined,
        tools: [],
        output: { format: 'text' },
      },
    },
    {
      should:
        'translate a string prompt correctly with tools referenced by their name',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        tools: ['tellAFunnyJoke'],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        context: undefined,
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
              additionalProperties: true,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text' },
      },
    },
    {
      should:
        'translate a string prompt correctly with tools referenced by their action',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        tools: [tellAFunnyJoke],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        candidates: undefined,
        config: undefined,
        context: undefined,
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
              additionalProperties: true,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text' },
      },
    },
    {
      should: 'translate a media prompt correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
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
        context: undefined,
        tools: [],
        output: { format: 'text' },
      },
    },
    {
      should: 'translate a prompt with history correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
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
        context: undefined,
        tools: [],
        output: { format: 'text' },
      },
    },
    {
      should: 'pass context through to the model',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: 'Tell a joke with context.',
        context: [{ content: [{ text: 'context here' }] }],
      },
      expectedOutput: {
        messages: [
          { content: [{ text: 'Tell a joke with context.' }], role: 'user' },
        ],
        candidates: undefined,
        config: undefined,
        context: [{ content: [{ text: 'context here' }] }],
        tools: [],
        output: { format: 'text' },
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

describe('GenerateResponseChunk', () => {
  describe('#output()', () => {
    const testCases = [
      {
        should: 'parse ``` correctly',
        accumulatedChunksTexts: ['```'],
        correctJson: null,
      },
      {
        should: 'parse valid json correctly',
        accumulatedChunksTexts: [`{"foo":"bar"}`],
        correctJson: { foo: 'bar' },
      },
      {
        should: 'if json invalid, return null',
        accumulatedChunksTexts: [`invalid json`],
        correctJson: null,
      },
      {
        should: 'handle missing closing brace',
        accumulatedChunksTexts: [`{"foo":"bar"`],
        correctJson: { foo: 'bar' },
      },
      {
        should: 'handle missing closing bracket in nested object',
        accumulatedChunksTexts: [`{"foo": {"bar": "baz"`],
        correctJson: { foo: { bar: 'baz' } },
      },
      {
        should: 'handle multiple chunks',
        accumulatedChunksTexts: [`{"foo": {"bar"`, `: "baz`],
        correctJson: { foo: { bar: 'baz' } },
      },
      {
        should: 'handle multiple chunks with nested objects',
        accumulatedChunksTexts: [`\`\`\`json{"foo": {"bar"`, `: {"baz": "qux`],
        correctJson: { foo: { bar: { baz: 'qux' } } },
      },
      {
        should: 'handle array nested in object',
        accumulatedChunksTexts: [`{"foo": ["bar`],
        correctJson: { foo: ['bar'] },
      },
      {
        should: 'handle array nested in object with multiple chunks',
        accumulatedChunksTexts: [`\`\`\`json{"foo": {"bar"`, `: ["baz`],
        correctJson: { foo: { bar: ['baz'] } },
      },
    ];

    for (const test of testCases) {
      if (test.should) {
        it(test.should, () => {
          const accumulatedChunks: GenerateResponseChunkData[] =
            test.accumulatedChunksTexts.map((text, index) => ({
              index,
              content: [{ text }],
            }));

          const chunkData = accumulatedChunks[accumulatedChunks.length - 1];

          const responseChunk: GenerateResponseChunk =
            new GenerateResponseChunk(chunkData, accumulatedChunks);

          const output = responseChunk.output();

          assert.deepStrictEqual(output, test.correctJson);
        });
      }
    }
  });
});
