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

"""Guardrails API client for Google Checks AI Safety.

This module provides the HTTP client for interacting with the Google Checks
classifyContent API endpoint.

API Flow
========

┌─────────────────────────────────────────────────────────────────────────────┐
│                     Guardrails API Request Flow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐        │
│  │   Content    │     │  Guardrails  │     │   Checks API         │        │
│  │   + Policies │ ──► │   Client     │ ──► │   classifyContent    │        │
│  └──────────────┘     └──────────────┘     └──────────────────────┘        │
│                              │                       │                      │
│                              │                       ▼                      │
│                              │              ┌──────────────────────┐        │
│                              │              │   Policy Results     │        │
│                              │              │   - policyType       │        │
│                              │              │   - score            │        │
│                              │              │   - violationResult  │        │
│                              │              └──────────────────────┘        │
│                              │                       │                      │
│                              ▼                       ▼                      │
│                       ┌──────────────────────────────────┐                 │
│                       │   Parsed Response with Results   │                 │
│                       └──────────────────────────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from google.auth import default
    from genkit.plugins.checks.guardrails import Guardrails
    from genkit.plugins.checks.metrics import ChecksMetricType

    credentials, project_id = default()
    guardrails = Guardrails(credentials, project_id)

    result = await guardrails.classify_content(
        content='Hello, how can I help you today?',
        policies=[ChecksMetricType.DANGEROUS_CONTENT],
    )

    for policy_result in result.policy_results:
        print(f'{policy_result.policy_type}: {policy_result.violation_result}')
    ```

See Also:
    - JS implementation: js/plugins/checks/src/guardrails.ts
    - Checks API docs: https://developers.google.com/checks
"""

from dataclasses import dataclass
from typing import Any

import httpx
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from genkit.plugins.checks.metrics import ChecksMetric, ChecksMetricConfig, ChecksMetricType

GUARDRAILS_URL = 'https://checks.googleapis.com/v1alpha/aisafety:classifyContent'


class PolicyResult(BaseModel):
    """Result of evaluating content against a single policy.

    Attributes:
        policy_type: The type of policy that was evaluated.
        score: Optional confidence score for the evaluation (0.0-1.0).
        violation_result: Whether the content violates this policy.
            Values: 'VIOLATIVE', 'NON_VIOLATIVE', or 'CLASSIFICATION_UNSPECIFIED'.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    policy_type: str
    score: float | None = None
    violation_result: str = 'CLASSIFICATION_UNSPECIFIED'


class ClassifyContentResponse(BaseModel):
    """Response from the Checks classifyContent API.

    Attributes:
        policy_results: List of results for each evaluated policy.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    policy_results: list[PolicyResult] = Field(default_factory=list)


@dataclass
class GuardrailsRequest:
    """Request structure for the classifyContent API.

    Attributes:
        content: The text content to classify.
        policies: List of policies to evaluate against.
    """

    content: str
    policies: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to API request format.

        Returns:
            Dictionary in the format expected by the Checks API.
        """
        return {
            'input': {
                'text_input': {
                    'content': self.content,
                },
            },
            'policies': self.policies,
        }


class Guardrails:
    """Client for the Google Checks AI Safety classifyContent API.

    This class handles authentication and HTTP requests to the Checks API
    for content classification against safety policies.

    Attributes:
        credentials: Google Cloud credentials for authentication.
        project_id: GCP project ID for quota attribution.
    """

    def __init__(
        self,
        credentials: Credentials,
        project_id: str | None = None,
    ) -> None:
        """Initialize the Guardrails client.

        Args:
            credentials: Google Cloud credentials for API authentication.
            project_id: Optional GCP project ID. If not provided, will attempt
                to use the default project from the credentials.
        """
        self._credentials = credentials
        self._project_id = project_id

    async def classify_content(
        self,
        content: str,
        policies: list[ChecksMetric],
    ) -> ClassifyContentResponse:
        """Classify content against specified safety policies.

        Args:
            content: The text content to evaluate.
            policies: List of policies to check against. Can be ChecksMetricType
                values or ChecksMetricConfig objects with custom thresholds.

        Returns:
            ClassifyContentResponse with results for each policy.

        Raises:
            httpx.HTTPError: If the API request fails.
            ValueError: If the API response cannot be parsed.

        Example:
            ```python
            result = await guardrails.classify_content(
                content='Some text to check',
                policies=[
                    ChecksMetricType.DANGEROUS_CONTENT,
                    ChecksMetricConfig(
                        type=ChecksMetricType.HARASSMENT,
                        threshold=0.8,
                    ),
                ],
            )

            violations = [r for r in result.policy_results if r.violation_result == 'VIOLATIVE']
            ```
        """
        # Convert policies to API format
        api_policies: list[dict[str, Any]] = []
        for policy in policies:
            if isinstance(policy, ChecksMetricConfig):
                api_policy: dict[str, Any] = {'policy_type': policy.type.value}
                if policy.threshold is not None:
                    api_policy['threshold'] = policy.threshold
                api_policies.append(api_policy)
            elif isinstance(policy, ChecksMetricType):
                api_policies.append({'policy_type': policy.value})

        request = GuardrailsRequest(content=content, policies=api_policies)

        # Get access token - the google-auth library handles caching and refresh
        # automatically when the token is expired or about to expire
        if not self._credentials.valid:
            self._credentials.refresh(Request())
        token = self._credentials.token

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        if self._project_id:
            headers['x-goog-user-project'] = self._project_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GUARDRAILS_URL,
                json=request.to_dict(),
                headers=headers,
            )
            response.raise_for_status()

            try:
                data = response.json()
                return ClassifyContentResponse.model_validate(data)
            except Exception as e:
                raise ValueError(f'Error parsing {GUARDRAILS_URL} API response: {e}') from e


__all__ = [
    'ClassifyContentResponse',
    'GUARDRAILS_URL',
    'Guardrails',
    'GuardrailsRequest',
    'PolicyResult',
]
