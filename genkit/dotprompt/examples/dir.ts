import { loadPromptDir } from '../src/index.js';
import { useGoogleAI } from '@google-genkit/providers/models';

useGoogleAI();

const prompts = loadPromptDir('./examples/prompts');

prompts.joke
  .generate({ subject: process.argv[2] }, { variant: process.argv[3] })
  .then((result) => console.log("Here'a a joke:", result.text()));
