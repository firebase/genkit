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
import { BaseDataPoint, Score } from '@genkit-ai/ai/evaluator';
import { extractJson } from '@genkit-ai/ai/extract';
import { ModelArgument } from '@genkit-ai/ai/model';
import Handlebars from 'handlebars';
import * as z from 'zod';

const QUESTION_GEN_PROMPT = `You are a food critic with a wide range in taste. Given the output, decide if it sounds delicious and provide your reasoning. Use only "yes" (if delicous), "no" (if not delicious), "maybe" (if you can't decide) as the verdict.

Here are a few examples:

Output:
Chicken parm sandwich
Response:
{ "reason": "This is a classic sandwich enjoyed by many - totally delicious", "verdict":"yes"}

Output:
Boston logan international airport tarmac
Response:
{ "reason": "This is not edible and definitely not delicious.", "verdict":"no"}

Output:
A juicy peice of gossip
Response:
{ "reason": "Gossip is sometimes metaphorically referred to as tasty.", "verdict":"maybe"}

Here is a new submission to assess:

Output:
{{output}}
Response:
`;

const DELICIOUSNESS_VALUES = ['yes', 'no', 'maybe'] as const;

const DeliciousnessDetectionResponseSchema = z.object({
  reason: z.string(),
  verdict: z.enum(DELICIOUSNESS_VALUES),
});

type DeliciousnessDetectionResponse = z.infer<
  typeof DeliciousnessDetectionResponseSchema
>;

export async function deliciousnessScore<
  CustomModelOptions extends z.ZodTypeAny,
>(
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseDataPoint,
  judgeConfig?: CustomModelOptions
): Promise<Score> {
  const d = dataPoint;
  try {
    if (!d.output) {
      throw new Error('Output is required for Funniness detection');
    }
    const promptTemplate = Handlebars.compile(QUESTION_GEN_PROMPT);
    const finalPrompt = promptTemplate({
      output: d.output,
    });

    const response = await generate({
      model: judgeLlm,
      prompt: finalPrompt,
      config: judgeConfig,
    });
    const parsedResponse = extractJson<DeliciousnessDetectionResponse>(
      response.text()
    );
    if (!parsedResponse) {
      throw new Error(`Unable to parse evaluator response: ${response.text()}`);
    }
    return {
      score: parsedResponse.verdict,
      details: { reasoning: parsedResponse.reason },
    };
  } catch (err) {
    console.debug(
      `BYO deliciousness evaluation failed with error ${err} for sample ${JSON.stringify(
        d
      )}`
    );
    throw err;
  }
}
