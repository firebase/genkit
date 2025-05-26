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
from pydantic import BaseModel
from google.genai.types import EmbedContentConfig, GenerateImagesConfigOrDict, HttpOptions

import pytest
from genkit.ai import Genkit, GENKIT_CLIENT_HEADER
from genkit.blocks.embedding import embedder_action_metadata
from genkit.blocks.model import model_action_metadata
from genkit.core.registry import ActionKind
from genkit.plugins.google_genai import (
    GoogleAI,
    VertexAI,
    googleai_name,
    vertexai_name,
)
from genkit.plugins.google_genai.google import _inject_attribution_headers
from genkit.plugins.google_genai.models.embedder import (
    GeminiEmbeddingModels,
    VertexEmbeddingModels,
    default_embedder_info,
)
from genkit.plugins.google_genai.models.gemini import (
    DEFAULT_SUPPORTS_MODEL,
    GeminiConfigSchema,
    SUPPORTED_MODELS,
    GoogleAIGeminiVersion,
    VertexAIGeminiVersion,
    google_model_info,
)
from genkit.plugins.google_genai.models.imagen import (
    SUPPORTED_MODELS as IMAGE_SUPPORTED_MODELS,
    DEFAULT_IMAGE_SUPPORT,
    ImagenVersion,
)
from genkit.types import (
    ModelInfo,
)


@pytest.fixture
@patch('google.genai.client.Client')
def googleai_plugin_instance(client):
    """GoogleAI fixture."""
    api_key = 'test_api_key'
    return GoogleAI(api_key=api_key)


class TestGoogleAIInit(unittest.TestCase):
    """Test cases for __init__ plugin."""

    @patch('google.genai.client.Client')
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


def test_googleai_initialize():
    """Unit tests for GoogleAI.initialize method."""
    api_key = 'test_api_key'
    plugin = GoogleAI(api_key=api_key)
    ai_mock = MagicMock(spec=Genkit)

    plugin.initialize(ai_mock)

    assert ai_mock.define_model.call_count == len(GoogleAIGeminiVersion)
    assert ai_mock.define_embedder.call_count == len(GeminiEmbeddingModels)

    for version in GoogleAIGeminiVersion:
        ai_mock.define_model.assert_any_call(
            name=googleai_name(version),
            fn=ANY,
            metadata=ANY,
            config_schema=GeminiConfigSchema,
        )

    for version in GeminiEmbeddingModels:
        ai_mock.define_embedder.assert_any_call(
            name=googleai_name(version),
            fn=ANY,
            metadata=ANY,
            config_schema=EmbedContentConfig,
        )


@patch('genkit.plugins.google_genai.GoogleAI._resolve_model')
def test_googleai_resolve_action_model(mock_resolve_action, googleai_plugin_instance):
    """Test resolve action for model."""
    plugin = googleai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin.resolve_action(ai=ai_mock, kind=ActionKind.MODEL, name='lazaro-model')
    mock_resolve_action.assert_called_once_with(ai_mock, 'lazaro-model')


@patch('genkit.plugins.google_genai.GoogleAI._resolve_embedder')
def test_googleai_resolve_action_embedder(mock_resolve_action, googleai_plugin_instance):
    """Test resolve action for embedder."""
    plugin = googleai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin.resolve_action(ai=ai_mock, kind=ActionKind.EMBEDDER, name='lazaro-model')
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
    googleai_plugin_instance,
):
    """Tests for GoogleAI._resolve_model method."""
    plugin = googleai_plugin_instance
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
    'model_name, expected_model_name, clean_name',
    [
        ('gemini-pro-deluxe-max', 'googleai/gemini-pro-deluxe-max', 'gemini-pro-deluxe-max'),
        ('googleai/gemini-pro-deluxe-max', 'googleai/gemini-pro-deluxe-max', 'gemini-pro-deluxe-max'),
    ],
)
def test_googleai__resolve_embedder(
    model_name,
    expected_model_name,
    clean_name,
    googleai_plugin_instance,
):
    """Tests for GoogleAI._resolve_embedder method."""
    plugin = googleai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin._resolve_embedder(
        ai=ai_mock,
        name=model_name,
    )

    ai_mock.define_embedder.assert_called_once_with(
        name=expected_model_name, fn=ANY, config_schema=EmbedContentConfig, metadata=default_embedder_info(clean_name)
    )


