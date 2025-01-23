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

import { ModelMiddleware, modelRef } from '@genkit-ai/ai/model';
import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import { Genkit, genkit } from '../src/genkit';
import { PromptAction, z } from '../src/index';
import {
  ProgrammableModel,
  defineEchoModel,
  defineProgrammableModel,
  defineStaticResponseModel,
} from './helpers';

const wrapRequest: ModelMiddleware = async (req, next) => {
  return next({
    ...req,
    messages: [
      {
        role: 'user',
        content: [
          {
            text:
              '(' +
              req.messages
                .map((m) => m.content.map((c) => c.text).join())
                .join() +
              ')',
          },
        ],
      },
    ],
  });
};
const wrapResponse: ModelMiddleware = async (req, next) => {
  const res = await next(req);
  return {
    message: {
      role: 'model',
      content: [
        {
          text: '[' + res.message!.content.map((c) => c.text).join() + ']',
        },
      ],
    },
    finishReason: res.finishReason,
  };
};

describe('definePrompt - functional', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
    });
    defineEchoModel(ai);
  });

  it('should apply middleware to a prompt call', async () => {
    const prompt = ai.definePrompt({
      name: 'hi',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      messages: async (input) => {
        return [
          {
            role: 'user',
            content: [{ text: `hi ${input.name}` }],
          },
        ];
      },
    });

    const response = await prompt(
      { name: 'Genkit' },
      { use: [wrapRequest, wrapResponse] }
    );
    assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
  });

  it('should apply middleware configured on a prompt', async () => {
    const prompt = ai.definePrompt({
      name: 'hi',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      use: [wrapRequest, wrapResponse],
      messages: async (input) => {
        return [
          {
            role: 'user',
            content: [{ text: `hi ${input.name}` }],
          },
        ];
      },
    });

    const response = await prompt({ name: 'Genkit' });
    assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
  });

  it('should apply middleware to a prompt call on a looked up prompt', async () => {
    ai.definePrompt({
      name: 'hi',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      use: [wrapRequest, wrapResponse],
      messages: async (input) => {
        return [
          {
            role: 'user',
            content: [{ text: `hi ${input.name}` }],
          },
        ];
      },
    });

    const prompt = ai.prompt('hi');

    const response = await prompt({ name: 'Genkit' });
    assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
  });

  it('should apply middleware configured on a prompt on a looked up prompt', async () => {
    ai.definePrompt({
      name: 'hi',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      messages: async (input) => {
        return [
          {
            role: 'user',
            content: [{ text: `hi ${input.name}` }],
          },
        ];
      },
    });

    const prompt = ai.prompt('hi');

    const response = await prompt(
      { name: 'Genkit' },
      { use: [wrapRequest, wrapResponse] }
    );
    assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
  });
});

