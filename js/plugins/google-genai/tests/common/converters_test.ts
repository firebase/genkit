/**
Copyright 2025 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
import * as assert from 'assert';
import { z } from 'genkit';
import type { MessageData } from 'genkit/model';
import { toJsonSchema } from 'genkit/schema';
import { describe, it } from 'node:test';
import {
  fromGeminiCandidate,
  toGeminiFunctionModeEnum,
  toGeminiMessage,
  toGeminiSystemInstruction,
  toGeminiTool,
} from '../../src/common/converters.js';
import type { GenerateContentCandidate } from '../../src/common/types.js';
import {
  ExecutableCodeLanguage,
  FunctionCallingMode,
  Outcome,
  SchemaType,
} from '../../src/common/types.js';

describe('toGeminiMessage', () => {
  const testCases = [
    {
      should: 'should transform genkit message (text content) correctly',
      inputMessage: {
        role: 'user',
        content: [{ text: 'Tell a joke about dogs.' }],
      },
      expectedOutput: {
        role: 'user',
        parts: [{ text: 'Tell a joke about dogs.' }],
      },
    },
    {
      should:
        'should transform genkit message (tool request content) correctly',
      inputMessage: {
        role: 'model',
        content: [
          { toolRequest: { name: 'tellAFunnyJoke', input: { topic: 'dogs' } } },
        ],
      },
      expectedOutput: {
        role: 'model',
        parts: [
          { functionCall: { name: 'tellAFunnyJoke', args: { topic: 'dogs' } } },
        ],
      },
    },
    {
      should:
        'should transform genkit message (tool response content) correctly and sort by ref',
      inputMessage: {
        role: 'tool',
        content: [
          {
            toolResponse: {
              name: 'tellAFunnyJoke',
              output: 'Why did the dogs cross the road?',
              ref: '1',
            },
          },
          {
            toolResponse: {
              name: 'tellAFunnyJoke',
              output: 'Why did the chicken cross the road?',
              ref: '0',
            },
          },
        ],
      },
      expectedOutput: {
        role: 'function',
        parts: [
          {
            functionResponse: {
              name: 'tellAFunnyJoke',
              response: {
                name: 'tellAFunnyJoke',
                content: 'Why did the chicken cross the road?',
              },
            },
          },
          {
            functionResponse: {
              name: 'tellAFunnyJoke',
              response: {
                name: 'tellAFunnyJoke',
                content: 'Why did the dogs cross the road?',
              },
            },
          },
        ],
      },
    },
    {
      should:
        'should transform genkit message (inline base64 image content) correctly',
      inputMessage: {
        role: 'user',
        content: [
          { text: 'describe the following image:' },
          {
            media: {
              contentType: 'image/jpeg',
              url: 'data:image/jpeg;base64,SHORTENED_BASE64_DATA',
            },
          },
        ],
      },
      expectedOutput: {
        role: 'user',
        parts: [
          { text: 'describe the following image:' },
          {
            inlineData: {
              mimeType: 'image/jpeg',
              data: 'SHORTENED_BASE64_DATA',
            },
          },
        ],
      },
    },
    {
      should:
        'should transform genkit message (fileData image content) correctly',
      inputMessage: {
        role: 'user',
        content: [
          { text: 'describe the following image:' },
          {
            media: {
              contentType: 'image/png',
              url: 'gs://bucket/image.png',
            },
          },
        ],
      },
      expectedOutput: {
        role: 'user',
        parts: [
          { text: 'describe the following image:' },
          {
            fileData: {
              mimeType: 'image/png',
              fileUri: 'gs://bucket/image.png',
            },
          },
        ],
      },
    },
    {
      should: 'should re-populate thoughtSignature from reasoning metadata',
      inputMessage: {
        role: 'model',
        content: [{ reasoning: '', metadata: { thoughtSignature: 'abc123' } }],
      },
      expectedOutput: {
        role: 'model',
        parts: [{ thought: true, thoughtSignature: 'abc123' }],
      },
    },
    {
      should: 'should transform reasoning with text',
      inputMessage: {
        role: 'model',
        content: [
          {
            reasoning: 'I should call a tool',
            metadata: { thoughtSignature: 'def456' },
          },
        ],
      },
      expectedOutput: {
        role: 'model',
        parts: [
          {
            thought: true,
            text: 'I should call a tool',
            thoughtSignature: 'def456',
          },
        ],
      },
    },
    {
      should: 'should transform executableCode custom part',
      inputMessage: {
        role: 'model',
        content: [
          {
            custom: {
              executableCode: {
                language: ExecutableCodeLanguage.PYTHON,
                code: 'print(1+1)',
              },
            },
          },
        ],
      },
      expectedOutput: {
        role: 'model',
        parts: [
          {
            executableCode: {
              language: ExecutableCodeLanguage.PYTHON,
              code: 'print(1+1)',
            },
          },
        ],
      },
    },
    {
      should: 'should transform codeExecutionResult custom part',
      inputMessage: {
        role: 'tool',
        content: [
          {
            custom: {
              codeExecutionResult: {
                outcome: Outcome.OUTCOME_OK,
                output: '2',
              },
            },
          },
        ],
      },
      expectedOutput: {
        role: 'function',
        parts: [
          {
            codeExecutionResult: {
              outcome: Outcome.OUTCOME_OK,
              output: '2',
            },
          },
        ],
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, () => {
      assert.deepStrictEqual(
        toGeminiMessage(test.inputMessage as MessageData),
        test.expectedOutput
      );
    });
  }

  it('should throw on unsupported part type', () => {
    const inputMessage = {
      role: 'user',
      content: [{ unsupported: 'data' } as any],
    };
    assert.throws(
      () => toGeminiMessage(inputMessage as MessageData),
      /Unsupported Part type/
    );
  });

  it('should throw on media part missing contentType for non-data URL', () => {
    const inputMessage = {
      role: 'user',
      content: [
        {
          media: {
            url: 'gs://bucket/file',
          },
        } as any,
      ],
    };
    assert.throws(
      () => toGeminiMessage(inputMessage as MessageData),
      /Must supply a (`)?contentType(`)? when sending File URIs to Gemini/
    );
  });
});

describe('toGeminiSystemInstruction', () => {
  const testCases = [
    {
      should: 'should transform from system to user',
      inputMessage: {
        role: 'system',
        content: [{ text: 'You are an expert in all things cats.' }],
      },
      expectedOutput: {
        role: 'user',
        parts: [{ text: 'You are an expert in all things cats.' }],
      },
    },
    {
      should: 'should transform from system to user with multiple parts',
      inputMessage: {
        role: 'system',
        content: [
          { text: 'You are an expert in all things animals.' },
          { text: 'You love cats.' },
        ],
      },
      expectedOutput: {
        role: 'user',
        parts: [
          { text: 'You are an expert in all things animals.' },
          { text: 'You love cats.' },
        ],
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, () => {
      assert.deepStrictEqual(
        toGeminiSystemInstruction(test.inputMessage as MessageData),
        test.expectedOutput
      );
    });
  }
});

describe('fromGeminiCandidate', () => {
  const testCases = [
    {
      should:
        'should transform gemini candidate to genkit candidate (text parts) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              text: 'Why did the dog go to the bank?\n\nTo get his bones cashed!',
            },
          ],
        },
        finishReason: 'STOP',
        safetyRatings: [
          { category: 'HARM_CATEGORY_HATE_SPEECH', probability: 'NEGLIGIBLE' },
        ],
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              text: 'Why did the dog go to the bank?\n\nTo get his bones cashed!',
            },
          ],
        },
        finishReason: 'stop',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: [
            {
              category: 'HARM_CATEGORY_HATE_SPEECH',
              probability: 'NEGLIGIBLE',
            },
          ],
        },
      },
    },
    {
      should:
        'should transform gemini candidate to genkit candidate (function call parts) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              functionCall: { name: 'tellAFunnyJoke', args: { topic: 'dog' } },
            },
            {
              functionCall: {
                name: 'my__tool__name',
                args: { param: 'value' },
              },
            },
          ],
        },
        finishReason: 'STOP',
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              toolRequest: {
                name: 'tellAFunnyJoke',
                input: { topic: 'dog' },
                ref: '0',
              },
            },
            {
              toolRequest: {
                name: 'my__tool__name', // Expected no conversion for functionCall
                input: { param: 'value' },
                ref: '1',
              },
            },
          ],
        },
        finishReason: 'stop',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: undefined,
        },
      },
    },
    {
      should:
        'should transform gemini candidate to genkit candidate (thought parts) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              thought: true,
              thoughtSignature: 'abc123',
            },
            {
              thought: true,
              text: 'thought with text',
              thoughtSignature: 'def456',
            },
          ],
        },
        finishReason: 'STOP',
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              reasoning: '',
              metadata: { thoughtSignature: 'abc123' },
            },
            {
              reasoning: 'thought with text',
              metadata: { thoughtSignature: 'def456' },
            },
          ],
        },
        finishReason: 'stop',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: undefined,
        },
      },
    },
    {
      should: 'should transform gemini candidate (inlineData) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              inlineData: {
                mimeType: 'image/jpeg',
                data: 'SHORTENED_BASE64_DATA',
              },
            },
          ],
        },
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              media: {
                contentType: 'image/jpeg',
                url: 'data:image/jpeg;base64,SHORTENED_BASE64_DATA',
              },
            },
          ],
        },
        finishReason: 'unknown',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: undefined,
        },
      },
    },
    {
      should: 'should transform gemini candidate (fileData) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              fileData: {
                mimeType: 'image/png',
                fileUri: 'gs://bucket/image.png',
              },
            },
          ],
        },
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              media: {
                contentType: 'image/png',
                url: 'gs://bucket/image.png',
              },
            },
          ],
        },
        finishReason: 'unknown',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: undefined,
        },
      },
    },
    {
      should: 'should transform gemini candidate (executableCode) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              executableCode: {
                language: ExecutableCodeLanguage.PYTHON,
                code: 'print(1+1)',
              },
            },
          ],
        },
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              custom: {
                executableCode: {
                  language: ExecutableCodeLanguage.PYTHON,
                  code: 'print(1+1)',
                },
              },
            },
          ],
        },
        finishReason: 'unknown',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: undefined,
        },
      },
    },
    {
      should:
        'should transform gemini candidate (codeExecutionResult) correctly',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {
              codeExecutionResult: {
                outcome: Outcome.OUTCOME_OK,
                output: '2',
              },
            },
          ],
        },
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              custom: {
                codeExecutionResult: {
                  outcome: Outcome.OUTCOME_OK,
                  output: '2',
                },
              },
            },
          ],
        },
        finishReason: 'unknown',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: undefined,
        },
      },
    },
    {
      should: 'handle various finish reasons',
      geminiCandidate: {
        index: 0,
        content: { role: 'model', parts: [] },
        finishReason: 'MAX_TOKENS',
      },
      expectedOutput: {
        index: 0,
        message: { role: 'model', content: [] },
        finishReason: 'length',
        finishMessage: undefined,
        custom: { citationMetadata: undefined, safetyRatings: undefined },
      },
    },
    {
      should: 'handle SAFETY finish reason',
      geminiCandidate: {
        index: 0,
        content: { role: 'model', parts: [] },
        finishReason: 'SAFETY',
      },
      expectedOutput: {
        index: 0,
        message: { role: 'model', content: [] },
        finishReason: 'blocked',
        finishMessage: undefined,
        custom: { citationMetadata: undefined, safetyRatings: undefined },
      },
    },
    {
      should: 'handle RECITATION finish reason',
      geminiCandidate: {
        index: 0,
        content: { role: 'model', parts: [] },
        finishReason: 'RECITATION',
      },
      expectedOutput: {
        index: 0,
        message: { role: 'model', content: [] },
        finishReason: 'blocked',
        finishMessage: undefined,
        custom: { citationMetadata: undefined, safetyRatings: undefined },
      },
    },
    {
      should: 'handle OTHER finish reason',
      geminiCandidate: {
        index: 0,
        content: { role: 'model', parts: [] },
        finishReason: 'OTHER',
      },
      expectedOutput: {
        index: 0,
        message: { role: 'model', content: [] },
        finishReason: 'other',
        finishMessage: undefined,
        custom: { citationMetadata: undefined, safetyRatings: undefined },
      },
    },
    {
      should: 'should ignore empty parts',
      geminiCandidate: {
        index: 0,
        content: {
          role: 'model',
          parts: [
            {}, // this one should be skipped
            {
              text: 'Why did the dog go to the bank?\n\nTo get his bones cashed!',
            },
          ],
        },
        finishReason: 'STOP',
        safetyRatings: [
          { category: 'HARM_CATEGORY_HATE_SPEECH', probability: 'NEGLIGIBLE' },
        ],
      },
      expectedOutput: {
        index: 0,
        message: {
          role: 'model',
          content: [
            {
              text: 'Why did the dog go to the bank?\n\nTo get his bones cashed!',
            },
          ],
        },
        finishReason: 'stop',
        finishMessage: undefined,
        custom: {
          citationMetadata: undefined,
          safetyRatings: [
            {
              category: 'HARM_CATEGORY_HATE_SPEECH',
              probability: 'NEGLIGIBLE',
            },
          ],
        },
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, () => {
      const result = fromGeminiCandidate(
        test.geminiCandidate as GenerateContentCandidate
      );
      assert.deepStrictEqual(result, test.expectedOutput);
    });
  }
});

describe('toGeminiTool', () => {
  it('should convert Genkit tool to Gemini FunctionDeclaration', async () => {
    const got = toGeminiTool({
      name: 'foo',
      description: 'tool foo',
      inputSchema: toJsonSchema({
        schema: z.object({
          simpleString: z.string().describe('a string').nullable(),
          simpleNumber: z.number().describe('a number'),
          simpleBoolean: z.boolean().describe('a boolean').optional(),
          simpleArray: z.array(z.string()).describe('an array').optional(),
          simpleEnum: z
            .enum(['choice_a', 'choice_b'])
            .describe('an enum')
            .optional(),
          nestedObject: z
            .object({
              innerString: z.string(),
            })
            .describe('nested object')
            .optional(),
        }),
      }),
    });

    const want = {
      description: 'tool foo',
      name: 'foo',
      parameters: {
        properties: {
          simpleArray: {
            description: 'an array',
            items: {
              type: SchemaType.STRING,
            },
            type: SchemaType.ARRAY,
          },
          simpleBoolean: {
            description: 'a boolean',
            type: SchemaType.BOOLEAN,
          },
          simpleEnum: {
            description: 'an enum',
            enum: ['choice_a', 'choice_b'],
            type: SchemaType.STRING,
          },
          simpleNumber: {
            description: 'a number',
            type: SchemaType.NUMBER,
          },
          simpleString: {
            description: 'a string',
            nullable: true,
            type: SchemaType.STRING,
          },
          nestedObject: {
            description: 'nested object',
            type: SchemaType.OBJECT,
            properties: {
              innerString: {
                type: SchemaType.STRING,
              },
            },
            required: ['innerString'],
          },
        },
        required: ['simpleString', 'simpleNumber'],
        type: SchemaType.OBJECT,
      },
    };
    assert.deepStrictEqual(got, want);
  });

  it('should replace slashes in tool names', async () => {
    const got = toGeminiTool({
      name: 'my/tool/name',
      description: 'tool with slashes',
    });
    const want = {
      description: 'tool with slashes',
      name: 'my__tool__name',
      parameters: undefined,
    };
    assert.deepStrictEqual(got, want);
  });
});

describe('toGeminiFunctionModeEnum', () => {
  const testCases = [
    { input: undefined, expected: undefined },
    {
      input: 'MODE_UNSPECIFIED',
      expected: FunctionCallingMode.MODE_UNSPECIFIED,
    },
    { input: 'required', expected: FunctionCallingMode.ANY },
    { input: 'ANY', expected: FunctionCallingMode.ANY },
    { input: 'auto', expected: FunctionCallingMode.AUTO },
    { input: 'AUTO', expected: FunctionCallingMode.AUTO },
    { input: 'none', expected: FunctionCallingMode.NONE },
    { input: 'NONE', expected: FunctionCallingMode.NONE },
  ];

  for (const test of testCases) {
    it(`should return ${test.expected} for input '${test.input}'`, () => {
      assert.strictEqual(toGeminiFunctionModeEnum(test.input), test.expected);
    });
  }

  it('should throw for unsupported mode', () => {
    assert.throws(
      () => toGeminiFunctionModeEnum('unsupported'),
      /unsupported function calling mode: unsupported/
    );
  });
});
