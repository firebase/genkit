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

"""Evaluator namespace module for Genkit.

Everything needed to call or write an evaluator lives here.

Per-row evaluators take ``EvaluatorRequest[Cfg]`` (``req.row``, ``req.options``).
Batch evaluators take ``BatchEvaluatorRequest[Cfg]`` (``req.dataset``,
``req.options``), the request the evaluator action receives on the wire.

Example:
    ```python
    from pydantic import BaseModel

    from genkit import Genkit
    from genkit.evaluator import BaseDataPoint, EvaluatorRequest, EvaluatorResponse, Score

    ai = Genkit()


    # 1. Declare the options and score one row
    class AllergenConfig(BaseModel):
        allergen: str = 'peanut'


    async def allergen_check(req: EvaluatorRequest[AllergenConfig]) -> EvaluatorResponse:
        ok = req.options.allergen not in str(req.row.output).lower()
        return EvaluatorResponse(test_case_id=req.row.test_case_id or '', evaluation=[Score(score=ok)])


    ai.define_evaluator(
        name='allergen_check', display_name='Allergen check', definition='Flags an allergen.', fn=allergen_check
    )

    # 2. Run it over a dataset; config is validated into AllergenConfig
    results = await ai.evaluate(
        evaluator='allergen_check',
        dataset=[BaseDataPoint(input='Suggest a dish.', output='Peanut noodles')],
        config={'allergen': 'peanut'},
    )
    print(results[0].evaluation[0].score)
    # => False
    ```
"""

from genkit._ai._evaluator import (
    BatchEvaluator,
    Evaluator,
    EvaluatorRef,
)
from genkit._core._model import BatchEvaluatorRequest, EvaluatorRequest
from genkit._core._typing import (
    BaseDataPoint,
    EvaluatorResponse,
    Score,
    ScoreDetails,
    ScoreStatus,
)

__all__ = [
    # Dataset rows
    'BaseDataPoint',
    # Request/Response types
    'EvaluatorRequest',
    'BatchEvaluatorRequest',
    'EvaluatorResponse',
    # Score types
    'Score',
    'ScoreDetails',
    # Status
    'ScoreStatus',
    # Reference types
    'EvaluatorRef',
    # Plugins: build and return in init, resolve, and list_actions
    'Evaluator',
    'BatchEvaluator',
]
