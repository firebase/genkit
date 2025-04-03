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
from typing import TypeVar

from genkit.core.typing import (
    BaseEvalDataPoint,
    EvalFnResponse,
    EvalRequest,
)

T = TypeVar('T')

# User-provided evaluator function that evaluates a single datapoint.
# type EvaluatorFn[T] = Callable[[BaseEvalDataPoint, T], EvalFnResponse]
EvaluatorFn = Callable[[BaseEvalDataPoint, T], EvalFnResponse]

# User-provided batch evaluator function that evaluates an EvaluationRequest
# type BatchEvaluatorFn[T] = Callable[[EvalRequest, T], list[EvalFnResponse]]
BatchEvaluatorFn = Callable[[EvalRequest, T], list[EvalFnResponse]]
