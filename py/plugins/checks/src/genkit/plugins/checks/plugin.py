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

"""Checks AI Safety Genkit plugin.

This module provides the main plugin class for integrating Google Checks
AI Safety with Genkit applications.

Plugin Registration
===================

The Checks plugin registers evaluators for each configured safety metric,
allowing you to evaluate content safety using Genkit's evaluation framework.

┌─────────────────────────────────────────────────────────────────────────────┐
│                    Checks Plugin Registration                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐        │
│  │   Genkit     │     │   Checks     │     │   Evaluators         │        │
│  │   Instance   │ ──► │   Plugin     │ ──► │   Registered         │        │
│  └──────────────┘     └──────────────┘     │   - DANGEROUS_CONTENT│        │
│                              │             │   - HARASSMENT        │        │
│                              │             │   - etc.              │        │
│                              │             └──────────────────────┘        │
│                              │                                              │
│                              ▼                                              │
│                       ┌──────────────────────────────────────────┐         │
│                       │   Google Checks API (classifyContent)    │         │
│                       └──────────────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Example:
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
                        ChecksMetricType.HATE_SPEECH,
                    ]
                },
            )
        ]
    )
    ```

See Also:
    - JS implementation: js/plugins/checks/src/index.ts
    - Checks API: https://developers.google.com/checks
"""

import os
from dataclasses import dataclass, field
from typing import Any

from google.auth import default as default_credentials
from google.auth.credentials import Credentials
from google.oauth2 import service_account

from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.logging import get_logger
from genkit.core.plugin import Plugin
from genkit.core.registry import Registry
from genkit.plugins.checks.guardrails import Guardrails
from genkit.plugins.checks.metrics import ChecksMetric, ChecksMetricConfig, ChecksMetricType

logger = get_logger(__name__)

CLOUD_PLATFORM_OAUTH_SCOPE = 'https://www.googleapis.com/auth/cloud-platform'
CHECKS_OAUTH_SCOPE = 'https://www.googleapis.com/auth/checks'


@dataclass
class ChecksEvaluationConfig:
    """Configuration for Checks evaluators.

    Attributes:
        metrics: List of safety metrics to enable as evaluators.
    """

    metrics: list[ChecksMetric] = field(default_factory=list)


@dataclass
class ChecksOptions:
    """Configuration options for the Checks plugin.

    Attributes:
        project_id: Google Cloud project ID with Checks API quota.
            If not provided, will attempt to detect from credentials
            or environment.
        google_auth_options: Custom Google Cloud authentication options.
            Can include 'credentials_file' for service account JSON path.
        evaluation: Configuration for Checks evaluators.
    """

    project_id: str | None = None
    google_auth_options: dict[str, Any] | None = None
    evaluation: ChecksEvaluationConfig | dict[str, Any] | None = None


