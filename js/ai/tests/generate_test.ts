import assert from 'node:assert';
import { describe, it } from 'node:test';
import { z } from 'zod';
import { GenerateOptions, toGenerateRequest } from '../src/generate';
import { defineTool } from '../src/tool';

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
    it(test.should, () => {
      assert.deepStrictEqual(
        toGenerateRequest(test.prompt as GenerateOptions),
        test.expectedOutput
      );
    });
  }
});
