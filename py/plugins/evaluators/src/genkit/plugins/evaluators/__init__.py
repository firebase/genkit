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


"""RAGAS Evaluators Plugin for Genkit.

This plugin provides Genkit evaluators, built as wrappers on RAGAS.
"""

from genkit.plugins.evaluators.constant import (
    GenkitMetricType,
    MetricConfig,
    PluginOptions,
)
from genkit.plugins.evaluators.plugin_api import (
    GenkitEvaluators,
    evaluators_name,
)


def package_name() -> str:
    """Get the package name for the Google AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.evaluators'


__all__ = ['package_name', 'GenkitEvaluators', 'evaluators_name', 'GenkitMetricType', 'MetricConfig', 'PluginOptions']
