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

The Checks plugin registers a guardrails evaluator that evaluates content
against all configured safety metrics using Genkit's evaluation framework.

┌─────────────────────────────────────────────────────────────────────────────┐
│                    Checks Plugin Registration                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐        │
│  │   Genkit     │     │   Checks     │     │   Evaluator          │        │
│  │   Instance   │ ──► │   Plugin     │ ──► │   checks/guardrails  │        │
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
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, cast

from google.auth import default as default_credentials
from google.auth.credentials import Credentials
from google.oauth2 import service_account

from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.logging import get_logger
from genkit.core.plugin import Plugin
from genkit.core.registry import Registry
from genkit.core.tracing import SpanMetadata, run_in_new_span
from genkit.core.typing import (
    BaseDataPoint,
    Details,
    EvalFnResponse,
    EvalRequest,
    EvalResponse,
    EvalStatusEnum,
    Score,
)
from genkit.plugins.checks.guardrails import Guardrails
from genkit.plugins.checks.metrics import ChecksMetric, ChecksMetricConfig, ChecksMetricType

logger = get_logger(__name__)

# Evaluator metadata keys (matching JS implementation)
EVALUATOR_METADATA_KEY_DEFINITION = 'definition'
EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'displayName'
EVALUATOR_METADATA_KEY_IS_BILLED = 'isBilled'

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
        - Single guardrails evaluator for all configured safety metrics
        - Automatic authentication with Google Cloud
        - Configurable safety thresholds per metric

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
    _GUARDRAILS_EVALUATOR_NAME = 'checks/guardrails'

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
        self._policy_configs: list[ChecksMetricConfig] = []
        self._evaluator_action: Action | None = None

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

    def _build_policy_configs(self) -> list[ChecksMetricConfig]:
        """Build policy configurations from metrics.

        Returns:
            List of ChecksMetricConfig with type and optional threshold.
        """
        configs: list[ChecksMetricConfig] = []
        for metric in self._metrics:
            if isinstance(metric, ChecksMetricConfig):
                configs.append(metric)
            elif isinstance(metric, ChecksMetricType):
                configs.append(ChecksMetricConfig(type=metric))
        return configs

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

        # Build policy configs for evaluation
        self._policy_configs = self._build_policy_configs()

        logger.info(f'Checks plugin initialized with {len(self._metrics)} metrics')

        # Actions are created lazily via resolve()
        return []

    async def _evaluate_datapoint(
        self,
        datapoint: BaseDataPoint,
        options: object | None,
    ) -> EvalFnResponse:
        """Evaluate a single datapoint against configured safety policies.

        Args:
            datapoint: The evaluation datapoint containing content to evaluate.
            options: Optional evaluation options (unused).

        Returns:
            EvalFnResponse with scores for each policy.
        """
        if self._guardrails is None:
            raise ValueError('Plugin not initialized: guardrails client is None')

        # Get the output content to evaluate
        output = datapoint.output
        if output is None:
            return EvalFnResponse(
                test_case_id=datapoint.test_case_id or '',
                evaluation=Score(
                    error='No output content to evaluate',
                    status=EvalStatusEnum.FAIL,
                ),
            )

        # Convert output to string
        content = output if isinstance(output, str) else str(output)

        # Call the Checks API
        response = await self._guardrails.classify_content(
            content=content,
            policies=[config.type for config in self._policy_configs],
        )

        # Convert policy results to evaluation scores
        # Return all policy results as an array of scores (matching JS implementation)
        if response.policy_results:
            # Create individual scores for each policy (matches JS evaluationResults)
            evaluation_results: list[Score] = []
            for result in response.policy_results:
                evaluation_results.append(
                    Score(
                        id=result.policy_type,
                        score=result.score,
                        details=Details(reasoning=f'Status {result.violation_result}'),
                    )
                )

            return EvalFnResponse(
                test_case_id=datapoint.test_case_id or '',
                evaluation=evaluation_results,
            )
        else:
            return EvalFnResponse(
                test_case_id=datapoint.test_case_id or '',
                evaluation=Score(
                    error='No policy results returned from Checks API',
                    status=EvalStatusEnum.FAIL,
                ),
            )

    def _create_evaluator_action(self) -> Action:
        """Create the guardrails evaluator action.

        This creates a single evaluator that evaluates content against all
        configured safety policies, matching the JS implementation.

        Returns:
            The evaluator Action.
        """
        if self._registry is None:
            raise ValueError('Plugin not initialized: registry is None')

        # Build definition string listing the policies
        policy_names = [config.type.value for config in self._policy_configs]
        definition = f'Evaluates input text against the Checks {", ".join(policy_names)} policies.'

        # Build evaluator metadata
        evaluator_meta: dict[str, object] = {
            'evaluator': {
                EVALUATOR_METADATA_KEY_DEFINITION: definition,
                EVALUATOR_METADATA_KEY_DISPLAY_NAME: self._GUARDRAILS_EVALUATOR_NAME,
                EVALUATOR_METADATA_KEY_IS_BILLED: True,  # Checks API is a paid service
                'label': self._GUARDRAILS_EVALUATOR_NAME,
            }
        }

        # Create the eval stepper function that iterates over the dataset
        # This matches the pattern in genkit.ai._registry.define_evaluator
        async def eval_stepper_fn(req: EvalRequest) -> EvalResponse:
            """Process all datapoints in the evaluation request."""
            eval_responses: list[EvalFnResponse] = []
            for datapoint in req.dataset:
                if datapoint.test_case_id is None:
                    datapoint.test_case_id = str(uuid.uuid4())
                span_metadata = SpanMetadata(
                    name=f'Test Case {datapoint.test_case_id}',
                    metadata={'evaluator:evalRunId': req.eval_run_id},
                )
                try:
                    # Try to run with tracing
                    try:
                        with run_in_new_span(span_metadata, labels={'genkit:type': 'evaluator'}) as span:
                            span_id = span.span_id
                            trace_id = span.trace_id
                            try:
                                span.set_input(datapoint)
                                test_case_output = await self._evaluate_datapoint(datapoint, req.options)
                                test_case_output.span_id = span_id
                                test_case_output.trace_id = trace_id
                                span.set_output(test_case_output)
                                eval_responses.append(test_case_output)
                            except Exception as e:
                                logger.debug(f'Checks evaluator error: {e!s}')
                                logger.debug(traceback.format_exc())
                                evaluation = Score(
                                    error=f'Evaluation of test case {datapoint.test_case_id} failed: \n{e!s}',
                                    status=cast(EvalStatusEnum, EvalStatusEnum.FAIL),
                                )
                                eval_responses.append(
                                    EvalFnResponse(
                                        span_id=span_id,
                                        trace_id=trace_id,
                                        test_case_id=datapoint.test_case_id,
                                        evaluation=evaluation,
                                    )
                                )
                                raise
                    except (AttributeError, UnboundLocalError):
                        # Fallback: run without span
                        try:
                            test_case_output = await self._evaluate_datapoint(datapoint, req.options)
                            eval_responses.append(test_case_output)
                        except Exception as e:
                            logger.debug(f'Checks evaluator error: {e!s}')
                            logger.debug(traceback.format_exc())
                            evaluation = Score(
                                error=f'Evaluation of test case {datapoint.test_case_id} failed: \n{e!s}',
                                status=cast(EvalStatusEnum, EvalStatusEnum.FAIL),
                            )
                            eval_responses.append(
                                EvalFnResponse(
                                    test_case_id=datapoint.test_case_id,
                                    evaluation=evaluation,
                                )
                            )
                except Exception:
                    # Continue to process other datapoints
                    continue
            return EvalResponse(eval_responses)

        # Create and return the Action directly
        return Action(
            kind=cast(ActionKind, ActionKind.EVALUATOR),
            name=self._GUARDRAILS_EVALUATOR_NAME,
            fn=eval_stepper_fn,
            metadata=evaluator_meta,
            description=definition,
        )

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve a single action by type and name.

        The Checks plugin provides a single evaluator action for content
        safety classification called 'checks/guardrails'.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action (e.g., 'checks/guardrails').

        Returns:
            Action | None: The Action instance if found, None otherwise.
        """
        if action_type != ActionKind.EVALUATOR:
            return None

        # Check if this is the checks guardrails evaluator
        if name != self._GUARDRAILS_EVALUATOR_NAME:
            return None

        # Create the evaluator action lazily (only when first requested)
        if self._evaluator_action is None:
            self._evaluator_action = self._create_evaluator_action()

        return self._evaluator_action

    async def list_actions(self) -> list[ActionMetadata]:
        """Return metadata for available evaluator actions.

        Returns:
            List with a single ActionMetadata for the guardrails evaluator
            if metrics are configured.
        """
        # Only advertise the evaluator if metrics are configured
        if not self._metrics:
            return []

        return [
            ActionMetadata(
                kind=ActionKind.EVALUATOR,
                name=self._GUARDRAILS_EVALUATOR_NAME,
            )
        ]


__all__ = [
    'Checks',
    'ChecksEvaluationConfig',
    'ChecksOptions',
]
