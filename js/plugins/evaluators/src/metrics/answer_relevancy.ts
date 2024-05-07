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

import { generate } from '@genkit-ai/ai';
import { embed, EmbedderArgument } from '@genkit-ai/ai/embedder';
import { BaseDataPoint, Score } from '@genkit-ai/ai/evaluator';
import { ModelArgument } from '@genkit-ai/ai/model';
import { defineDotprompt, loadPromptFile } from '@genkit-ai/dotprompt';
import similarity from 'compute-cosine-similarity';
import path from 'path';
import * as z from 'zod';

const AnswerRelevancyResponseSchema = z.object({
  question: z.string(),
  answered: z.literal(0).or(z.literal(1)),
  noncommittal: z.literal(0).or(z.literal(1)),
});

const QUESTION_GEN_PROMPT = defineDotprompt(
  {
    input: {
      schema: z.object({
        question: z.string(),
        answer: z.string(),
        context: z.string(),
      }),
    },
    output: {
      schema: AnswerRelevancyResponseSchema,
    },
  },
  `Assess whether the generated output is relevant to the question asked.

To accomplish this perform the following 3 tasks in a step by step manner:
1. Identify if the question is noncommittal. A noncommittal answer is one that is evasive, vague, or ambiguous. For example, "I don't know", "I'm not sure", and "I can't answer" are noncommittal answers. Give a score of 1 if the answer is noncommittal and 0 if it is committal.
2. Assess whether the answer provided addresses the question posed. If the answer is similar in subject matter but doesn't answer the question posed, that is not satisfactory. Give a score of 1 for a satisfactory answer and 0 if it is not satisfactory.
3. Generate a question that could produce the provided answer. Use only the information in the provided answer.

Format the answer as json in the following manner where task 1 is assigned to the "noncommittal" field, task 2 is assigned to the "answered" field, and task 3 is assigned to the "question" field.

Here are some examples:

Question:
In what country was Albert Einstein born?
Context:
Albert Einstein was a German-born theoretical physicist who is widely held to be one of the greatest and most influential scientists of all time
Answer:
Albert Einstein was born in Germany.
Output:
{"noncommittal":0, "answered": 1, "question":"Where was Albert Einstein born?"}


Question:
Are there any frogs that can change their skin color like chameleons?
Context:
A recent scientific study has discovered a new species of frog in the Amazon rainforest that has the unique ability to change its skin color based on the temperature of its environment.
Answer:
It can change its skin color based on the temperature of its environment.
Output:
{"noncommittal":0, "answered":0, "question":"What unique ability does the newly discovered species of frog have?"}

Question:
What is the tallest mountain?
Context:
The tallest mountain on Earth, measured from sea level, is a renowned peak located in the Himalayas.
Answer:
Everest
Output:
{"noncommittal":0, "answered":1, "question":"What is the tallest mountain on Earth?"}


Question:
Where there any groundbreaking new features announced for new smartphones in 2023?
Answer:
I don't know about the  groundbreaking feature of the smartphone invented in 2023 as am unware of information beyong 2022. 
Context:
In 2023, a groundbreaking invention was announced: a smartphone with a battery life of one month, revolutionizing the way people use mobile technology.
Output:
{"noncommittal":1, "answered":0, "question":"What was the groundbreaking feature of the smartphone invented in 2023?"}

Now provide your analysis for the following inputs. DO NOT PROVIDE ANY MORE EXAMPLES. Your response must be a valid JSON like you see above.

Question:
{{question}}
Answer:
{{answer}}
Context:
{{context}}
Output:
`
);

export async function answerRelevancyScore<
  CustomModelOptions extends z.ZodTypeAny,
  CustomEmbedderOptions extends z.ZodTypeAny,
>(
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseDataPoint,
  embedder: EmbedderArgument<CustomEmbedderOptions>,
  judgeConfig?: CustomModelOptions,
  embedderOptions?: z.infer<CustomEmbedderOptions>
): Promise<Score> {
  try {
    if (!dataPoint.context?.length) {
      throw new Error('Context was not provided');
    }
    if (!dataPoint.output) {
      throw new Error('Output was not provided');
    }
    const prompt = await loadPromptFile(path.resolve(__dirname, "../../prompts/answer_relevancy.prompt"))
    const response = await generate({
      model: judgeLlm,
      config: judgeConfig,
      prompt: prompt.renderText({
        question: dataPoint.input as string,
        answer: dataPoint.output as string,
        context: dataPoint.context.join(' '),
      }),
    });
    const genQuestion = response.output()?.question;
    if (!genQuestion)
      throw new Error('Error generating question for answer relevancy');

    const questionEmbed = await embed({
      embedder,
      content: dataPoint.input as string,
      options: embedderOptions,
    });
    const genQuestionEmbed = await embed({
      embedder,
      content: genQuestion,
      options: embedderOptions,
    });
    const score = cosineSimilarity(questionEmbed, genQuestionEmbed);
    const answered = response.output()?.answered === 1;
    const isNonCommittal = response.output()?.noncommittal === 1;
    const answeredPenalty = !answered ? 0.5 : 0;
    const adjustedScore =
      score - answeredPenalty < 0 ? 0 : score - answeredPenalty;
    const reasoning = isNonCommittal
      ? 'Noncommittal'
      : answered
        ? 'Cosine similarity'
        : 'Cosine similarity with penalty for insufficient answer';
    return {
      score: adjustedScore * (isNonCommittal ? 0 : 1),
      details: {
        reasoning,
      },
    };
  } catch (err) {
    console.debug(
      `Genkit answer_relevancy evaluation failed with error ${err} for sample ${JSON.stringify(
        dataPoint
      )}`
    );
    throw err;
  }
}

function cosineSimilarity(v1: Array<number>, v2: Array<number>) {
  const maybeScore = similarity(v1, v2);
  if (!maybeScore) {
    throw new Error('Unable to compute cosine similarity');
  }
  return Math.abs(maybeScore);
}
