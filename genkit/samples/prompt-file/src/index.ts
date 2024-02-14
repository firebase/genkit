import { loadPromptFile } from '@google-genkit/dotprompt';
import { initializeGenkit } from '@google-genkit/common/config';

initializeGenkit();

const recipePrompt = loadPromptFile('./recipe.prompt');

recipePrompt
  .generate({ food: process.argv[2] || 'mexican asian fusion' })
  .then((result) => {
    console.log(result.output());
    process.exit(0); // TODO: figure out why process hangs
  });
