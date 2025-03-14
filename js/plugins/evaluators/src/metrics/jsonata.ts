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

import { BaseEvalDataPoint, EvalStatusEnum, Score } from 'genkit/evaluator';
import jsonata from 'jsonata';

/**
 * JSONata evaluator -- matches JSONata expression from the reference against the output.
 */
export async function jsonataMetric(
  dataPoint: BaseEvalDataPoint
): Promise<Score> {
  if (!dataPoint.output) {
    throw new Error('Output was not provided');
  }
  if (!dataPoint.reference) {
    throw new Error('Reference was not provided');
  }
  if (typeof dataPoint.reference !== 'string') {
    throw new Error('Reference must be a string (jsonata)');
  }

  const expression = jsonata(dataPoint.reference);
  const result = await expression.evaluate(dataPoint.output);

  return {
    score: !!result,
    status: !!result ? EvalStatusEnum.PASS : EvalStatusEnum.FAIL,
  };
}
