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

import {
  BaseDataPoint,
  defineEvaluator,
  EvaluatorAction,
} from 'genkit/evaluator';
import { ModelReference } from 'genkit/model';
import * as z from 'zod';
import { ByoMetric } from '..';
import { deliciousnessScore } from './deliciousness';

export const DELICIOUSNESS: ByoMetric = {
  name: 'deliciousness',
};

/**
 * Create the Deliciousness evaluator.
 */
export function createDeliciousnessEvaluator<
  ModelCustomOptions extends z.ZodTypeAny,
>(
  judge: ModelReference<ModelCustomOptions>,
  judgeConfig: z.infer<ModelCustomOptions>
): EvaluatorAction {
  return defineEvaluator(
    {
      name: `byo/${DELICIOUSNESS.name}`,
      displayName: 'Deliciousness',
      definition: 'Determines if output is considered delicous.',
    },
    async (datapoint: BaseDataPoint) => {
      const score = await deliciousnessScore(judge, datapoint, judgeConfig);
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: score,
      };
    }
  );
}
