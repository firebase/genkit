# Copyright 2026 Google LLC
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

"""Checks AI Safety metric types and configurations.

This module defines the supported safety policy types for the Google Checks
AI Safety API and configuration structures for customizing evaluation behavior.

Metric Types
============

Each metric type corresponds to a specific category of potentially harmful
content that the Checks API can detect:

┌─────────────────────────────────────────────────────────────────────────────┐
│ Metric                    │ Detects                                         │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ DANGEROUS_CONTENT         │ Content promoting harmful goods/services        │
│ PII_SOLICITING_RECITING   │ Requests or disclosure of personal info         │
│ HARASSMENT                │ Bullying, intimidation, or abuse                │
│ SEXUALLY_EXPLICIT         │ Sexually explicit material                      │
│ HATE_SPEECH               │ Discrimination, hatred, or violence promotion   │
│ MEDICAL_INFO              │ Potentially harmful medical advice              │
│ VIOLENCE_AND_GORE         │ Graphic violence descriptions                   │
│ OBSCENITY_AND_PROFANITY   │ Vulgar or profane language                      │
└───────────────────────────┴─────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.plugins.checks import ChecksMetricType, ChecksMetricConfig

    # Use metric type directly
    metrics = [ChecksMetricType.DANGEROUS_CONTENT]

    # Or with custom threshold
    metrics = [
        ChecksMetricType.DANGEROUS_CONTENT,
        ChecksMetricConfig(
            type=ChecksMetricType.HARASSMENT,
            threshold=0.8,
        ),
    ]
    ```

See Also:
    - JS implementation: js/plugins/checks/src/metrics.ts
"""

from dataclasses import dataclass
from enum import Enum


class ChecksMetricType(str, Enum):
    """Supported Checks AI Safety policy types.

    Each value corresponds to a specific content safety policy that can be
    evaluated by the Google Checks API.
    """

    DANGEROUS_CONTENT = 'DANGEROUS_CONTENT'
    """Content that facilitates, promotes, or enables access to harmful
    goods, services, and activities."""

    PII_SOLICITING_RECITING = 'PII_SOLICITING_RECITING'
    """Content that reveals or solicits personal information and data."""

    HARASSMENT = 'HARASSMENT'
    """Content that is malicious, intimidating, bullying, or abusive
    towards another individual."""

    SEXUALLY_EXPLICIT = 'SEXUALLY_EXPLICIT'
    """Content that is sexually explicit in nature."""

    HATE_SPEECH = 'HATE_SPEECH'
    """Content that promotes violence, hatred, or discrimination on the
    basis of race, religion, etc."""

    MEDICAL_INFO = 'MEDICAL_INFO'
    """Content that facilitates harm by providing health advice or guidance."""

    VIOLENCE_AND_GORE = 'VIOLENCE_AND_GORE'
    """Content that contains gratuitous, realistic descriptions of
    violence or gore."""

    OBSCENITY_AND_PROFANITY = 'OBSCENITY_AND_PROFANITY'
    """Content that contains vulgar, profane, or offensive language."""


@dataclass
class ChecksMetricConfig:
    """Configuration for a Checks evaluation metric with custom threshold.

    Use this to override the default violation threshold for a specific
    policy type.

    Attributes:
        type: The metric type to configure.
        threshold: Custom threshold for violation detection (0.0-1.0).
            Higher values require stronger signals to trigger a violation.
    """

    type: ChecksMetricType
    threshold: float | None = None


ChecksMetric = ChecksMetricType | ChecksMetricConfig
"""A Checks metric can be specified as either a type or a config with threshold."""


def is_metric_config(metric: ChecksMetric) -> bool:
    """Check if a metric is a config object with custom settings.

    Args:
        metric: The metric to check.

    Returns:
        True if the metric is a ChecksMetricConfig instance.
    """
    return isinstance(metric, ChecksMetricConfig)


__all__ = [
    'ChecksMetric',
    'ChecksMetricConfig',
    'ChecksMetricType',
    'is_metric_config',
]
