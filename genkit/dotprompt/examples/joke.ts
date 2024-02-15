import { googleAIModel } from '@google-genkit/providers/models';
import { PromptFile } from '../src/prompt';

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
