import { genkit } from 'genkit';
import { googleAI, gemini15Flash } from '@genkit-ai/googleai'

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

(async () => {
  const { text } = await ai.generate('hi');
  console.log(text);
})();
