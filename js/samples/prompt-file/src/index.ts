/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { prompt } from '@genkit-ai/dotprompt';
import { initializeGenkit } from '@genkit-ai/common/config';

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
