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

from collections.abc import Callable, Coroutine
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from genkit.core.typing import (
    BaseDataPoint,
    EvalFnResponse,
    EvalRequest,
)

T = TypeVar('T')

# User-provided evaluator function that evaluates a single datapoint.
# Must be async (coroutine function).
EvaluatorFn = Callable[[BaseDataPoint, T], Coroutine[Any, Any, EvalFnResponse]]

# User-provided batch evaluator function that evaluates an EvaluationRequest
BatchEvaluatorFn = Callable[[EvalRequest, T], Coroutine[Any, Any, list[EvalFnResponse]]]


class EvaluatorRef(BaseModel):
    """Reference to an evaluator."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=to_camel)

    name: str
    config_schema: dict[str, object] | None = None


def evaluator_ref(name: str, config_schema: dict[str, object] | None = None) -> EvaluatorRef:
    """Create a reference to an evaluator.

    Args:
        name: Name of the evaluator.
        config_schema: Optional schema for evaluator configuration.

    Returns:
        An EvaluatorRef instance.
    """
    return EvaluatorRef(name=name, config_schema=config_schema)
