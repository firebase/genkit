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

import { defineModel } from '@genkit-ai/ai/model';
import z from 'zod';

import { defineTool } from '@genkit-ai/ai';
import { toToolDefinition } from '@genkit-ai/ai/tool';
import { toJsonSchema, ValidationError } from '@genkit-ai/core/schema';
import { definePrompt, prompt, Prompt } from '../src/index.js';
import { PromptMetadata } from '../src/metadata.js';

const echo = defineModel(
  { name: 'echo', supports: { tools: true } },
  async (input) => ({
    candidates: [
      { index: 0, message: input.messages[0], finishReason: 'stop' },
    ],
  })
);

function testPrompt(template, options?: Partial<PromptMetadata>): Prompt {
  return new Prompt({ name: 'test', model: echo, ...options }, template);
}

describe('Prompt', () => {
  describe('#render', () => {
    it('should render variables', async () => {
      const prompt = testPrompt(`Hello {{name}}, how are you?`);

      const rendered = await prompt.render({ input: { name: 'Michael' } });
      assert.deepStrictEqual(rendered.messages, [
        { role: 'user', content: [{ text: 'Hello Michael, how are you?' }] },
      ]);
    });

    it('should render default variables', async () => {
      const prompt = testPrompt(`Hello {{name}}, how are you?`, {
        input: { default: { name: 'Fellow Human' } },
      });

      const rendered = await prompt.render({ input: {} });
      assert.deepStrictEqual(rendered.messages, [
        {
          role: 'user',
          content: [{ text: 'Hello Fellow Human, how are you?' }],
        },
      ]);
    });
  });

  describe('#toJSON', () => {
    it('should convert zod to json schema', () => {
      const schema = z.object({ name: z.string() });

      const prompt = testPrompt(`hello {{name}}`, {
        input: { schema },
      });

      assert.deepStrictEqual(
        prompt.toJSON().input?.schema,
        toJsonSchema({ schema })
      );
    });
  });

  describe('#generate', () => {
    it('rejects input not matching the schema', async () => {
      const invalidSchemaPrompt = definePrompt(
        {
          name: 'invalidInput',
          model: 'echo',
          input: {
            jsonSchema: {
              properties: { foo: { type: 'boolean' } },
              required: ['foo'],
            },
          },
        },
        `You asked for {{foo}}.`
      );

      await assert.rejects(async () => {
        await invalidSchemaPrompt.generate({ input: { foo: 'baz' } });
      }, ValidationError);
    });

    const tinyPrompt = definePrompt(
      {
        name: 'littlePrompt',
        model: 'echo',
        input: { schema: z.any() },
      },
      `Tiny prompt`
    );

    it('includes its request in the response', async () => {
      const response = await tinyPrompt.generate({ input: {} });
      assert.notEqual(response.request, undefined);
    });

    it('does not call the model when candidates==0', async () => {
      const response = await tinyPrompt.generate({ candidates: 0, input: {} });
      assert.notEqual(response.request, undefined);
      assert.equal(response.candidates.length, 0);
    });
  });

  describe('.parse', () => {
    it('should throw a good error for invalid YAML', () => {
      assert.throws(
        () => {
          Prompt.parse(
            'example',
            `---
input: {
  isInvalid: true
  wasInvalid: true
}
---

This is the rest of the prompt`
          );
        },
        (e: any) => e.status === 'INVALID_ARGUMENT'
      );
    });

    it('should parse picoschema', () => {
      const p = Prompt.parse(
        'example',
        `---
input:
  schema:
    type: string
output:
  schema:
    name: string, the name of the person
    date?: string, ISO date like '2024-04-09'
---`
      );

      assert.deepEqual(p.input, { jsonSchema: { type: 'string' } });
      assert.deepEqual(p.output, {
        jsonSchema: {
          type: 'object',
          required: ['name'],
          additionalProperties: false,
          properties: {
            name: { type: 'string', description: 'the name of the person' },
            date: { type: 'string', description: "ISO date like '2024-04-09'" },
          },
        },
      });
    });
  });

  describe('definePrompt', () => {
    it('registers a prompt and its variant', async () => {
      definePrompt(
        {
          name: 'promptName',
          model: 'echo',
        },
        `This is a prompt.`
      );

      definePrompt(
        {
          name: 'promptName',
          variant: 'variantName',
          model: 'echo',
        },
        `And this is its variant.`
      );

      const basePrompt = await prompt('promptName');
      assert.equal('This is a prompt.', basePrompt.template);

      const variantPrompt = await prompt('promptName', {
        variant: 'variantName',
      });
      assert.equal('And this is its variant.', variantPrompt.template);
    });
  });

  it('resolves its tools when generating', async () => {
    const tool = defineTool(
      {
        name: 'testTool',
        description: 'Just a test',
        inputSchema: z.string(),
        outputSchema: z.string(),
      },
      async (input) => {
        return 'result';
      }
    );

    const prompt = definePrompt(
      {
        name: 'promptName',
        model: 'echo',
        tools: [tool],
      },
      `This is a prompt.`
    );

    const out = await prompt.generate({ input: 'test' });
    assert.deepEqual(out.request?.tools, [toToolDefinition(tool)]);
  });
});
