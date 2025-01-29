import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
});

const prompt = ai.definePrompt(
  {
    name: 'Character Prompt',
    model: gemini15Flash,
    input: {
      schema: z.object({
        inspiration: z.string(),
      }),
    },
    output: {
      format: 'json',
      schema: z.object({
        name: z.string(),
        strength: z.number(),
        intelligence: z.number(),
        description: z.string(),
      }),
    },
  },
  `
You're a expert DnD designer, create a new character.

Base the character on {{inspiration}} but don't make it
and exact match.
`
);

(async () => {
  console.log((await prompt({ inspiration: 'Yogi Berra' })).output);
})();
