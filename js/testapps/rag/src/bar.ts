import { vertexAI } from '@genkit-ai/vertexai';
import { genkit, z } from 'genkit';
import { modelRef } from 'genkit/model';

const ai = genkit({
  plugins: [vertexAI({ location: 'us-central1' })],
  model: modelRef({
    name: 'vertexai/gemini-1.5-flash',
    config: {
      temperature: 1,
    },
  }),
});

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


(async () => {
  const response = await hi({ name: 'Genkit' });
  console.log(response.text());
})()
