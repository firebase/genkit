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

import { initializeGenkit } from '@genkit-ai/common/config';
import { RagasMetric, ragasRef } from '@genkit-ai/plugin-ragas';

import { Dataset, evaluate } from '@genkit-ai/ai/evaluators';
import config from './genkit.conf';

initializeGenkit(config);

const samples: Dataset = [
  {
    testCaseId: 'who_is_spongebob',
    input: 'Who is SpongeBob?',
    context: [
      'SpongeBob loves his friends Patrick and Sandy Cheeks',
      'SpongeBob is a sea sponge who lives in a pineapple',
    ],
    output: 'Spongebob is a sea sponge',
  },
  {
    testCaseId: 'why_absorbancy',
    input: 'Why can Spongebob absorb liquids?',
    context: [
      'SpongeBob can soak liquids because he is a sea sponge',
      'SpongeBob has a pet snail',
    ],
    output: 'Spongebob is a sea sponge',
  },
  {
    testCaseId: 'first_aired',
    input: 'When was SpongeBob first aired?',
    context: [
      'SpongeBob loves his friends Patrick and Sandy Cheeks',
      'SpongeBob is a sea sponge who lives in a pineapple',
    ],
    output: 'Spongebob was aired on April 1, 1999',
  },
];

async function main() {
  console.log('running ragas eval...');
  const scores = await evaluate({
    evaluator: ragasRef(RagasMetric.FAITHFULNESS),
    dataset: samples,
  });
  console.log(JSON.stringify(scores));
}

main();
