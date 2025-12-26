# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import random

from genkit_demo import ai

from genkit.core.typing import BaseEvalDataPoint, EvalStatusEnum, Score


# Test evaluator that generates random scores and randomly fails
async def random_eval(datapoint: BaseEvalDataPoint, options: dict | None = None):
    score = random.random()
    # Throw if score is 0.5x (10% prob.)
    if 0.5 <= score < 0.6:
        raise ValueError('Simulated error')

    # PASS if score > 0.5, else FAIL
    status = EvalStatusEnum.FAIL if score < 0.5 else EvalStatusEnum.PASS_
    return Score(
        score=score,
        status=status,
        details={'reasoning': 'Randomly failed' if status == EvalStatusEnum.FAIL else 'Randomly passed'},
    )


ai.define_evaluator(
    name='custom/test_evaluator',
    display_name='TEST - Random Eval',
    definition='Randomly generates scores, for testing Evals UI only',
    fn=random_eval,
)

if __name__ == '__main__':
    ai.run_main()
