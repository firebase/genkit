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
from google.genai.types import HttpOptions

import pytest
from genkit.ai import Genkit, GENKIT_CLIENT_HEADER
from genkit.blocks.embedding import embedder_action_metadata, EmbedderOptions, EmbedderSupports
from genkit.blocks.model import model_action_metadata
from genkit.core.registry import ActionKind
from genkit.plugins.google_genai import GoogleAI, VertexAI
from genkit.plugins.google_genai.google import googleai_name, vertexai_name
from genkit.plugins.google_genai.google import _inject_attribution_headers
from genkit.plugins.google_genai.models.embedder import (
    default_embedder_info,
)
from genkit.plugins.google_genai.models.gemini import (
    DEFAULT_SUPPORTS_MODEL,
    SUPPORTED_MODELS,
    google_model_info,
)
from genkit.plugins.google_genai.models.imagen import (
    SUPPORTED_MODELS as IMAGE_SUPPORTED_MODELS,
    DEFAULT_IMAGE_SUPPORT,
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
    def test_init_with_api_key(self, mock_genai_client) -> None:
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
    def test_init_from_env_var(self, mock_genai_client) -> None:
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
    def test_init_with_credentials(self, mock_genai_client) -> None:
        """Test using credentials parameter."""
        mock_credentials = MagicMock(spec=Credentials)
        plugin = GoogleAI(credentials=mock_credentials)
        mock_genai_client.assert_called_once_with(
            vertexai=False,
            api_key=ANY,
            credentials=mock_credentials,
            debug_config=None,
            http_options=_inject_attribution_headers(),
        )
        self.assertIsInstance(plugin, GoogleAI)
        self.assertFalse(plugin._vertexai)
        self.assertIsInstance(plugin._client, MagicMock)

    def test_init_raises_value_error_no_api_key(self) -> None:
        """Test using credentials parameter."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}, clear=True):
            with self.assertRaisesRegex(
                ValueError,
                'Gemini api key should be passed in plugin params or as a GEMINI_API_KEY environment variable',
            ):
                GoogleAI()


@pytest.mark.asyncio
async def test_googleai_initialize() -> None:
    """Unit tests for GoogleAI.init method."""
    api_key = 'test_api_key'
    plugin = GoogleAI(api_key=api_key)

    result = await plugin.init()

    # init returns known models and embedders
    assert len(result) > 0, 'Should initialize with known models and embedders'
    assert all(hasattr(action, 'kind') for action in result), 'All actions should have a kind'
    assert all(hasattr(action, 'name') for action in result), 'All actions should have a name'
    assert all(action.name.startswith('googleai/') for action in result), (
        "All actions should be namespaced with 'googleai/'"
    )

    # Verify we have both models and embedders
    model_actions = [a for a in result if a.kind == ActionKind.MODEL]
    embedder_actions = [a for a in result if a.kind == ActionKind.EMBEDDER]
    assert len(model_actions) > 0, 'Should have at least one model'
    assert len(embedder_actions) > 0, 'Should have at least one embedder'


@patch('genkit.plugins.google_genai.GoogleAI._resolve_model')
@pytest.mark.asyncio
async def test_googleai_resolve_action_model(mock_resolve_action, googleai_plugin_instance) -> None:
    """Test resolve action for model."""
    plugin = googleai_plugin_instance

    await plugin.resolve(action_type=ActionKind.MODEL, name='lazaro-model')
    mock_resolve_action.assert_called_once_with('lazaro-model')


@patch('genkit.plugins.google_genai.GoogleAI._resolve_embedder')
@pytest.mark.asyncio
async def test_googleai_resolve_action_embedder(mock_resolve_action, googleai_plugin_instance) -> None:
    """Test resolve action for embedder."""
    plugin = googleai_plugin_instance

    await plugin.resolve(action_type=ActionKind.EMBEDDER, name='lazaro-model')
    mock_resolve_action.assert_called_once_with('lazaro-model')


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
) -> None:
    """Tests for GoogleAI._resolve_model method."""
    plugin = googleai_plugin_instance

    mock_google_model_info.return_value = ModelInfo(
        label=f'Google AI - {model_name}',
        supports=DEFAULT_SUPPORTS_MODEL,
    )

    action = plugin._resolve_model(name=expected_model_name)

    assert action is not None
    assert action.kind == ActionKind.MODEL
    assert action.name == expected_model_name
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
) -> None:
    """Tests for GoogleAI._resolve_embedder method."""
    plugin = googleai_plugin_instance

    action = plugin._resolve_embedder(name=expected_model_name)

    assert action is not None
    assert action.kind == ActionKind.EMBEDDER
    assert action.name == expected_model_name


@pytest.mark.asyncio
async def test_googleai_list_actions(googleai_plugin_instance) -> None:
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

    result = await googleai_plugin_instance.list_actions()
    assert result == [
        model_action_metadata(
            name=googleai_name('model1'),
            info=google_model_info('model1').model_dump(),
        ),
        embedder_action_metadata(
            name=googleai_name('model2'),
            options=EmbedderOptions(
                label=default_embedder_info('model2').get('label'),
                supports=EmbedderSupports(input=default_embedder_info('model2').get('supports', {}).get('input')),
                dimensions=default_embedder_info('model2').get('dimensions'),
            ),
        ),
        model_action_metadata(
            name=googleai_name('model3'),
            info=google_model_info('model3').model_dump(),
        ),
        embedder_action_metadata(
            name=googleai_name('model3'),
            options=EmbedderOptions(
                label=default_embedder_info('model3').get('label'),
                supports=EmbedderSupports(input=default_embedder_info('model3').get('supports', {}).get('input')),
                dimensions=default_embedder_info('model3').get('dimensions'),
            ),
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
def test_inject_attribution_headers(input_options, expected_headers) -> None:
    """Tests the _inject_attribution_headers function with various inputs."""
    result = _inject_attribution_headers(input_options)
    assert isinstance(result, HttpOptions)
    assert result.headers == expected_headers


class TestVertexAIInit(unittest.TestCase):
    """Test cases for VertexAI.__init__ plugin."""

    @patch('google.genai.client.Client')
    @patch.dict(os.environ, {'GCLOUD_PROJECT': 'project'})
    def test_init_with_api_key(self, mock_genai_client) -> None:
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
    def test_init_with_credentials(self, mock_genai_client) -> None:
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
    def test_init_with_all(self, mock_genai_client) -> None:
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


@pytest.mark.asyncio
async def test_vertexai_initialize(vertexai_plugin_instance) -> None:
    """Unit tests for VertexAI.init method."""
    plugin = vertexai_plugin_instance

    result = await plugin.init()

    # init returns known models and embedders
    assert len(result) > 0, 'Should initialize with known models and embedders'
    assert all(hasattr(action, 'kind') for action in result), 'All actions should have a kind'
    assert all(hasattr(action, 'name') for action in result), 'All actions should have a name'
    assert all(action.name.startswith('vertexai/') for action in result), (
        "All actions should be namespaced with 'vertexai/'"
    )

    # Verify we have both models and embedders
    model_actions = [a for a in result if a.kind == ActionKind.MODEL]
    embedder_actions = [a for a in result if a.kind == ActionKind.EMBEDDER]
    assert len(model_actions) > 0, 'Should have at least one model'
    assert len(embedder_actions) > 0, 'Should have at least one embedder'


@patch('genkit.plugins.google_genai.VertexAI._resolve_model')
@pytest.mark.asyncio
async def test_vertexai_resolve_action_model(mock_resolve_action, vertexai_plugin_instance) -> None:
    """Test resolve action for model."""
    plugin = vertexai_plugin_instance

    await plugin.resolve(action_type=ActionKind.MODEL, name='lazaro-model')
    mock_resolve_action.assert_called_once_with('lazaro-model')


@patch('genkit.plugins.google_genai.VertexAI._resolve_embedder')
@pytest.mark.asyncio
async def test_vertexai_resolve_action_embedder(mock_resolve_action, vertexai_plugin_instance) -> None:
    """Test resolve action for embedder."""
    plugin = vertexai_plugin_instance

    await plugin.resolve(action_type=ActionKind.EMBEDDER, name='lazaro-model')
    mock_resolve_action.assert_called_once_with('lazaro-model')


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
) -> None:
    """Tests for VertexAI._resolve_model method."""
    plugin = vertexai_plugin_instance
    MagicMock(spec=Genkit)

    mock_google_model_info.return_value = ModelInfo(
        label=f'Google AI - {model_name}',
        supports=DEFAULT_SUPPORTS_MODEL,
    )

    mock_vertexai_image_model_info.return_value = ModelInfo(
        label=f'Vertex AI - {model_name}',
        supports=DEFAULT_IMAGE_SUPPORT,
    )

    action = plugin._resolve_model(name=expected_model_name)

    assert action is not None
    assert action.kind == ActionKind.MODEL
    assert action.name == expected_model_name

    if image:
        assert key in IMAGE_SUPPORTED_MODELS
    else:
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
) -> None:
    """Tests for VertexAI._resolve_embedder method."""
    plugin = vertexai_plugin_instance

    action = plugin._resolve_embedder(name=expected_model_name)

    assert action is not None
    assert action.kind == ActionKind.EMBEDDER
    assert action.name == expected_model_name


@pytest.mark.asyncio
async def test_vertexai_list_actions(vertexai_plugin_instance) -> None:
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

    result = await vertexai_plugin_instance.list_actions()
    assert result == [
        model_action_metadata(
            name=vertexai_name('model1'),
            info=google_model_info('model1').model_dump(),
        ),
        embedder_action_metadata(
            name=vertexai_name('model2_embeddings'),
            options=EmbedderOptions(
                label=default_embedder_info('model2_embeddings').get('label'),
                supports=EmbedderSupports(
                    input=default_embedder_info('model2_embeddings').get('supports', {}).get('input')
                ),
                dimensions=default_embedder_info('model2_embeddings').get('dimensions'),
            ),
        ),
        model_action_metadata(
            name=vertexai_name('model2_embeddings'),
            info=google_model_info('model2_embeddings').model_dump(),
        ),
        embedder_action_metadata(
            name=vertexai_name('model3_embedder'),
            options=EmbedderOptions(
                label=default_embedder_info('model3_embedder').get('label'),
                supports=EmbedderSupports(
                    input=default_embedder_info('model3_embedder').get('supports', {}).get('input')
                ),
                dimensions=default_embedder_info('model3_embedder').get('dimensions'),
            ),
        ),
        model_action_metadata(
            name=vertexai_name('model3_embedder'),
            info=google_model_info('model3_embedder').model_dump(),
        ),
    ]
