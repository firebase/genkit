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

import { loadPromptFile } from '@genkit-ai/dotprompt';
import similarity from 'compute-cosine-similarity';
import { generate } from 'genkit';
import { embed, EmbedderArgument } from 'genkit/embedder';
import { BaseDataPoint, Score } from 'genkit/evaluator';
import { ModelArgument } from 'genkit/model';
import path from 'path';
import * as z from 'zod';
import { getDirName } from './helper.js';

const AnswerRelevancyResponseSchema = z.object({
  question: z.string(),
  answered: z.literal(0).or(z.literal(1)),
  noncommittal: z.literal(0).or(z.literal(1)),
});

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
    const prompt = await loadPromptFile(
      path.resolve(getDirName(), '../../prompts/answer_relevancy.prompt')
    );
    const response = await generate({
      model: judgeLlm,
      config: judgeConfig,
      prompt: prompt.renderText({
        question: dataPoint.input as string,
        answer: dataPoint.output as string,
        context: dataPoint.context.join(' '),
      }),
      output: {
        schema: AnswerRelevancyResponseSchema,
      },
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
