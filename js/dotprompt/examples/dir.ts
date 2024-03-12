import { loadPromptDir } from '../src/index';
import { useGoogleAI } from '@genkit-ai/providers/google-ai';

useGoogleAI();

const prompts = loadPromptDir('./examples/prompts');

prompts.joke
  .generate({ subject: process.argv[2] }, { variant: process.argv[3] })
  .then((result) => console.log("Here'a a joke:", result.text()))
  .catch(console.error);
