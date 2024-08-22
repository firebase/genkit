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

import { generate } from '@genkit/ai';
import { BaseDataPoint, Score } from '@genkit/ai/evaluator';
import { ModelArgument } from '@genkit/ai/model';
import { loadPromptFile } from '@genkit/dotprompt';
import path from 'path';
import * as z from 'zod';
import { getDirName } from './helper.js';

const LongFormResponseSchema = z.object({ statements: z.array(z.string()) });

const NliResponseBaseSchema = z.object({
  statement: z.string(),
  reason: z.string(),
  verdict: z.union([z.literal(0), z.literal(1)]),
});

type NliResponseBase = z.infer<typeof NliResponseBaseSchema>;
const NliResponseSchema = z.union([
  NliResponseBaseSchema,
  z.array(NliResponseBaseSchema),
]);

/**
 *
 */
export async function faithfulnessScore<
  CustomModelOptions extends z.ZodTypeAny,
>(
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseDataPoint,
  judgeConfig?: CustomModelOptions
): Promise<Score> {
  try {
    const { input, output, context } = dataPoint;
    if (!context?.length) {
      throw new Error('Context was not provided');
    }
    if (!output) {
      throw new Error('Output was not provided');
    }
    const longFormPrompt = await loadPromptFile(
      path.resolve(getDirName(), '../../prompts/faithfulness_long_form.prompt')
    );
    const longFormResponse = await generate({
      model: judgeLlm,
      config: judgeConfig,
      prompt: longFormPrompt.renderText({
        question: input as string,
        answer: output as string,
      }),
      output: {
        schema: LongFormResponseSchema,
      },
    });
    const parsedLongFormResponse = longFormResponse.output();
    let statements = parsedLongFormResponse?.statements ?? [];
    if (statements.length === 0) {
      throw new Error('No statements returned');
    }
    const allStatements = statements.map((s) => `statement: ${s}`).join('\n');
    const allContext = context.join('\n');
    const nliPrompt = await loadPromptFile(
      path.resolve(getDirName(), '../../prompts/faithfulness_nli.prompt')
    );
    const response = await generate({
      model: judgeLlm,
      prompt: nliPrompt.renderText({
        context: allContext,
        statements: allStatements,
      }),
      output: {
        schema: NliResponseSchema,
      },
    });
    const parsedResponse = response.output();
    return nliResponseToScore(parsedResponse);
  } catch (err) {
    console.debug(
      `Genkit faithfulness evaluation failed with error ${err} for sample ${JSON.stringify(
        dataPoint
      )}`
    );
    throw err;
  }
}

function nliResponseToScore(
  input: NliResponseBase[] | NliResponseBase | null
): Score {
  if (!input) {
    throw new Error(`Evaluator response empty`);
  }
  let responses: NliResponseBase[];
  responses = Array.isArray(input) ? input : [input];
  const faithfulStatements = responses.reduce((total, resp) => {
    return total + resp.verdict;
  }, 0);
  return {
    score: faithfulStatements / responses.length,
    details: { reasoning: responses.map((r) => r.reason).join('; ') },
  };
}
