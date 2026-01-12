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

from __future__ import annotations

import pytest

from genkit.core.action.types import ActionKind
from genkit.plugins.evaluators.constant import GenkitMetricType, MetricConfig
from genkit.plugins.evaluators.plugin_api import GenkitEvaluators


@pytest.mark.asyncio
async def test_init_returns_evaluator_actions():
    plugin = GenkitEvaluators(
        params=[
            MetricConfig(metric_type=GenkitMetricType.REGEX),
            MetricConfig(metric_type=GenkitMetricType.DEEP_EQUAL),
        ]
    )

    actions = await plugin.init()

    assert {a.kind for a in actions} == {ActionKind.EVALUATOR}
    assert {a.name for a in actions} == {str(GenkitMetricType.REGEX).lower(), str(GenkitMetricType.DEEP_EQUAL).lower()}


@pytest.mark.asyncio
async def test_list_returns_action_metadata():
    plugin = GenkitEvaluators(
        params=[
            MetricConfig(metric_type=GenkitMetricType.REGEX),
        ]
    )

    metas = await plugin.list_actions()

    assert len(metas) == 1
    assert metas[0].kind == ActionKind.EVALUATOR
    assert metas[0].name == str(GenkitMetricType.REGEX).lower()
