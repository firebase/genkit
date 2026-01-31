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

"""Model middleware for Checks AI Safety content filtering.

This module provides model middleware that automatically evaluates both
input and output content against configured safety policies, blocking
content that violates those policies.

Middleware Flow
===============

┌─────────────────────────────────────────────────────────────────────────────┐
│                    Checks Middleware Processing                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input Messages                                                             │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────┐                                                       │
│  │  Check Input     │ ──► Violation? ──► Return blocked response           │
│  │  Content         │                                                       │
│  └──────────────────┘                                                       │
│       │                                                                      │
│       ▼ (no violation)                                                      │
│  ┌──────────────────┐                                                       │
│  │  Call Model      │                                                       │
│  │  (next())        │                                                       │
│  └──────────────────┘                                                       │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────┐                                                       │
│  │  Check Output    │ ──► Violation? ──► Return blocked response           │
│  │  Content         │                                                       │
│  └──────────────────┘                                                       │
│       │                                                                      │
│       ▼ (no violation)                                                      │
│  Return normal response                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.ai import Genkit
    from genkit.plugins.checks import checks_middleware, ChecksMetricType

    ai = Genkit()

    response = await ai.generate(
        model='googleai/gemini-2.0-flash',
        prompt='Hello!',
        use=[
            checks_middleware(
                metrics=[ChecksMetricType.HARASSMENT, ChecksMetricType.HATE_SPEECH],
                auth_options={'project_id': 'my-project'},
            )
        ],
    )

    if response.finish_reason == 'blocked':
        print(f'Content blocked: {response.finish_message}')
    ```

See Also:
    - JS implementation: js/plugins/checks/src/middleware.ts
"""

from typing import Any

from genkit.blocks.model import ModelMiddleware, ModelMiddlewareNext
from genkit.core.action import ActionRunContext
from genkit.core.typing import FinishReason, GenerateRequest, GenerateResponse, Message
from genkit.plugins.checks.auth import initialize_credentials
from genkit.plugins.checks.guardrails import Guardrails
from genkit.plugins.checks.metrics import ChecksMetric


def _get_text_content(message: Message) -> str:
    """Extract text content from a message.

    Args:
        message: The message to extract text from.

    Returns:
        Concatenated text from all text parts of the message.
    """
    texts: list[str] = []
    for part in message.content:
        if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
            texts.append(str(part.root.text))
        elif hasattr(part, 'text') and part.text:
            texts.append(str(part.text))
    return ' '.join(texts)


def checks_middleware(
    metrics: list[ChecksMetric],
    auth_options: dict[str, Any] | None = None,
) -> ModelMiddleware:
    """Create model middleware that enforces Checks AI Safety policies.

    This middleware evaluates both input and output content against the
    specified safety policies. If any policy is violated, the generation
    is blocked and a response with `finish_reason='blocked'` is returned.

    Args:
        metrics: List of safety policies to evaluate. Can be ChecksMetricType
            values or ChecksMetricConfig objects with custom thresholds.
        auth_options: Optional authentication configuration:
            - project_id: GCP project ID for API quota
            - credentials_file: Path to service account JSON

    Returns:
        A ModelMiddleware function that can be passed to ai.generate(use=[...]).

    Example:
        ```python
        from genkit.plugins.checks import checks_middleware, ChecksMetricType

        # Basic usage with default authentication
        middleware = checks_middleware(
            metrics=[ChecksMetricType.DANGEROUS_CONTENT],
        )

        # With custom authentication
        middleware = checks_middleware(
            metrics=[ChecksMetricType.HARASSMENT],
            auth_options={
                'project_id': 'my-project',
                'credentials_file': '/path/to/creds.json',
            },
        )

        # Use in generation
        response = await ai.generate(
            model='googleai/gemini-2.0-flash',
            prompt='Hello!',
            use=[middleware],
        )
        ```

    Blocking Behavior:
        When content violates a policy, the middleware returns a response with:
        - finish_reason: 'blocked'
        - finish_message: Description of which policies were violated

    See Also:
        - ChecksMetricType: Available safety policy types
        - Checks plugin: For plugin-based configuration
    """
    # Initialize credentials and guardrails client
    credentials, project_id = initialize_credentials(auth_options)
    guardrails = Guardrails(credentials, project_id)

    async def classify_content(content: str) -> list[str]:
        """Classify content and return violated policy types.

        Args:
            content: Text content to classify.

        Returns:
            List of policy type names that were violated.
        """
        response = await guardrails.classify_content(content, metrics)
        return [pr.policy_type for pr in response.policy_results if pr.violation_result == 'VIOLATIVE']

    async def middleware(
        request: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        """Middleware function that checks content safety.

        Args:
            request: The generation request.
            ctx: The action run context.
            next_fn: Function to call the next middleware/model.

        Returns:
            The generation response, or a blocked response if content
            violates safety policies.
        """
        # Check input messages
        for message in request.messages:
            text_content = _get_text_content(message)
            if text_content:
                violated_policies = await classify_content(text_content)
                if violated_policies:
                    policy_list = ' '.join(violated_policies)
                    return GenerateResponse(
                        message=Message(role='model', content=[]),
                        finish_reason=FinishReason.BLOCKED,
                        finish_message=(
                            f'Model input violated Checks policies: [{policy_list}], further processing blocked.'
                        ),
                    )

        # Call the model
        response = await next_fn(request, ctx)

        # Check output content
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'message') and candidate.message:
                    text_content = _get_text_content(candidate.message)
                    if text_content:
                        violated_policies = await classify_content(text_content)
                        if violated_policies:
                            policy_list = ' '.join(violated_policies)
                            return GenerateResponse(
                                message=Message(role='model', content=[]),
                                finish_reason=FinishReason.BLOCKED,
                                finish_message=(
                                    f'Model output violated Checks policies: [{policy_list}], output blocked.'
                                ),
                            )

        return response

    return middleware


__all__ = [
    'checks_middleware',
]
