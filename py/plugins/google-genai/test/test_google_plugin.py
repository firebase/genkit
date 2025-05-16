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

"""Unit-Tests for GoogleAI & VertexAI plugin."""

import sys  # noqa
import os

import unittest
from unittest.mock import MagicMock, patch, ANY

from google.auth.credentials import Credentials
from google.genai.types import HttpOptions

import pytest
from genkit.ai import Genkit, GENKIT_CLIENT_HEADER
from genkit.core.registry import ActionKind
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.google_genai.google import _inject_attribution_headers
from genkit.plugins.google_genai.models.gemini import (
    DEFAULT_SUPPORTS_MODEL,
    GeminiConfigSchema,
    SUPPORTED_MODELS,
)
from genkit.types import (
    ModelInfo,
)


class TestGoogleAIInit(unittest.TestCase):
    """Test cases for __init__ plugin."""

    @patch('google.genai.client.Client')
    @patch.dict(os.environ, {})
    def test_init_with_api_key(self, mock_genai_client):
        """Test using api_key parameter."""
        api_key = 'test_api_key'
        plugin = GoogleAI(api_key=api_key)
        mock_genai_client.assert_called_once_with(
            vertexai=False,
            api_key=api_key,
            credentials=None,
            debug_config=None,
            http_options=_inject_attribution_headers(),
        )
        self.assertIsInstance(plugin, GoogleAI)
        self.assertFalse(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)

    @patch('google.genai.client.Client')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'env_api_key'})
    def test_init_from_env_var(self, mock_genai_client):
        """Test using env var for api_key."""
        plugin = GoogleAI()
        mock_genai_client.assert_called_once_with(
            vertexai=False,
            api_key='env_api_key',
            credentials=None,
            debug_config=None,
            http_options=_inject_attribution_headers(),
        )
        self.assertIsInstance(plugin, GoogleAI)
        self.assertFalse(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)

    @patch('google.genai.client.Client')
    def test_init_with_credentials(self, mock_genai_client):
        """Test using credentials parameter."""
        mock_credentials = MagicMock(spec=Credentials)
        plugin = GoogleAI(credentials=mock_credentials)
        mock_genai_client.assert_called_once_with(
            vertexai=False,
            api_key=None,
            credentials=mock_credentials,
            debug_config=None,
            http_options=_inject_attribution_headers(),
        )
        self.assertIsInstance(plugin, GoogleAI)
        self.assertFalse(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)

    def test_init_raises_value_error_no_api_key(self):
        """Test using credentials parameter."""
        with self.assertRaisesRegex(
            ValueError,
            'Gemini api key should be passed in plugin params or as a GEMINI_API_KEY environment variable',
        ):
            GoogleAI()


@patch('genkit.plugins.google_genai.GoogleAI._resolve_model')
def test_googleai_resolve_action_model(mock_resolve_action):
    """Test resolve action for model."""
    api_key = 'test_api_key'
    plugin = GoogleAI(api_key=api_key)
    ai_mock = MagicMock(spec=Genkit)

    plugin.resolve_action(ai=ai_mock, type=ActionKind.MODEL, name='lazaro-model')
    mock_resolve_action.assert_called_once_with(ai_mock, 'lazaro-model')


@patch('genkit.plugins.google_genai.GoogleAI._resolve_embedder')
def test_googleai_resolve_action_embedder(mock_resolve_action):
    """Test resolve action for embedder."""
    api_key = 'test_api_key'
    plugin = GoogleAI(api_key=api_key)
    ai_mock = MagicMock(spec=Genkit)

    plugin.resolve_action(ai=ai_mock, type=ActionKind.EMBEDDER, name='lazaro-model')
    mock_resolve_action.assert_called_once_with(ai_mock, 'lazaro-model')


