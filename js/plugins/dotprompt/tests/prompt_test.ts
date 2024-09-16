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
import { toJsonSchema, ValidationError } from '@genkit-ai/core/schema';
import z from 'zod';
import { registerPluginProvider } from '../../../core/src/registry.js';
import { defineJsonSchema, defineSchema } from '../../../core/src/schema.js';
import { defineDotprompt, Dotprompt, prompt, promptRef } from '../src/index.js';
import { PromptMetadata } from '../src/metadata.js';

function registerDotprompt() {
  registerPluginProvider('dotprompt', {
    name: 'dotprompt',
    async initializer() {
      return {};
    },
  });
}

const echo = defineModel(
  { name: 'echo', supports: { tools: true } },
  async (input) => ({
    candidates: [
      { index: 0, message: input.messages[0], finishReason: 'stop' },
    ],
  })
);

function testPrompt(template, options?: Partial<PromptMetadata>): Dotprompt {
  return new Dotprompt({ name: 'test', model: echo, ...options }, template);
}

describe('Prompt', () => {
  describe('#render', () => {
    it('should render variables', async () => {
      const prompt = testPrompt(`Hello {{name}}, how are you?`);

      const rendered = await prompt.render({ input: { name: 'Michael' } });
      assert.deepStrictEqual(rendered.prompt, [
        { text: 'Hello Michael, how are you?' },
      ]);
    });

    it('should render default variables', async () => {
      const prompt = testPrompt(`Hello {{name}}, how are you?`, {
        input: { default: { name: 'Fellow Human' } },
      });

      const rendered = await prompt.render({ input: {} });
      assert.deepStrictEqual(rendered.prompt, [
        {
          text: 'Hello Fellow Human, how are you?',
        },
      ]);
    });

    it('rejects input not matching the schema', async () => {
      registerDotprompt();
      const invalidSchemaPrompt = defineDotprompt(
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
        await invalidSchemaPrompt.render({ input: { foo: 'baz' } });
      }, ValidationError);
    });

    it('should render with overridden fields', async () => {
      const prompt = testPrompt(`Hello {{name}}, how are you?`);

      const streamingCallback = (c) => console.log(c);

      const rendered = await prompt.render({
        input: { name: 'Michael' },
        streamingCallback,
        returnToolRequests: true,
      });
      assert.strictEqual(rendered.streamingCallback, streamingCallback);
      assert.strictEqual(rendered.returnToolRequests, true);
    });
  });

  describe('#generate', () => {
    it('renders and calls the model', async () => {
      const prompt = testPrompt(`Hello {{name}}, how are you?`);
      const response = await prompt.generate({ input: { name: 'Bob' } });
      assert.equal(response.text(), `Hello Bob, how are you?`);
    });

    it('rejects input not matching the schema', async () => {
      registerDotprompt();
      const invalidSchemaPrompt = defineDotprompt(
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

  describe('.parse', () => {
    it('should throw a good error for invalid YAML', () => {
      assert.throws(
        () => {
          Dotprompt.parse(
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
      const p = Dotprompt.parse(
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
            date: {
              type: ['string', 'null'],
              description: "ISO date like '2024-04-09'",
            },
          },
        },
      });
    });

    it('should use registered schemas', () => {
      const MyInput = defineSchema('MyInput', z.number());
      defineJsonSchema('MyOutput', { type: 'boolean' });

      const p = Dotprompt.parse(
        'example2',
        `---
input:
  schema: MyInput
output:
  schema: MyOutput
---`
      );

      assert.deepEqual(p.input, { schema: MyInput });
      assert.deepEqual(p.output, { jsonSchema: { type: 'boolean' } });
    });
  });

  describe('defineDotprompt', () => {
    it('registers a prompt and its variant', async () => {
      registerDotprompt();
      defineDotprompt(
        {
          name: 'promptName',
          model: 'echo',
        },
        `This is a prompt.`
      );

      defineDotprompt(
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
});

describe('DotpromptRef', () => {
  it('Should load a prompt correctly', async () => {
    registerDotprompt();
    defineDotprompt(
      {
        name: 'promptName',
        model: 'echo',
      },
      `This is a prompt.`
    );

    const ref = promptRef('promptName');

    const p = await ref.loadPrompt();

    const isDotprompt = p instanceof Dotprompt;

    assert.equal(isDotprompt, true);
    assert.equal(p.template, 'This is a prompt.');
  });

  it('Should generate output correctly using DotpromptRef', async () => {
    registerDotprompt();
    defineDotprompt(
      {
        name: 'generatePrompt',
        model: 'echo',
      },
      `Hello {{name}}, this is a test prompt.`
    );

    const ref = promptRef('generatePrompt');
    const response = await ref.generate({ input: { name: 'Alice' } });

    assert.equal(response.text(), 'Hello Alice, this is a test prompt.');
  });

  it('Should render correctly using DotpromptRef', async () => {
    registerDotprompt();
    defineDotprompt(
      {
        name: 'renderPrompt',
        model: 'echo',
      },
      `Hi {{name}}, welcome to the system.`
    );

    const ref = promptRef('renderPrompt');
    const rendered = await ref.render({ input: { name: 'Bob' } });

    assert.deepStrictEqual(rendered.prompt, [
      { text: 'Hi Bob, welcome to the system.' },
    ]);
  });

  it('Should handle invalid schema input in DotpromptRef', async () => {
    registerDotprompt();
    defineDotprompt(
      {
        name: 'invalidSchemaPromptRef',
        model: 'echo',
        input: {
          jsonSchema: {
            properties: { foo: { type: 'boolean' } },
            required: ['foo'],
          },
        },
      },
      `This is the prompt with foo={{foo}}.`
    );

    const ref = promptRef('invalidSchemaPromptRef');

    await assert.rejects(async () => {
      await ref.generate({ input: { foo: 'not_a_boolean' } });
    }, ValidationError);
  });

  it('Should support streamingCallback in DotpromptRef', async () => {
    registerDotprompt();
    defineDotprompt(
      {
        name: 'streamingCallbackPrompt',
        model: 'echo',
      },
      `Hello {{name}}, streaming test.`
    );

    const ref = promptRef('streamingCallbackPrompt');

    const streamingCallback = (chunk) => console.log(chunk);
    const options = {
      input: { name: 'Charlie' },
      streamingCallback,
      returnToolRequests: true,
    };

    const rendered = await ref.render(options);

    assert.strictEqual(rendered.streamingCallback, streamingCallback);
    assert.strictEqual(rendered.returnToolRequests, true);
  });

  it('Should cache loaded prompt in DotpromptRef', async () => {
    registerDotprompt();
    defineDotprompt(
      {
        name: 'cacheTestPrompt',
        model: 'echo',
      },
      `This is a prompt for cache test.`
    );

    const ref = promptRef('cacheTestPrompt');
    const firstLoad = await ref.loadPrompt();
    const secondLoad = await ref.loadPrompt();

    assert.strictEqual(
      firstLoad,
      secondLoad,
      'Loaded prompts should be identical (cached).'
    );
  });
});
