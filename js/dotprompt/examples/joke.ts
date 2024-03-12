import { PromptFile } from '../src/prompt';
import { googleAIModel } from '@genkit-ai/providers/google-ai';

googleAIModel('gemini-pro');

PromptFile.loadFile('./examples/joke.prompt')
  .generate({
    subject: 'working late on a Friday',
    style: 'Rodney Dangerfield',
  })
  .then((result) => {
    console.log(result.text());
  })
  .catch(console.error);
