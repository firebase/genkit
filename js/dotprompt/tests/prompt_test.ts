import assert from 'node:assert';
import { describe, it } from 'node:test';

import { defineModel } from '@genkit-ai/ai/model';
import z from 'zod';

import zodToJsonSchema from 'zod-to-json-schema';
import { Prompt } from '../src';
import { PromptMetadata } from '../src/metadata';

const echo = defineModel({ name: 'echo' }, async (input) => ({
  candidates: [{ index: 0, message: input.messages[0], finishReason: 'stop' }],
}));

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
        zodToJsonSchema(schema)
      );
    });
  });
});