describe('definePrompt - dotprompt', () => {
  describe('default model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({
        model: 'echoModel',
      });
      defineEchoModel(ai);
    });

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls dotprompt with default model with config', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('calls dotprompt with default model via retrieved prompt', async () => {
      ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const hi = ai.prompt('hi');

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('should apply middleware to a prompt call', async () => {
      const prompt = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await prompt(
        { name: 'Genkit' },
        { use: [wrapRequest, wrapResponse] }
      );
      assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
    });

    it('should apply middleware configured on a prompt', async () => {
      const prompt = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        use: [wrapRequest, wrapResponse],
        prompt: 'hi {{ name }}',
      });

      const response = await prompt({ name: 'Genkit' });
      assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
    });

    it('should apply middleware to a prompt call on a looked up prompt', async () => {
      ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        use: [wrapRequest, wrapResponse],
        prompt: 'hi {{ name }}',
      });

      const prompt = ai.prompt('hi');

      const response = await prompt({ name: 'Genkit' });
      assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
    });

    it('should apply middleware configured on a prompt on a looked up prompt', async () => {
      ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const prompt = ai.prompt('hi');

      const response = await prompt(
        { name: 'Genkit' },
        { use: [wrapRequest, wrapResponse] }
      );
      assert.strictEqual(response.text, '[Echo: (hi Genkit),; config: {}]');
    });
  });

  describe('default model ref', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({
        model: modelRef({
          name: 'echoModel',
        }),
      });
      defineEchoModel(ai);
    });

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('infers output schema', async () => {
      const Foo = z.object({
        bar: z.string(),
      });
      const model = defineStaticResponseModel(ai, {
        role: 'model',
        content: [
          {
            text: '```json\n{bar: "baz"}\n```',
          },
        ],
      });
      const hi = ai.definePrompt({
        name: 'hi',
        model,
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        output: {
          format: 'json',
          schema: Foo,
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      const foo = response.output;
      assert.deepStrictEqual(foo, { bar: 'baz' });
    });

    it('defaults to json format', async () => {
      const Foo = z.object({
        bar: z.string(),
      });
      const model = defineStaticResponseModel(ai, {
        role: 'model',
        content: [
          {
            text: '```json\n{bar: "baz"}\n```',
          },
        ],
      });
      const hi = ai.definePrompt({
        name: 'hi',
        model,
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        output: {
          // no format specified
          schema: Foo,
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      const foo = response.output;
      assert.deepStrictEqual(foo, { bar: 'baz' });
    });

    it('streams dotprompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        prompt: 'hi {{ name }}',
      });

      const { response, stream } = hi.stream({ name: 'Genkit' });
      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      const responseText = (await response).text;

      assert.strictEqual(
        responseText,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });

    it('calls dotprompt with default model via retrieved prompt', async () => {
      ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const hi = ai.prompt('hi');

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');

      const { stream } = hi.stream({ name: 'Genkit' });
      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });
  });

  describe('explicit model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls dotprompt with history and places it before user message', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi(
        { name: 'Genkit' },
        {
          messages: [
            { role: 'user', content: [{ text: 'hi' }] },
            { role: 'model', content: [{ text: 'bye' }] },
          ],
        }
      );
      assert.deepStrictEqual(response.messages, [
        {
          role: 'user',
          content: [{ text: 'hi' }],
        },
        {
          role: 'model',
          content: [{ text: 'bye' }],
        },
        {
          role: 'user',
          content: [{ text: 'hi Genkit' }],
        },
        {
          role: 'model',
          content: [
            { text: 'Echo: hi,bye,hi Genkit' },
            { text: '; config: {}' },
          ],
        },
      ]);
    });

    it('streams dotprompt with history and places it before user message', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi.stream(
        { name: 'Genkit' },
        {
          messages: [
            { role: 'user', content: [{ text: 'hi' }] },
            { role: 'model', content: [{ text: 'bye' }] },
          ],
        }
      );
      assert.deepStrictEqual((await response.response).messages, [
        {
          role: 'user',
          content: [{ text: 'hi' }],
        },
        {
          role: 'model',
          content: [{ text: 'bye' }],
        },
        {
          role: 'user',
          content: [{ text: 'hi Genkit' }],
        },
        {
          role: 'model',
          content: [
            { text: 'Echo: hi,bye,hi Genkit' },
            { text: '; config: {}' },
          ],
        },
      ]);
    });

    it('calls dotprompt with default model with config', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('rejects on invalid model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'modelThatDoesNotExist',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = hi({ name: 'Genkit' });
      await assert.rejects(response, {
        message: 'NOT_FOUND: Model modelThatDoesNotExist not found',
      });
    });
  });

  describe('render', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('renderes dotprompt messages', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        prompt: 'hi {{ name }}',
      });

      const response = await hi.render({ name: 'Genkit' });
      delete response.model; // ignore
      assert.deepStrictEqual(response, {
        config: {},
        docs: undefined,
        maxTurns: undefined,
        messages: [{ content: [{ text: 'hi Genkit' }], role: 'user' }],
        output: undefined,
        tools: undefined,
        returnToolRequests: undefined,
        use: undefined,
      });
    });
  });
});