@patch('genkit.plugins.google_genai.models.gemini.google_model_info')
@pytest.mark.parametrize(
    'model_name, expected_model_name, key',
    [
        (
            'gemini-pro-deluxe-max',
            'googleai/gemini-pro-deluxe-max',
            'gemini-pro-deluxe-max',
        ),
        (
            'googleai/gemini-pro-deluxe-max',
            'googleai/gemini-pro-deluxe-max',
            'gemini-pro-deluxe-max',
        ),
    ],
)
def test_googleai__resolve_model(
    mock_google_model_info,
    model_name,
    expected_model_name,
    key,
):
    """Tests for GoogleAI._resolve_model method."""
    api_key = 'test_api_key'
    plugin = GoogleAI(api_key=api_key)
    ai_mock = MagicMock(spec=Genkit)

    mock_google_model_info.return_value = ModelInfo(
        label=f'Google AI - {model_name}',
        supports=DEFAULT_SUPPORTS_MODEL,
    )

    plugin._resolve_model(
        ai=ai_mock,
        name=model_name,
    )

    ai_mock.define_model.assert_called_once_with(
        name=expected_model_name,
        fn=ANY,
        metadata=ANY,
        config_schema=GeminiConfigSchema,
    )
    assert key in SUPPORTED_MODELS


@pytest.mark.parametrize(
    'model_name, expected_model_name',
    [
        (
            'gemini-pro-deluxe-max',
            'googleai/gemini-pro-deluxe-max',
        ),
        (
            'googleai/gemini-pro-deluxe-max',
            'googleai/gemini-pro-deluxe-max',
        ),
    ],
)
def test_googleai__resolve_embedder(
    model_name,
    expected_model_name,
):
    """Tests for GoogleAI._resolve_embedder method."""
    api_key = 'test_api_key'
    plugin = GoogleAI(api_key=api_key)
    ai_mock = MagicMock(spec=Genkit)

    plugin._resolve_embedder(
        ai=ai_mock,
        name=model_name,
    )

    ai_mock.define_embedder.assert_called_once_with(
        name=expected_model_name,
        fn=ANY,
    )


@pytest.mark.parametrize(
    'input_options, expected_headers',
    [
        (
            None,
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            {},
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            {'headers': {'existing-header': 'value'}},
            {
                'existing-header': 'value',
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            {'headers': {'x-goog-api-client': 'initial-client'}},
            {
                'x-goog-api-client': f'initial-client {GENKIT_CLIENT_HEADER}',
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            {'headers': {'user-agent': 'initial-agent'}},
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': f'initial-agent {GENKIT_CLIENT_HEADER}',
            },
        ),
        (
            {'headers': {'x-goog-api-client': 'old', 'user-agent': 'old-ua'}},
            {
                'x-goog-api-client': f'old {GENKIT_CLIENT_HEADER}',
                'user-agent': f'old-ua {GENKIT_CLIENT_HEADER}',
            },
        ),
        (
            HttpOptions(),
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            HttpOptions(headers={'other': 'value'}),
            {
                'other': 'value',
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            HttpOptions(headers={'x-goog-api-client': 'initial'}),
            {
                'x-goog-api-client': f'initial {GENKIT_CLIENT_HEADER}',
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            HttpOptions(headers={'user-agent': 'initial-u'}),
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': f'initial-u {GENKIT_CLIENT_HEADER}',
            },
        ),
        (
            HttpOptions(headers={'x-goog-api-client': 'pre', 'user-agent': 'pre-u'}),
            {
                'x-goog-api-client': f'pre {GENKIT_CLIENT_HEADER}',
                'user-agent': f'pre-u {GENKIT_CLIENT_HEADER}',
            },
        ),
        (
            HttpOptions(timeout=10),
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            {'timeout': 5},
            {
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
        (
            {'headers': {'one': '1'}},
            {
                'one': '1',
                'x-goog-api-client': GENKIT_CLIENT_HEADER,
                'user-agent': GENKIT_CLIENT_HEADER,
            },
        ),
    ],
)
def test_inject_attribution_headers(input_options, expected_headers):
    """Tests the _inject_attribution_headers function with various inputs."""
    result = _inject_attribution_headers(input_options)
    assert isinstance(result, HttpOptions)
    assert result.headers == expected_headers