class Checks(Plugin):
    """Google Checks AI Safety plugin for Genkit.

    This plugin integrates the Google Checks AI Safety API with Genkit,
    providing content safety evaluation capabilities.

    Key Features:
        - Evaluators for each safety metric type
        - Automatic authentication with Google Cloud
        - Configurable safety thresholds

    Example:
        ```python
        from genkit.ai import Genkit
        from genkit.plugins.checks import Checks, ChecksMetricType

        # Basic usage
        ai = Genkit(plugins=[Checks(project_id='my-project')])

        # With evaluation metrics
        ai = Genkit(
            plugins=[
                Checks(
                    project_id='my-project',
                    evaluation={
                        'metrics': [
                            ChecksMetricType.DANGEROUS_CONTENT,
                            ChecksMetricType.HARASSMENT,
                        ]
                    },
                )
            ]
        )

        # With custom authentication
        ai = Genkit(
            plugins=[
                Checks(
                    project_id='my-project',
                    google_auth_options={'credentials_file': '/path/to/creds.json'},
                )
            ]
        )
        ```

    Authentication:
        The plugin uses Google Cloud authentication. Credentials are loaded in
        this order:
        1. GCLOUD_SERVICE_ACCOUNT_CREDS environment variable (JSON string)
        2. google_auth_options.credentials_file (service account file path)
        3. Default application credentials

    See Also:
        - ChecksMetricType: Available safety metrics
        - checks_middleware: For middleware-based content filtering
    """

    name = 'checks'

    def __init__(
        self,
        project_id: str | None = None,
        google_auth_options: dict[str, Any] | None = None,
        evaluation: ChecksEvaluationConfig | dict[str, Any] | None = None,
    ) -> None:
        """Initialize the Checks plugin.

        Args:
            project_id: Google Cloud project ID. Must have Checks API quota.
            google_auth_options: Custom authentication options.
            evaluation: Configuration for safety evaluators.
        """
        self._project_id = project_id
        self._google_auth_options = google_auth_options
        self._evaluation = evaluation
        self._credentials: Credentials | None = None
        self._registry: Registry | None = None
        self._guardrails: Guardrails | None = None
        self._metrics: list[ChecksMetric] = []

    def _initialize_auth(self) -> Credentials:
        """Initialize Google Cloud authentication.

        Returns:
            Initialized credentials.

        Raises:
            ValueError: If authentication cannot be established.
        """
        # Check for service account in environment
        if os.environ.get('GCLOUD_SERVICE_ACCOUNT_CREDS'):
            import json

            creds_data = json.loads(os.environ['GCLOUD_SERVICE_ACCOUNT_CREDS'])
            credentials = service_account.Credentials.from_service_account_info(
                creds_data,
                scopes=[CLOUD_PLATFORM_OAUTH_SCOPE, CHECKS_OAUTH_SCOPE],
            )
            return credentials

        # Use credentials file if provided
        if self._google_auth_options and self._google_auth_options.get('credentials_file'):
            credentials = service_account.Credentials.from_service_account_file(
                self._google_auth_options['credentials_file'],
                scopes=[CLOUD_PLATFORM_OAUTH_SCOPE, CHECKS_OAUTH_SCOPE],
            )
            return credentials

        # Fall back to default credentials
        credentials, project = default_credentials(scopes=[CLOUD_PLATFORM_OAUTH_SCOPE, CHECKS_OAUTH_SCOPE])

        # Update project_id if not set
        if self._project_id is None and project:
            self._project_id = project

        return credentials

    async def init(self, registry: Registry | None = None) -> list[Action]:
        """Initialize the plugin with the Genkit registry.

        This method sets up authentication and prepares evaluators for
        each configured safety metric.

        Args:
            registry: The Genkit registry. Used for cross-plugin resolution.

        Returns:
            List of actions to pre-register (empty for this plugin).

        Raises:
            ValueError: If project_id is not configured and cannot be detected.
        """
        self._registry = registry
        self._credentials = self._initialize_auth()

        # Determine project ID
        if self._project_id is None:
            raise ValueError(
                "Checks Plugin is missing the 'project_id' configuration. "
                "Please set the 'GCLOUD_PROJECT' environment variable or "
                "explicitly pass 'project_id' into the plugin config."
            )

        # Initialize guardrails client
        self._guardrails = Guardrails(self._credentials, self._project_id)

        # Get metrics from evaluation config
        if self._evaluation:
            if isinstance(self._evaluation, ChecksEvaluationConfig):
                self._metrics = self._evaluation.metrics
            elif isinstance(self._evaluation, dict):
                self._metrics = self._evaluation.get('metrics', [])

        logger.info(f'Checks plugin initialized with {len(self._metrics)} metrics')

        # Actions are created lazily via resolve()
        return []

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve a single action by type and name.

        Currently, the Checks plugin provides evaluator actions for content
        safety classification.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action (e.g., 'checks/dangerous_content').

        Returns:
            Action | None: The Action instance if found, None otherwise.
        """
        if action_type != ActionKind.EVALUATOR:
            return None

        # Check if this is a checks evaluator
        if not name.startswith(f'{self.name}/'):
            return None

        # TODO(#4357): Create and return evaluator action for the requested metric
        # The JS implementation creates evaluators using ai.defineEvaluator()
        # See: js/plugins/checks/src/evaluation.ts
        logger.debug(f'Checks evaluator requested but not yet implemented: {name}')
        return None

    async def list_actions(self) -> list[ActionMetadata]:
        """Return metadata for available evaluator actions.

        Returns:
            List of ActionMetadata for each configured safety metric evaluator.
        """
        actions: list[ActionMetadata] = []

        for metric in self._metrics:
            # Get metric type name
            if isinstance(metric, ChecksMetricConfig):
                metric_name = metric.type.value
            elif isinstance(metric, ChecksMetricType):
                metric_name = metric.value
            else:
                continue

            evaluator_name = f'{self.name}/{metric_name.lower()}'
            actions.append(
                ActionMetadata(
                    kind=ActionKind.EVALUATOR,
                    name=evaluator_name,
                )
            )

        return actions


__all__ = [
    'Checks',
    'ChecksEvaluationConfig',
    'ChecksOptions',
]
