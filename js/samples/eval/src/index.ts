import { initializeGenkit } from '@google-genkit/common/config';
import {
  RagasDataPointZodType,
  RagasMetric,
  ragasRef,
} from '@google-genkit/plugin-ragas';

import config from './genkit.conf';
import { Dataset, evaluate } from '@google-genkit/ai/evaluators';

initializeGenkit(config);

const samples: Dataset<RagasDataPointZodType> = [
  {
    input: 'Who is SpongeBob?',
    context: [
      'SpongeBob loves his friends Patrick and Sandy Cheeks',
      'SpongeBob is a sea sponge who lives in a pineapple',
    ],
    output: 'Spongebob is a sea sponge',
  },
  {
    input: 'Why can Spongebob absorb liquids?',
    context: [
      'SpongeBob can soak liquids because he is a sea sponge',
      'SpongeBob has a pet snail',
    ],
    output: 'Spongebob is a sea sponge',
  },
  {
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
    evaluator: ragasRef(RagasMetric.ANSWER_RELEVANCY),
    dataset: samples,
  });
  console.log(JSON.stringify(scores));
}

main();
