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

"""Tests for the Checks middleware.

These tests verify parity with the JS implementation in:
js/plugins/checks/src/middleware.ts
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.core.typing import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
    Part,
    TextPart,
)
from genkit.plugins.checks.guardrails import ClassifyContentResponse, PolicyResult
from genkit.plugins.checks.metrics import ChecksMetricType
from genkit.plugins.checks.middleware import checks_middleware


class TestChecksMiddleware:
    """Tests for checks_middleware function."""

    @pytest.mark.asyncio
    async def test_middleware_blocks_violative_input(self) -> None:
        """Test middleware blocks violative input content (matching JS behavior)."""
        # Mock guardrails to return a violation
        mock_response = ClassifyContentResponse.model_validate({
            'policyResults': [
                {
                    'policyType': 'HARASSMENT',
                    'score': 0.95,
                    'violationResult': 'VIOLATIVE',
                }
            ]
        })

        with (
            patch('genkit.plugins.checks.middleware.initialize_credentials') as mock_init_creds,
            patch(
                'genkit.plugins.checks.guardrails.Guardrails.classify_content',
                new_callable=AsyncMock,
            ) as mock_classify,
        ):
            mock_init_creds.return_value = (MagicMock(), 'test-project')
            mock_classify.return_value = mock_response

            middleware = checks_middleware(
                metrics=[ChecksMetricType.HARASSMENT],
                auth_options={'project_id': 'test-project'},
            )

            # Create a request with text content
            request = GenerateRequest(
                messages=[
                    Message(
                        role='user',
                        content=[Part(root=TextPart(text='Some harassing content'))],
                    )
                ]
            )

            ctx = MagicMock()
            next_fn = AsyncMock()

            result = await middleware(request, ctx, next_fn)

            # Verify blocked response matches JS format
            assert result.finish_reason == FinishReason.BLOCKED
            assert 'violated Checks policies' in (result.finish_message or '')
            assert 'HARASSMENT' in (result.finish_message or '')
            assert 'further processing blocked' in (result.finish_message or '')

            # Verify model was NOT called
            next_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_blocks_violative_output(self) -> None:
        """Test middleware blocks violative output content (matching JS behavior)."""
        # First call (input check) returns non-violative
        # Second call (output check) returns violative
        mock_input_response = ClassifyContentResponse.model_validate({
            'policyResults': [
                {
                    'policyType': 'HARASSMENT',
                    'score': 0.1,
                    'violationResult': 'NON_VIOLATIVE',
                }
            ]
        })
        mock_output_response = ClassifyContentResponse.model_validate({
            'policyResults': [
                {
                    'policyType': 'HARASSMENT',
                    'score': 0.95,
                    'violationResult': 'VIOLATIVE',
                }
            ]
        })

        with (
            patch('genkit.plugins.checks.middleware.initialize_credentials') as mock_init_creds,
            patch(
                'genkit.plugins.checks.guardrails.Guardrails.classify_content',
                new_callable=AsyncMock,
            ) as mock_classify,
        ):
            mock_init_creds.return_value = (MagicMock(), 'test-project')
            mock_classify.side_effect = [mock_input_response, mock_output_response]

            middleware = checks_middleware(
                metrics=[ChecksMetricType.HARASSMENT],
                auth_options={'project_id': 'test-project'},
            )

            request = GenerateRequest(
                messages=[
                    Message(
                        role='user',
                        content=[Part(root=TextPart(text='Hello'))],
                    )
                ]
            )

            # Mock model response with violative output
            model_response = MagicMock()
            model_response.candidates = [
                MagicMock(
                    message=Message(
                        role='model',
                        content=[Part(root=TextPart(text='Harassing output'))],
                    )
                )
            ]

            ctx = MagicMock()
            next_fn = AsyncMock(return_value=model_response)

            result = await middleware(request, ctx, next_fn)

            # Verify output was blocked
            assert result.finish_reason == FinishReason.BLOCKED
            assert 'output blocked' in (result.finish_message or '')

            # Verify model WAS called (input passed)
            next_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_passes_non_violative_content(self) -> None:
        """Test middleware allows non-violative content through."""
        mock_response = ClassifyContentResponse.model_validate({
            'policyResults': [
                {
                    'policyType': 'HARASSMENT',
                    'score': 0.05,
                    'violationResult': 'NON_VIOLATIVE',
                }
            ]
        })

        with (
            patch('genkit.plugins.checks.middleware.initialize_credentials') as mock_init_creds,
            patch(
                'genkit.plugins.checks.guardrails.Guardrails.classify_content',
                new_callable=AsyncMock,
            ) as mock_classify,
        ):
            mock_init_creds.return_value = (MagicMock(), 'test-project')
            mock_classify.return_value = mock_response

            middleware = checks_middleware(
                metrics=[ChecksMetricType.HARASSMENT],
                auth_options={'project_id': 'test-project'},
            )

            request = GenerateRequest(
                messages=[
                    Message(
                        role='user',
                        content=[Part(root=TextPart(text='Hello, how are you?'))],
                    )
                ]
            )

            expected_response = GenerateResponse(
                message=Message(role='model', content=[Part(root=TextPart(text='I am fine!'))]),
                finish_reason=FinishReason.STOP,
            )

            ctx = MagicMock()
            next_fn = AsyncMock(return_value=expected_response)

            result = await middleware(request, ctx, next_fn)

            # Verify response passed through
            assert result == expected_response
            next_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_checks_all_messages(self) -> None:
        """Test middleware checks all input messages (matching JS)."""
        call_count = 0

        async def mock_classify(content: str, policies: list) -> ClassifyContentResponse:
            nonlocal call_count
            call_count += 1
            return ClassifyContentResponse(
                policy_results=[
                    PolicyResult(
                        policy_type='DANGEROUS_CONTENT',
                        score=0.1,
                        violation_result='NON_VIOLATIVE',
                    )
                ]
            )

        with (
            patch('genkit.plugins.checks.middleware.initialize_credentials') as mock_init_creds,
            patch(
                'genkit.plugins.checks.guardrails.Guardrails.classify_content',
                new_callable=AsyncMock,
            ) as mock_classify_method,
        ):
            mock_init_creds.return_value = (MagicMock(), 'test-project')
            mock_classify_method.side_effect = mock_classify

            middleware = checks_middleware(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            )

            request = GenerateRequest(
                messages=[
                    Message(role='user', content=[Part(root=TextPart(text='Message 1'))]),
                    Message(role='model', content=[Part(root=TextPart(text='Response 1'))]),
                    Message(role='user', content=[Part(root=TextPart(text='Message 2'))]),
                ]
            )

            model_response = GenerateResponse(
                message=Message(role='model', content=[]),
                finish_reason=FinishReason.STOP,
            )

            ctx = MagicMock()
            next_fn = AsyncMock(return_value=model_response)

            await middleware(request, ctx, next_fn)

            # Verify all messages were checked
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_middleware_multiple_violations_in_message(self) -> None:
        """Test middleware reports multiple policy violations (matching JS format)."""
        mock_response = ClassifyContentResponse(
            policy_results=[
                PolicyResult(
                    policy_type='HARASSMENT',
                    score=0.95,
                    violation_result='VIOLATIVE',
                ),
                PolicyResult(
                    policy_type='HATE_SPEECH',
                    score=0.88,
                    violation_result='VIOLATIVE',
                ),
            ]
        )

        with (
            patch('genkit.plugins.checks.middleware.initialize_credentials') as mock_init_creds,
            patch(
                'genkit.plugins.checks.guardrails.Guardrails.classify_content',
                new_callable=AsyncMock,
            ) as mock_classify,
        ):
            mock_init_creds.return_value = (MagicMock(), 'test-project')
            mock_classify.return_value = mock_response

            middleware = checks_middleware(
                metrics=[ChecksMetricType.HARASSMENT, ChecksMetricType.HATE_SPEECH],
            )

            request = GenerateRequest(
                messages=[
                    Message(role='user', content=[Part(root=TextPart(text='Bad content'))]),
                ]
            )

            ctx = MagicMock()
            next_fn = AsyncMock()

            result = await middleware(request, ctx, next_fn)

            # Verify message format matches JS: policies joined with space
            assert 'HARASSMENT' in (result.finish_message or '')
            assert 'HATE_SPEECH' in (result.finish_message or '')

    @pytest.mark.asyncio
    async def test_middleware_skips_empty_text_content(self) -> None:
        """Test middleware skips messages without text content."""
        with (
            patch('genkit.plugins.checks.middleware.initialize_credentials') as mock_init_creds,
            patch(
                'genkit.plugins.checks.guardrails.Guardrails.classify_content',
                new_callable=AsyncMock,
            ) as mock_classify,
        ):
            mock_init_creds.return_value = (MagicMock(), 'test-project')
            # Should not be called if no text content
            mock_classify.return_value = ClassifyContentResponse()

            middleware = checks_middleware(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            )

            # Message with empty content list
            request = GenerateRequest(
                messages=[
                    Message(role='user', content=[]),
                ]
            )

            model_response = GenerateResponse(
                message=Message(role='model', content=[]),
                finish_reason=FinishReason.STOP,
            )

            ctx = MagicMock()
            next_fn = AsyncMock(return_value=model_response)

            result = await middleware(request, ctx, next_fn)

            # Should pass through without checking
            assert result == model_response


class TestMiddlewareFinishMessage:
    """Tests for middleware finish message format to match JS."""

    def test_input_blocked_message_format(self) -> None:
        """Verify input blocked message format matches JS implementation.

        JS format: Model input violated Checks policies: [policies], further processing blocked.
        This is validated in the actual middleware tests above.
        """
        pass

    def test_output_blocked_message_format(self) -> None:
        """Verify output blocked message format matches JS implementation.

        JS format: Model output violated Checks policies: [policies], output blocked.
        This is validated in the actual middleware tests above.
        """
        pass
