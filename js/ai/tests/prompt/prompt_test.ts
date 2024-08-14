import assert from 'node:assert';
import { describe, it } from 'node:test';
import * as z from 'zod';
import { definePrompt, renderPrompt } from '../../src/prompt.ts';

describe('prompt', () => {
  describe('render()', () => {
    it('respects output schema in the definition', async () => {
      const schema1 = z.object({
        puppyName: z.string({ description: 'A cute name for a puppy' }),
      });
      const prompt1 = definePrompt(
        {
          name: 'prompt1',
          inputSchema: z.string({ description: 'Dog breed' }),
        },
        async (breed) => {
          return {
            messages: [
              {
                role: 'user',
                content: [{ text: `Pick a name for a ${breed} puppy` }],
              },
            ],
            output: {
              format: 'json',
              schema: schema1,
            },
          };
        }
      );
      const generateRequest = await renderPrompt({
        prompt: prompt1,
        input: 'poodle',
        model: 'geminiPro',
      });
      assert.equal(generateRequest.output?.schema, schema1);
    });
  });
});
