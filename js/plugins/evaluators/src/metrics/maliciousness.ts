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

const MaliciousnessResponseSchema = z.object({
  reason: z.string(),
  verdict: z.boolean(),
});

export async function maliciousnessScore<
  CustomModelOptions extends z.ZodTypeAny,
>(
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseDataPoint,
  judgeConfig?: CustomModelOptions
): Promise<Score> {
  const d = dataPoint;
  try {
    if (!d.input || !d.output) {
      throw new Error('input and output are required');
    }

    const prompt = await loadPromptFile(
      path.resolve(getDirName(), '../../prompts/maliciousness.prompt')
    );
    //TODO: safetySettings are gemini specific - pull these out so they are tied to the LLM
    const response = await generate({
      model: judgeLlm,
      config: judgeConfig,
      prompt: prompt.renderText({
        input: d.input as string,
        submission: d.output as string,
      }),
      output: {
        schema: MaliciousnessResponseSchema,
      },
    });
    const parsedResponse = response.output();
    if (!parsedResponse) {
      throw new Error(`Unable to parse evaluator response: ${response.text()}`);
    }
    return {
      score: 1.0 * (parsedResponse.verdict ? 1 : 0),
      details: { reasoning: parsedResponse.reason },
    };
  } catch (err) {
    console.debug(
      `Genkit answer relevancy evaluation failed with error ${err} for sample ${JSON.stringify(
        d
      )}`
    );
    throw err;
  }
}
