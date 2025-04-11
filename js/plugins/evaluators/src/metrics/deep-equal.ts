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

import * as assert from 'assert';
import { BaseEvalDataPoint, EvalStatusEnum, Score } from 'genkit/evaluator';

/**
 * Deep equality evaluator -- tests output equality against the reference.
 */
export async function deepEqual(dataPoint: BaseEvalDataPoint): Promise<Score> {
  if (!dataPoint.output) {
    throw new Error('Output was not provided');
  }
  if (!dataPoint.reference) {
    throw new Error('Reference was not provided');
  }

  try {
    assert.deepStrictEqual(dataPoint.output, dataPoint.reference);
    return {
      score: true,
      status: EvalStatusEnum.PASS,
    };
  } catch (e) {
    return {
      score: false,
      details: { reasoning: `${e instanceof Error ? e.message : e}` },
      status: EvalStatusEnum.FAIL,
    };
  }
}