describe('definePrompt', () => {
  describe('default model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({
        model: 'echoModel',
      });
      defineEchoModel(ai);
    });

    it('calls prompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls prompt with default model with config', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('calls prompt with default model via retrieved prompt', async () => {
      ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const hi = ai.prompt('hi');

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });
  });

  describe('default model ref', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({
        model: modelRef({
          name: 'echoModel',
        }),
      });
      defineEchoModel(ai);
    });

    it('calls prompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('streams prompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const { response, stream } = await hi.stream({ name: 'Genkit' });
      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      const responseText = (await response).text;

      assert.strictEqual(
        responseText,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });
  });

  describe('explicit model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('calls prompt with default model', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls prompt with default model with config', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('calls prompt with default model with call site config', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        config: {
          temperature: 11,
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi(
        { name: 'Genkit' },
        {
          config: {
            version: 'abc',
          },
        }
      );
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"version":"abc","temperature":11}'
      );
    });
  });

  describe('render', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('renders prompt', async () => {
      const hi = ai.definePrompt({
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
        messages: async (input) => {
          return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
        },
      });

      const response = await hi.render({ name: 'Genkit' });
      delete response.model; // ignore
      assert.deepStrictEqual(response, {
        config: {},
        docs: undefined,
        messages: [
          {
            content: [
              {
                text: 'hi Genkit',
              },
            ],
            role: 'user',
          },
        ],
        output: undefined,
        tools: undefined,
        maxTurns: undefined,
        returnToolRequests: undefined,
        use: undefined,
      });
    });
  });
});

describe('prompt', () => {
  let ai: Genkit;
  let pm: ProgrammableModel;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
      promptDir: './tests/prompts',
    });
    defineEchoModel(ai);
    pm = defineProgrammableModel(ai);
  });

  it('loads from from the folder', async () => {
    const testPrompt = ai.prompt('test'); // see tests/prompts folder

    const { text } = await testPrompt();

    assert.strictEqual(
      text,
      'Echo: Hello from the prompt file; config: {"temperature":11}'
    );
  });

  it('loads a varaint from from the folder', async () => {
    const testPrompt = ai.prompt('test', { variant: 'variant' }); // see tests/prompts folder

    const { text } = await testPrompt();

    assert.strictEqual(
      text,
      'Echo: Hello from a variant of the hello prompt; config: {"temperature":13}'
    );
  });

  it('returns a ref to functional prompts', async () => {
    ai.definePrompt({
      name: 'hi',
      model: 'echoModel',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      config: {
        temperature: 11,
      },
      messages: async (input) => {
        return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
      },
    });
    const testPrompt = ai.prompt('hi');
    const { text } = await testPrompt({ name: 'banana' });

    assert.strictEqual(text, 'Echo: hi banana; config: {"temperature":11}');
  });

  it('includes metadata for functional prompts', async () => {
    ai.definePrompt({
      name: 'hi',
      model: 'echoModel',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      config: {
        temperature: 0.13,
      },
      messages: async (input) => [],
    });
    const testPrompt: PromptAction =
      await ai.registry.lookupAction('/prompt/hi');

    assert.deepStrictEqual(testPrompt.__action.metadata, {
      type: 'prompt',
      prompt: {
        name: 'hi',
        model: 'echoModel',
        config: {
          temperature: 0.13,
        },
        input: {
          schema: {
            type: 'object',
            properties: {
              name: {
                type: 'string',
              },
            },
            required: ['name'],
            additionalProperties: true,
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      },
    });
  });

  it('passes in output options to the model', async () => {
    const hi = ai.definePrompt({
      name: 'hi',
      model: 'programmableModel',
      input: {
        schema: z.object({
          name: z.string(),
        }),
      },
      output: {
        schema: z.object({
          message: z.string(),
        }),
        format: 'json',
      },
      config: {
        temperature: 11,
      },
      messages: async (input) => {
        return [{ role: 'user', content: [{ text: `hi ${input.name}` }] }];
      },
    });

    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [{ text: '```json\n{"message": "hello"}\n```' }],
        },
      };
    };

    const { output } = await hi({
      name: 'Pavel',
    });

    assert.deepStrictEqual(output, { message: 'hello' });
  });
});

