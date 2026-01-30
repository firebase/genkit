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

"""Google Checks AI Safety plugin for Genkit.

This plugin integrates the Google Checks AI Safety API with Genkit, providing
content safety evaluation, guardrails middleware, and policy-based content
filtering for AI-generated content.

Overview
========

Google Checks AI Safety evaluates content against configurable safety policies
to detect potentially harmful content including dangerous information,
harassment, hate speech, explicit content, and more.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      Checks Plugin Architecture                          │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                          │
    │  ┌──────────┐     ┌──────────────┐     ┌──────────────────┐            │
    │  │  Model   │     │   Checks     │     │   Checks API     │            │
    │  │ Request  │ ──► │  Middleware  │ ──► │   (classify)     │            │
    │  └──────────┘     └──────────────┘     └──────────────────┘            │
    │       │                  │                      │                       │
    │       │                  ▼                      ▼                       │
    │       │           ┌──────────────┐     ┌──────────────────┐            │
    │       │           │   Policy     │ ◄── │   Violation      │            │
    │       │           │   Check      │     │   Results        │            │
    │       │           └──────────────┘     └──────────────────┘            │
    │       │                  │                                              │
    │       │                  ▼                                              │
    │       │           ┌──────────────┐                                     │
    │       └─────────► │   Allow /    │ ──► Response to user                │
    │                   │   Block      │                                     │
    │                   └──────────────┘                                     │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘

Key Components
==============

┌─────────────────────────────────────────────────────────────────────────────┐
│ Component             │ Description                                         │
├───────────────────────┼─────────────────────────────────────────────────────┤
│ Checks plugin         │ Main plugin that registers evaluators               │
│ checks_middleware()   │ Model middleware for automatic content filtering    │
│ ChecksMetricType      │ Enum of supported safety policy types               │
│ Guardrails            │ API client for Checks classifyContent endpoint      │
└───────────────────────┴─────────────────────────────────────────────────────┘

Supported Metrics
=================

┌─────────────────────────────────────────────────────────────────────────────┐
│ Metric                    │ Description                                     │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ DANGEROUS_CONTENT         │ Harmful goods, services, or activities          │
│ PII_SOLICITING_RECITING   │ Personal information disclosure                 │
│ HARASSMENT                │ Malicious, intimidating, or abusive content     │
│ SEXUALLY_EXPLICIT         │ Sexually explicit content                       │
│ HATE_SPEECH               │ Violence, hatred, or discrimination             │
│ MEDICAL_INFO              │ Harmful health advice                           │
│ VIOLENCE_AND_GORE         │ Gratuitous violence or gore                     │
│ OBSCENITY_AND_PROFANITY   │ Vulgar or offensive language                    │
└───────────────────────────┴─────────────────────────────────────────────────┘

Example:
    Basic plugin usage:

    ```python
    from genkit.ai import Genkit
    from genkit.plugins.checks import Checks, ChecksMetricType

    ai = Genkit(
        plugins=[
            Checks(
                project_id='my-gcp-project',
                evaluation={
                    'metrics': [
                        ChecksMetricType.DANGEROUS_CONTENT,
                        ChecksMetricType.HARASSMENT,
                    ]
                },
            )
        ]
    )
    ```

    Using middleware for automatic content filtering:

    ```python
    from genkit.plugins.checks import checks_middleware, ChecksMetricType

    response = await ai.generate(
        model='googleai/gemini-2.0-flash',
        prompt='Tell me about AI safety',
        use=[
            checks_middleware(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
                auth_options={'project_id': 'my-project'},
            )
        ],
    )

    # Check if response was blocked
    if response.finish_reason == 'blocked':
        print(f'Content blocked: {response.finish_message}')
    ```

Caveats:
    - Requires Google Cloud project with Checks API quota
    - Network latency added for each content classification
    - Some metrics may have different sensitivities

See Also:
    - Google Checks: https://developers.google.com/checks
    - JS implementation: js/plugins/checks/
"""

from genkit.plugins.checks.guardrails import Guardrails, PolicyResult
from genkit.plugins.checks.metrics import (
    ChecksMetricConfig,
    ChecksMetricType,
    is_metric_config,
)
from genkit.plugins.checks.middleware import checks_middleware
from genkit.plugins.checks.plugin import Checks, ChecksEvaluationConfig, ChecksOptions

__all__ = [
    'Checks',
    'ChecksEvaluationConfig',
    'ChecksMetricConfig',
    'ChecksMetricType',
    'ChecksOptions',
    'Guardrails',
    'PolicyResult',
    'checks_middleware',
    'is_metric_config',
]