def test_googleai_list_actions(googleai_plugin_instance):
    """Unit test for list actions."""

    class MockModel(BaseModel):
        """mock."""

        supported_actions: list[str]
        name: str

    models_return_value = [
        MockModel(supported_actions=['generateContent'], name='models/model1'),
        MockModel(supported_actions=['embedContent'], name='models/model2'),
        MockModel(supported_actions=['generateContent', 'embedContent'], name='models/model3'),
    ]

    mock_client = MagicMock()
    mock_client.models.list.return_value = models_return_value
    googleai_plugin_instance._client = mock_client

    result = googleai_plugin_instance.list_actions
    assert result == [
        model_action_metadata(
            name=googleai_name('model1'),
            info=google_model_info('model1').model_dump(),
            config_schema=GeminiConfigSchema,
        ),
        embedder_action_metadata(
            name=googleai_name('model2'),
            info=default_embedder_info('model2'),
            config_schema=EmbedContentConfig,
        ),
        model_action_metadata(
            name=googleai_name('model3'),
            info=google_model_info('model3').model_dump(),
            config_schema=GeminiConfigSchema,
        ),
        embedder_action_metadata(
            name=googleai_name('model3'),
            info=default_embedder_info('model3'),
            config_schema=EmbedContentConfig,
        ),
    ]


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


class TestVertexAIInit(unittest.TestCase):
    """Test cases for VertexAI.__init__ plugin."""

    @patch('google.genai.client.Client')
    @patch.dict(os.environ, {'GCLOUD_PROJECT': 'project'})
    def test_init_with_api_key(self, mock_genai_client):
        """Test using api_key parameter."""
        api_key = 'test_api_key'
        plugin = VertexAI(api_key=api_key)
        mock_genai_client.assert_called_once_with(
            vertexai=True,
            api_key=api_key,
            credentials=None,
            debug_config=None,
            http_options=_inject_attribution_headers(),
            project='project',
            location='us-central1',
        )
        self.assertIsInstance(plugin, VertexAI)
        self.assertTrue(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)

    @patch('google.genai.client.Client')
    @patch.dict(os.environ, {'GCLOUD_PROJECT': 'project'})
    def test_init_with_credentials(self, mock_genai_client):
        """Test using credentials parameter."""
        mock_credentials = MagicMock(spec=Credentials)
        plugin = VertexAI(credentials=mock_credentials)
        mock_genai_client.assert_called_once_with(
            vertexai=True,
            api_key=None,
            credentials=mock_credentials,
            debug_config=None,
            http_options=_inject_attribution_headers(),
            project='project',
            location='us-central1',
        )
        self.assertIsInstance(plugin, VertexAI)
        self.assertTrue(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)

    @patch('google.genai.client.Client')
    def test_init_with_all(self, mock_genai_client):
        """Test using credentials parameter."""
        mock_credentials = MagicMock(spec=Credentials)
        api_key = 'test_api_key'
        plugin = VertexAI(
            credentials=mock_credentials,
            api_key=api_key,
            project='project',
            location='location',
        )
        mock_genai_client.assert_called_once_with(
            vertexai=True,
            api_key=api_key,
            credentials=mock_credentials,
            debug_config=None,
            http_options=_inject_attribution_headers(),
            project='project',
            location='location',
        )
        self.assertIsInstance(plugin, VertexAI)
        self.assertTrue(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)


@pytest.fixture
@patch('google.genai.client.Client')
def vertexai_plugin_instance(client):
    """VertexAI fixture."""
    return VertexAI()


def test_vertexai_initialize(vertexai_plugin_instance):
    """Unit tests for VertexAI.initialize method."""
    plugin = vertexai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin.initialize(ai_mock)

    assert ai_mock.define_model.call_count == len(VertexAIGeminiVersion) + len(ImagenVersion)
    assert ai_mock.define_embedder.call_count == len(VertexEmbeddingModels)

    for version in VertexAIGeminiVersion:
        ai_mock.define_model.assert_any_call(
            name=vertexai_name(version),
            fn=ANY,
            metadata=ANY,
            config_schema=GeminiConfigSchema,
        )

    for version in ImagenVersion:
        ai_mock.define_model.assert_any_call(
            name=vertexai_name(version), fn=ANY, metadata=ANY, config_schema=GenerateImagesConfigOrDict
        )

    for version in VertexEmbeddingModels:
        ai_mock.define_embedder.assert_any_call(
            name=vertexai_name(version),
            fn=ANY,
            metadata=ANY,
            config_schema=EmbedContentConfig,
        )


@patch('genkit.plugins.google_genai.VertexAI._resolve_model')
def test_vertexai_resolve_action_model(mock_resolve_action, vertexai_plugin_instance):
    """Test resolve action for model."""
    plugin = vertexai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin.resolve_action(ai=ai_mock, kind=ActionKind.MODEL, name='lazaro-model')
    mock_resolve_action.assert_called_once_with(ai_mock, 'lazaro-model')


@patch('genkit.plugins.google_genai.VertexAI._resolve_embedder')
def test_vertexai_resolve_action_embedder(mock_resolve_action, vertexai_plugin_instance):
    """Test resolve action for embedder."""
    plugin = vertexai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin.resolve_action(ai=ai_mock, kind=ActionKind.EMBEDDER, name='lazaro-model')
    mock_resolve_action.assert_called_once_with(ai_mock, 'lazaro-model')


