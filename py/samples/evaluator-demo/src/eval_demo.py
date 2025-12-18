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

import json
import os
from typing import Any

import pytest
import structlog

from genkit.ai import Genkit
from genkit.core.typing import BaseDataPoint, EvalFnResponse, EvalStatusEnum, Score
from genkit.plugins.google_genai import GoogleAI

logger = structlog.get_logger(__name__)

ai = Genkit(plugins=[GoogleAI()])


async def substring_match(datapoint: BaseDataPoint, options: Any | None):
    output = str(datapoint.output or '')
    reference = str(datapoint.reference or '')

    passed = reference.lower() in output.lower()

    return EvalFnResponse(
        test_case_id=datapoint.test_case_id,
        evaluation=Score(
            score=passed,
            status=EvalStatusEnum.PASS_ if passed else EvalStatusEnum.FAIL,
            details={'reasoning': f'Reference "{reference}" was {"found" if passed else "not found"} in output'},
        ),
    )


ai.define_evaluator(
    name='substring_match',
    display_name='Substring Match',
    definition='Checks if the reference string is present in the output',
    fn=substring_match,
)


#  Define a flow that programmatically runs the evaluation
@ai.flow()
async def run_eval_demo(input: Any = None):
    # Load dataset
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset.json')
    with open(data_path, 'r') as f:
        raw_data = json.load(f)

    dataset = [BaseDataPoint(**d) for d in raw_data]

    logger.info('Running evaluation...', count=len(dataset))

    # Run evaluation using the high-level ai.evaluate() API
    results = await ai.evaluate(evaluator='substring_match', dataset=dataset)

    logger.info('Evaluation complete', results_count=len(results.root))

    for res in results.root:
        case_id = res.test_case_id
        evaluation = res.evaluation[0] if isinstance(res.evaluation, list) else res.evaluation
        score = evaluation.score
        reason = evaluation.details.reasoning if evaluation.details else 'N/A'
        logger.info(f'Case {case_id}: {"✅ PASS" if score else "❌ FAIL"} - {reason}')

    return results


if __name__ == '__main__':
    ai.run_main()
