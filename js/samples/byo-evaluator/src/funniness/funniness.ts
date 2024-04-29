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

const QUESTION_GEN_PROMPT = `You are a joke critic with a wide range in your taste for jokes. Given the output, decide if it is a joke and then decide if that joke is funny and provide your reasoning. Use the following categories as a verdict in the response FUNNY_JOKE, NOT_FUNNY_JOKE, OFFENSIVE_JOKE, NOT_A_JOKE.

Here is an example of an output that is a funny joke:

Output:
Why did the scarecrow win an award? Because he was outstanding in his field!
Response:
{ "reason": "This is a classic, simple joke with a play on words that's likely to elicit a chuckle.", "verdict":"FUNNY"}

Here is an example of an output that is not a funny joke:

Output:
Why did the chicken cross the road? To get to the other side!
Response:
{ "reason": "This is a classic joke that is not funny because it has been overused. It might elicit a sigh or a sarcastic haha.", "verdict":"NOT_FUNNY"}

Here is an example of an output that is an offensive joke:

Output:
What's the difference between a pizza and a politician? A pizza can feed a family of four.
Response:
{ "reason": "This joke targets a specific group (politicians) and makes a negative generalization about them. It could be considered offensive because it's mean-spirited and relies on a stereotype.", "verdict": "OFFENSIVE_JOKE"}

Here is an example of an output that is not a joke:

Output:
The quick brown fox jumps over the lazy dog.
Response:
{ "reason": "This output is a statement with no intent to be funny", "verdict": "NOT_A_JOKE"}

Here is a new submission to assess:

Output:
{{output}}
Response:
`;

const FUNNINESS_VALUES = [
  'FUNNY_JOKE',
  'NOT_FUNNY_JOKE',
  'OFFENSIVE_JOKE',
  'NOT_A_JOKE',
] as const;

const FunninessResponseSchema = z.object({
  reason: z.string(),
  verdict: z.enum(FUNNINESS_VALUES),
});

type FunninessResponse = z.infer<typeof FunninessResponseSchema>;

export async function funninessScore<CustomModelOptions extends z.ZodTypeAny>(
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseDataPoint,
  judgeConfig?: z.infer<CustomModelOptions>
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
    const parsedResponse = extractJson<FunninessResponse>(response.text());
    if (!parsedResponse) {
      throw new Error(`Unable to parse evaluator response: ${response.text()}`);
    }
    return {
      score: parsedResponse.verdict,
      details: { reasoning: parsedResponse.reason },
    };
  } catch (err) {
    console.debug(
      `BYO funniness evaluation failed with error ${err} for sample ${JSON.stringify(
        d
      )}`
    );
    throw err;
  }
}
