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


from collections.abc import Callable
try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum
from typing import Any

from pydantic import BaseModel, RootModel

from genkit.core.typing import ModelReference
from genkit.types import EvalStatusEnum, Score


class GenkitMetricType(StrEnum):
    """Enumeration of GenkitMetricType values."""

    ANSWER_RELEVANCY = ('ANSWER_RELEVANCY',)
    FAITHFULNESS = ('FAITHFULNESS',)
    MALICIOUSNESS = ('MALICIOUSNESS',)
    REGEX = ('REGEX',)
    DEEP_EQUAL = ('DEEP_EQUAL',)
    JSONATA = ('JSONATA',)


class MetricConfig(BaseModel):
    """Represents configuration for a GenkitEval metric.

    Some optional fields in this schema may be required, based on the metric type.
    """

    metric_type: GenkitMetricType
    status_override_fn: Callable[[Score], EvalStatusEnum] | None = None
    metric_config: Any | None = None
    judge: ModelReference | None = None
    judge_config: dict[str, Any] | None = None


class PluginOptions(RootModel[list[MetricConfig]]):
    """List of metrics to configure the genkitEval plugin."""

    root: list[MetricConfig]


class AnswerRelevancyResponseSchema(BaseModel):
    question: str
    answered: bool
    noncommittal: bool


class MaliciousnessResponseSchema(BaseModel):
    reason: str
    verdict: bool


class LongFormResponseSchema(BaseModel):
    statements: list[str]


class NliResponseBase(BaseModel):
    statement: str
    reason: str
    verdict: bool


class NliResponse(BaseModel):
    responses: list[NliResponseBase]
