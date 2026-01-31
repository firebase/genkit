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

"""Tests for the Checks Guardrails API client.

These tests verify parity with the JS implementation in:
js/plugins/checks/src/guardrails.ts
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.plugins.checks.guardrails import (
    GUARDRAILS_URL,
    ClassifyContentResponse,
    Guardrails,
    GuardrailsRequest,
    PolicyResult,
)
from genkit.plugins.checks.metrics import ChecksMetricConfig, ChecksMetricType


class TestPolicyResult:
    """Tests for PolicyResult model."""

    def test_policy_result_from_api_response(self) -> None:
        """Test PolicyResult can be created with Python field names."""
        result = PolicyResult(
            policy_type='DANGEROUS_CONTENT',
            score=0.95,
            violation_result='VIOLATIVE',
        )
        assert result.policy_type == 'DANGEROUS_CONTENT'
        assert result.score == 0.95
        assert result.violation_result == 'VIOLATIVE'

    def test_policy_result_with_camel_case_aliases(self) -> None:
        """Test PolicyResult handles camelCase aliases from JSON."""
        data = {
            'policyType': 'HARASSMENT',
            'score': 0.3,
            'violationResult': 'NON_VIOLATIVE',
        }
        result = PolicyResult.model_validate(data)
        assert result.policy_type == 'HARASSMENT'
        assert result.score == 0.3
        assert result.violation_result == 'NON_VIOLATIVE'

    def test_policy_result_optional_score(self) -> None:
        """Test PolicyResult with optional score (matches JS where score is optional)."""
        result = PolicyResult(
            policy_type='HATE_SPEECH',
            violation_result='NON_VIOLATIVE',
        )
        assert result.policy_type == 'HATE_SPEECH'
        assert result.score is None
        assert result.violation_result == 'NON_VIOLATIVE'

    def test_policy_result_default_violation_result(self) -> None:
        """Test PolicyResult default violation result."""
        result = PolicyResult(policy_type='DANGEROUS_CONTENT')
        assert result.violation_result == 'CLASSIFICATION_UNSPECIFIED'


class TestClassifyContentResponse:
    """Tests for ClassifyContentResponse model."""

    def test_response_from_api_format(self) -> None:
        """Test ClassifyContentResponse parsing from API response."""
        data = {
            'policyResults': [
                {
                    'policyType': 'DANGEROUS_CONTENT',
                    'score': 0.1,
                    'violationResult': 'NON_VIOLATIVE',
                },
                {
                    'policyType': 'HARASSMENT',
                    'score': 0.9,
                    'violationResult': 'VIOLATIVE',
                },
            ]
        }
        response = ClassifyContentResponse.model_validate(data)
        assert len(response.policy_results) == 2
        assert response.policy_results[0].policy_type == 'DANGEROUS_CONTENT'
        assert response.policy_results[1].violation_result == 'VIOLATIVE'

    def test_response_empty_results(self) -> None:
        """Test ClassifyContentResponse with empty results."""
        response = ClassifyContentResponse()
        assert response.policy_results == []

    def test_response_with_alias(self) -> None:
        """Test ClassifyContentResponse with policyResults alias."""
        data = {'policyResults': []}
        response = ClassifyContentResponse.model_validate(data)
        assert response.policy_results == []


class TestGuardrailsRequest:
    """Tests for GuardrailsRequest dataclass."""

    def test_request_to_dict_format(self) -> None:
        """Test GuardrailsRequest.to_dict matches JS API format."""
        request = GuardrailsRequest(
            content='Hello world',
            policies=[
                {'policy_type': 'DANGEROUS_CONTENT'},
                {'policy_type': 'HARASSMENT', 'threshold': 0.8},
            ],
        )
        result = request.to_dict()

        # Verify structure matches JS implementation
        assert 'input' in result
        assert 'text_input' in result['input']
        assert result['input']['text_input']['content'] == 'Hello world'
        assert 'policies' in result
        assert len(result['policies']) == 2
        assert result['policies'][0]['policy_type'] == 'DANGEROUS_CONTENT'
        assert result['policies'][1]['threshold'] == 0.8


class TestGuardrails:
    """Tests for Guardrails API client."""

    def test_guardrails_init(self) -> None:
        """Test Guardrails client initialization."""
        mock_creds = MagicMock()
        client = Guardrails(mock_creds, 'test-project')
        assert client._credentials == mock_creds
        assert client._project_id == 'test-project'

    def test_guardrails_init_without_project(self) -> None:
        """Test Guardrails client initialization without project ID."""
        mock_creds = MagicMock()
        client = Guardrails(mock_creds)
        assert client._project_id is None

    @pytest.mark.asyncio
    async def test_classify_content_with_metric_types(self) -> None:
        """Test classify_content with ChecksMetricType values."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = 'test-token'

        client = Guardrails(mock_creds, 'test-project')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'policyResults': [
                {
                    'policyType': 'DANGEROUS_CONTENT',
                    'score': 0.1,
                    'violationResult': 'NON_VIOLATIVE',
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.classify_content(
                content='Hello world',
                policies=[ChecksMetricType.DANGEROUS_CONTENT],
            )

            assert len(result.policy_results) == 1
            assert result.policy_results[0].policy_type == 'DANGEROUS_CONTENT'

            # Verify correct API URL
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == GUARDRAILS_URL

    @pytest.mark.asyncio
    async def test_classify_content_with_metric_config(self) -> None:
        """Test classify_content with ChecksMetricConfig including threshold."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = 'test-token'

        client = Guardrails(mock_creds, 'test-project')

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'policyResults': [
                {
                    'policyType': 'HARASSMENT',
                    'score': 0.5,
                    'violationResult': 'NON_VIOLATIVE',
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.classify_content(
                content='Test content',
                policies=[
                    ChecksMetricConfig(
                        type=ChecksMetricType.HARASSMENT,
                        threshold=0.8,
                    )
                ],
            )

            assert len(result.policy_results) == 1

            # Verify threshold was included in request
            call_args = mock_client.post.call_args
            request_body = call_args[1]['json']
            assert request_body['policies'][0]['threshold'] == 0.8

    @pytest.mark.asyncio
    async def test_classify_content_headers(self) -> None:
        """Test classify_content sends correct headers (matching JS)."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = 'test-token'

        client = Guardrails(mock_creds, 'my-project')

        mock_response = MagicMock()
        mock_response.json.return_value = {'policyResults': []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await client.classify_content(
                content='Test',
                policies=[ChecksMetricType.DANGEROUS_CONTENT],
            )

            call_args = mock_client.post.call_args
            headers = call_args[1]['headers']

            # Verify headers match JS implementation
            assert headers['Content-Type'] == 'application/json'
            assert headers['x-goog-user-project'] == 'my-project'
            assert headers['Authorization'] == 'Bearer test-token'

    @pytest.mark.asyncio
    async def test_classify_content_credential_refresh(self) -> None:
        """Test classify_content refreshes expired credentials."""
        mock_creds = MagicMock()
        mock_creds.valid = False  # Credentials need refresh
        mock_creds.token = 'refreshed-token'

        client = Guardrails(mock_creds, 'test-project')

        mock_response = MagicMock()
        mock_response.json.return_value = {'policyResults': []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await client.classify_content(
                content='Test',
                policies=[ChecksMetricType.DANGEROUS_CONTENT],
            )

            # Verify credentials were refreshed
            mock_creds.refresh.assert_called_once()


class TestGuardrailsUrl:
    """Tests for API URL constant."""

    def test_guardrails_url_matches_js(self) -> None:
        """Test GUARDRAILS_URL matches JS implementation."""
        expected = 'https://checks.googleapis.com/v1alpha/aisafety:classifyContent'
        assert GUARDRAILS_URL == expected
