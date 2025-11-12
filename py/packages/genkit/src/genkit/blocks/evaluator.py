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

"""Evaluator type definitions for the Genkit framework.

This module defines the type interfaces for evaluators in the Genkit framework.
Evaluators are used for assessint the quality of output of a Genkit flow or
model.
"""

from collections.abc import Callable
from typing import TypeVar, Any

from genkit.core.action import Action
from genkit.core.action.types import ActionKind
from genkit.core.typing import (
    BaseEvalDataPoint,
    EvalFnResponse,
    EvalRequest,
    BaseDataPoint,
    EvaluatorOptions
)
EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'evaluatorDisplayName'
EVALUATOR_METADATA_KEY_DEFINITION = 'evaluatorDefinition'
EVALUATOR_METADATA_KEY_IS_BILLED = 'evaluatorIsBilled'

T = TypeVar('T')

# User-provided evaluator function that evaluates a single datapoint.
# type EvaluatorFn[T] = Callable[[BaseEvalDataPoint, T], EvalFnResponse]
EvaluatorFn = Callable[[BaseEvalDataPoint, T], EvalFnResponse]

# User-provided batch evaluator function that evaluates an EvaluationRequest
# type BatchEvaluatorFn[T] = Callable[[EvalRequest, T], list[EvalFnResponse]]
BatchEvaluatorFn = Callable[[EvalRequest, T], list[EvalFnResponse]]



def new_evaluator(
    options: EvaluatorOptions,
    runner: EvaluatorFn[Any],
) -> Action:
    """Create a new evaluator action.

    Args:
        options: Configuration options for the evaluator including name,
                 display name, definition, and optional schemas.
        runner: The evaluator function that processes individual data points.

    Returns:
        An Action instance configured as an evaluator.

    Raises:
        ValueError: If required options are missing or invalid.
    """
    if not options.name:
        raise ValueError('Evaluator name is required')

    metadata = {
        EVALUATOR_METADATA_KEY_DISPLAY_NAME: options.display_name,
        EVALUATOR_METADATA_KEY_DEFINITION: options.definition,
        EVALUATOR_METADATA_KEY_IS_BILLED: options.is_billed if options.is_billed is not None else True,
    }
    if options.config_schema:
        metadata['configSchema'] = options.config_schema

    async def evaluator_wrapper(request: EvalRequest) -> list[EvalFnResponse]:
        """Wrapper function that processes evaluation requests.

        Args:
            request: The evaluation request containing dataset and options.

        Returns:
            List of evaluation responses for each data point.
        """
        results: list[EvalFnResponse] = []
        for datapoint in request.dataset:
            # Ensure each datapoint has a test_case_id
            if not isinstance(datapoint, BaseEvalDataPoint):
                raise ValueError('Dataset must contain BaseEvalDataPoint instances')

            try:
                result = await runner(datapoint, request.options)
                results.append(result)
            except Exception as e:
                # Create error response for failed evaluations
                from genkit.core.typing import EvalStatusEnum, Score
                error_result = EvalFnResponse(
                    test_case_id=datapoint.test_case_id,
                    evaluation=Score(
                        status=EvalStatusEnum.FAIL,
                        error=f'Evaluation failed: {str(e)}',
                    ),
                )
                results.append(error_result)

        return results

    evaluator = Action(
        ActionKind.EVALUATOR,
        options.name,
        fn=evaluator_wrapper,
        metadata={
            'type': ActionKind.EVALUATOR.value,
            'evaluator': metadata,
        }
    )

    return evaluator


