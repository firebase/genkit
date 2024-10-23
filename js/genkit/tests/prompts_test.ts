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

import { modelRef } from '@genkit-ai/ai/model';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { Genkit, genkit } from '../src/genkit';
import { z } from '../src/index';
import { defineEchoModel, defineStaticResponseModel } from './helpers';

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
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        'hi {{ name }}'
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls dotprompt with default model with config', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        'hi {{ name }}'
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('calls dotprompt with .generate', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        'hi {{ name }}'
      );

      const response = await hi.generate({
        input: { name: 'Genkit' },
        config: { version: 'abc' },
      });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"version":"abc","temperature":11}'
      );
    });

    it('calls dotprompt with default model via retrieved prompt', async () => {
      ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        'hi {{ name }}'
      );

      const hi = await ai.prompt('hi');

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

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        'hi {{ name }}'
      );

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
      const hi = ai.definePrompt(
        {
          name: 'hi',
          model,
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          output: {
            schema: Foo,
          },
        },
        'hi {{ name }}'
      );

      const response = await hi({ name: 'Genkit' });
      const foo: z.infer<typeof Foo> = response.output;
      assert.deepStrictEqual(foo, { bar: 'baz' });
    });

    it('streams dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        'hi {{ name }}'
      );

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

    it('streams dotprompt .generateStream', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        'hi {{ name }}'
      );

      const { response, stream } = await hi.generateStream({
        input: { name: 'Genkit' },
        config: { version: 'abc' },
      });
      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      const responseText = (await response).text;

      assert.strictEqual(
        responseText,
        'Echo: hi Genkit; config: {"version":"abc","temperature":11}'
      );
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });

    it('calls dotprompt with default model via retrieved prompt', async () => {
      ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        'hi {{ name }}'
      );

      const hi = await ai.prompt('hi');

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });
  });

  describe('explicit model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          model: 'echoModel',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        'hi {{ name }}'
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls dotprompt with default model with config', async () => {
      const hi = ai.definePrompt(
        {
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
        },
        'hi {{ name }}'
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });
  });

  describe('render', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('renderes dotprompt messages', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        'hi {{ name }}'
      );

      const response = await hi.render({ input: { name: 'Genkit' } });
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
        output: {
          format: 'text',
          jsonSchema: undefined,
        },
        tools: [],
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

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls dotprompt with default model with config', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('calls dotprompt with default model via retrieved prompt', async () => {
      ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const hi = await ai.prompt('hi');

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

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('streams dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

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

    it('calls dotprompt with default model', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          model: 'echoModel',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('calls dotprompt with default model with config', async () => {
      const hi = ai.definePrompt(
        {
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
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi({ name: 'Genkit' });
      assert.strictEqual(
        response.text,
        'Echo: hi Genkit; config: {"temperature":11}'
      );
    });

    it('calls dotprompt with default model with call site config', async () => {
      const hi = ai.definePrompt(
        {
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
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

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

    it('works with .generate', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          model: 'echoModel',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi.generate({ input: { name: 'Genkit' } });
      assert.strictEqual(response.text, 'Echo: hi Genkit; config: {}');
    });

    it('streams dotprompt with .generateStream', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
          config: {
            temperature: 11,
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const { response, stream } = await hi.generateStream({
        model: 'echoModel',
        input: { name: 'Genkit' },
        config: { version: 'abc' },
      });
      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      const responseText = (await response).text;

      assert.strictEqual(
        responseText,
        'Echo: hi Genkit; config: {"version":"abc","temperature":11}'
      );
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });
  });

  describe('render', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('renders prompt', async () => {
      const hi = ai.definePrompt(
        {
          name: 'hi',
          model: 'echoModel',
          input: {
            schema: z.object({
              name: z.string(),
            }),
          },
        },
        async (input) => {
          return {
            messages: [
              { role: 'user', content: [{ text: `hi ${input.name}` }] },
            ],
          };
        }
      );

      const response = await hi.render({ input: { name: 'Genkit' } });
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
      });
    });
  });
});

describe('prompt', () => {
  let ai: Genkit;

  beforeEach(() => {
    ai = genkit({
      model: 'echoModel',
      promptDir: './tests/prompts',
    });
    defineEchoModel(ai);
  });

  it('loads from from the folder', async () => {
    const testPrompt = await ai.prompt('test'); // see tests/prompts folder

    const { text } = await testPrompt();

    assert.strictEqual(
      text,
      'Echo: Hello from the prompt file; config: {"temperature":11}'
    );
  });

  it('returns a ref to functional prompts', async () => {
    ai.definePrompt(
      {
        name: 'hi',
        model: 'echoModel',
        input: {
          schema: z.object({
            name: z.string(),
          }),
        },
      },
      async (input) => {
        return {
          messages: [{ role: 'user', content: [{ text: `hi ${input.name}` }] }],
          config: {
            temperature: 11,
          },
        };
      }
    );
    const testPrompt = await ai.prompt('hi');
    const { text } = await testPrompt({ name: 'banana' });

    assert.strictEqual(text, 'Echo: hi banana; config: {"temperature":11}');
  });
});