@patch(
    'genkit.plugins.google_genai.models.gemini.google_model_info',
    new_callable=MagicMock,
)
@patch(
    'genkit.plugins.google_genai.models.imagen.vertexai_image_model_info',
    new_callable=MagicMock,
)
@pytest.mark.parametrize(
    'model_name, expected_model_name, key, image',
    [
        (
            'gemini-pro-deluxe-max',
            'vertexai/gemini-pro-deluxe-max',
            'gemini-pro-deluxe-max',
            False,
        ),
        (
            'vertexai/gemini-pro-deluxe-max',
            'vertexai/gemini-pro-deluxe-max',
            'gemini-pro-deluxe-max',
            False,
        ),
        (
            'vertexai/image-gemini-pro-deluxe-max',
            'vertexai/image-gemini-pro-deluxe-max',
            'image-gemini-pro-deluxe-max',
            True,
        ),
        (
            'image-gemini-pro-deluxe-max',
            'vertexai/image-gemini-pro-deluxe-max',
            'image-gemini-pro-deluxe-max',
            True,
        ),
        (
            'gemini-pro-deluxe-max-image',
            'vertexai/gemini-pro-deluxe-max-image',
            'gemini-pro-deluxe-max-image',
            False,
        ),
    ],
)
def test_vertexai__resolve_model(
    mock_google_model_info,
    mock_vertexai_image_model_info,
    model_name,
    expected_model_name,
    key,
    image,
    vertexai_plugin_instance,
):
    """Tests for VertexAI._resolve_model method."""
    plugin = vertexai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    mock_google_model_info.return_value = ModelInfo(
        label=f'Google AI - {model_name}',
        supports=DEFAULT_SUPPORTS_MODEL,
    )

    mock_vertexai_image_model_info.return_value = ModelInfo(
        label=f'Vertex AI - {model_name}',
        supports=DEFAULT_IMAGE_SUPPORT,
    )

    plugin._resolve_model(
        ai=ai_mock,
        name=model_name,
    )

    if image:
        ai_mock.define_model.assert_called_once_with(
            name=expected_model_name,
            fn=ANY,
            metadata=ANY,
            config_schema=GenerateImagesConfigOrDict,
        )
        assert key in IMAGE_SUPPORTED_MODELS
    else:
        ai_mock.define_model.assert_called_once_with(
            name=expected_model_name,
            fn=ANY,
            metadata=ANY,
            config_schema=GeminiConfigSchema,
        )
        assert key in SUPPORTED_MODELS


@pytest.mark.parametrize(
    'model_name, expected_model_name, clean_name',
    [
        (
            'gemini-pro-deluxe-max',
            'vertexai/gemini-pro-deluxe-max',
            'gemini-pro-deluxe-max',
        ),
        (
            'vertexai/gemini-pro-deluxe-max',
            'vertexai/gemini-pro-deluxe-max',
            'gemini-pro-deluxe-max',
        ),
    ],
)
def test_vertexai__resolve_embedder(
    model_name,
    expected_model_name,
    clean_name,
    vertexai_plugin_instance,
):
    """Tests for VertexAI._resolve_embedder method."""
    plugin = vertexai_plugin_instance
    ai_mock = MagicMock(spec=Genkit)

    plugin._resolve_embedder(
        ai=ai_mock,
        name=model_name,
    )

    ai_mock.define_embedder.assert_called_once_with(
        name=expected_model_name, fn=ANY, config_schema=EmbedContentConfig, metadata=default_embedder_info(clean_name)
    )


def test_vertexai_list_actions(vertexai_plugin_instance):
    """Unit test for list actions."""

    class MockModel(BaseModel):
        """mock."""

        name: str

    models_return_value = [
        MockModel(name='publishers/google/models/model1'),
        MockModel(name='publishers/google/models/model2_embeddings'),
        MockModel(name='publishers/google/models/model3_embedder'),
    ]

    mock_client = MagicMock()
    mock_client.models.list.return_value = models_return_value
    vertexai_plugin_instance._client = mock_client

    result = vertexai_plugin_instance.list_actions
    assert result == [
        model_action_metadata(
            name=vertexai_name('model1'),
            info=google_model_info('model1').model_dump(),
            config_schema=GeminiConfigSchema,
        ),
        embedder_action_metadata(
            name=vertexai_name('model2_embeddings'),
            info=default_embedder_info('model2_embeddings'),
            config_schema=EmbedContentConfig,
        ),
        model_action_metadata(
            name=vertexai_name('model2_embeddings'),
            info=google_model_info('model2_embeddings').model_dump(),
            config_schema=GeminiConfigSchema,
        ),
        embedder_action_metadata(
            name=vertexai_name('model3_embedder'),
            info=default_embedder_info('model3_embedder'),
            config_schema=EmbedContentConfig,
        ),
        model_action_metadata(
            name=vertexai_name('model3_embedder'),
            info=google_model_info('model3_embedder').model_dump(),
            config_schema=GeminiConfigSchema,
        ),
    ]
