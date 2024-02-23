import { prompt } from '@google-genkit/dotprompt';
import { initializeGenkit } from '@google-genkit/common/config';

initializeGenkit();

(async () => {
  const food = process.argv[2] || 'mexican asian fusion';
  const recipePrompt = await prompt('recipe');

  const result = await recipePrompt.generate({
    variables: { food },
  });

  console.log(result.output());

  console.log('');
  console.log('Now, as a robot...');
  const robotPrompt = await prompt('recipe', { variant: 'robot' });

  const result2 = await robotPrompt.generate({
    variables: { food },
  });

  console.log(result2.output());
})();