describe('asTool', () => {
  let ai: Genkit;
  let pm: ProgrammableModel;

  beforeEach(() => {
    ai = genkit({
      model: 'programmableModel',
      promptDir: './tests/prompts',
    });
    pm = defineProgrammableModel(ai);
  });

  it('swaps out preamble on .prompt file tool invocation', async () => {
    const session = ai.createSession({ initialState: { name: 'Genkit' } });
    const agentA = ai.definePrompt({
      name: 'agentA',
      config: { temperature: 2 },
      description: 'Agent A description',
      tools: ['toolPrompt'], // <--- defined in a .prompt file
      messages: async () => {
        return [
          {
            role: 'system',
            content: [{ text: ' agent a' }],
          },
        ];
      },
    });

    // simple hi, nothing interesting...
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [{ text: `hi ${session.state?.name} from agent a` }],
        },
      };
    };
    const chat = session.chat(agentA);
    let { text } = await chat.send('hi');
    assert.strictEqual(text, 'hi Genkit from agent a');
    assert.deepStrictEqual(pm.lastRequest, {
      config: {
        temperature: 2,
      },
      messages: [
        {
          content: [{ text: ' agent a' }],
          metadata: { preamble: true },
          role: 'system',
        },
        {
          content: [{ text: 'hi' }],
          role: 'user',
        },
      ],
      output: {},
      tools: [
        {
          name: 'toolPrompt',
          description: 'prompt in a file',
          inputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          metadata: {
            originalName: 'dotprompt/toolPrompt',
          },
        },
      ],
    });

    // transfer to toolPrompt...

    // first response be tools call, the subsequent just text response from agent b.
    let reqCounter = 0;
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [
            reqCounter++ === 0
              ? {
                  toolRequest: {
                    name: 'toolPrompt',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : { text: 'hi from agent b' },
          ],
        },
      };
    };

    ({ text } = await chat.send('pls transfer to b'));

    assert.deepStrictEqual(text, 'hi from agent b');
    assert.deepStrictEqual(pm.lastRequest, {
      config: {
        // TODO: figure out if config should be swapped out as well...
        temperature: 2,
      },
      messages: [
        {
          role: 'system',
          content: [{ text: ' Genkit toolPrompt prompt' }], // <--- NOTE: swapped out the preamble
          metadata: { preamble: true },
        },
        {
          role: 'user',
          content: [{ text: 'hi' }],
        },
        {
          role: 'model',
          content: [{ text: 'hi Genkit from agent a' }],
        },
        {
          role: 'user',
          content: [{ text: 'pls transfer to b' }],
        },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                input: {},
                name: 'toolPrompt',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: 'toolPrompt',
                output: 'transferred to toolPrompt',
                ref: 'ref123',
              },
            },
          ],
        },
      ],
      output: {},
      tools: [
        {
          name: 'agentA',
          description: 'Agent A description',
          inputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
    });

    // transfer back to to agent A...

    // first response be tools call, the subsequent just text response from agent a.
    reqCounter = 0;
    pm.handleResponse = async (req, sc) => {
      return {
        message: {
          role: 'model',
          content: [
            reqCounter++ === 0
              ? {
                  toolRequest: {
                    name: 'agentA',
                    input: {},
                    ref: 'ref123',
                  },
                }
              : { text: 'hi Genkit from agent a' },
          ],
        },
      };
    };

    ({ text } = await chat.send('pls transfer to a'));

    assert.deepStrictEqual(text, 'hi Genkit from agent a');
    assert.deepStrictEqual(pm.lastRequest, {
      config: {
        temperature: 2,
      },
      messages: [
        {
          role: 'system',
          content: [{ text: ' agent a' }], // <--- NOTE: swapped out the preamble
          metadata: { preamble: true },
        },
        {
          role: 'user',
          content: [{ text: 'hi' }],
        },
        {
          role: 'model',
          content: [{ text: 'hi Genkit from agent a' }],
        },
        {
          role: 'user',
          content: [{ text: 'pls transfer to b' }],
        },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                input: {},
                name: 'toolPrompt',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: 'toolPrompt',
                output: 'transferred to toolPrompt',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'model',
          content: [{ text: 'hi from agent b' }],
        },
        {
          role: 'user',
          content: [{ text: 'pls transfer to a' }],
        },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                input: {},
                name: 'agentA',
                ref: 'ref123',
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: 'agentA',
                output: 'transferred to agentA',
                ref: 'ref123',
              },
            },
          ],
        },
      ],
      output: {},
      tools: [
        {
          description: 'prompt in a file',
          inputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          name: 'toolPrompt',
          outputSchema: {
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          metadata: {
            originalName: 'dotprompt/toolPrompt',
          },
        },
      ],
    });
  });
});
