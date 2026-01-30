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

"""Tests for Pinecone helper functions.

These tests verify parity with the JS implementation in:
js/plugins/pinecone/src/index.ts (createPineconeIndex, describePineconeIndex, deletePineconeIndex)
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from genkit.plugins.pinecone.plugin import (
    _get_client,
    create_pinecone_index,
    delete_pinecone_index,
    describe_pinecone_index,
)


class TestGetClient:
    """Tests for _get_client function matching JS Pinecone client instantiation."""

    def test_get_client_with_api_key_in_params(self) -> None:
        """Test creating client with API key in params."""
        with patch('genkit.plugins.pinecone.plugin.PineconeClient') as mock_pinecone:
            mock_client = MagicMock()
            mock_pinecone.return_value = mock_client

            result = _get_client({'api_key': 'my-api-key'})

            mock_pinecone.assert_called_once_with(api_key='my-api-key')
            assert result == mock_client

    def test_get_client_with_env_var(self) -> None:
        """Test creating client with PINECONE_API_KEY env var (matches JS getDefaultConfig)."""
        with (
            patch('genkit.plugins.pinecone.plugin.PineconeClient') as mock_pinecone,
            patch.dict(os.environ, {'PINECONE_API_KEY': 'env-api-key'}),
        ):
            mock_client = MagicMock()
            mock_pinecone.return_value = mock_client

            _get_client(None)

            mock_pinecone.assert_called_once_with(api_key='env-api-key')

    def test_get_client_raises_without_api_key(self) -> None:
        """Test error when no API key is available (matches JS getDefaultConfig)."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove PINECONE_API_KEY if it exists
            if 'PINECONE_API_KEY' in os.environ:
                del os.environ['PINECONE_API_KEY']

            with pytest.raises(ValueError, match='Pinecone API key must be provided'):
                _get_client(None)


class TestCreatePineconeIndex:
    """Tests for create_pinecone_index matching JS createPineconeIndex."""

    @pytest.mark.asyncio
    async def test_create_index_basic(self) -> None:
        """Test basic index creation."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await create_pinecone_index(
                name='test-index',
                dimension=768,
            )

            mock_client.create_index.assert_called_once()
            call_kwargs = mock_client.create_index.call_args[1]
            assert call_kwargs['name'] == 'test-index'
            assert call_kwargs['dimension'] == 768
            assert call_kwargs['metric'] == 'cosine'  # default

    @pytest.mark.asyncio
    async def test_create_index_with_metric(self) -> None:
        """Test index creation with custom metric."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await create_pinecone_index(
                name='test-index',
                dimension=768,
                metric='euclidean',
            )

            call_kwargs = mock_client.create_index.call_args[1]
            assert call_kwargs['metric'] == 'euclidean'

    @pytest.mark.asyncio
    async def test_create_index_with_client_params(self) -> None:
        """Test index creation with client params."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await create_pinecone_index(
                name='test-index',
                dimension=768,
                client_params={'api_key': 'custom-key'},
            )

            mock_get_client.assert_called_once_with({'api_key': 'custom-key'})

    @pytest.mark.asyncio
    async def test_create_index_returns_info(self) -> None:
        """Test index creation returns info dict."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = await create_pinecone_index(
                name='my-index',
                dimension=512,
                metric='dotproduct',
            )

            assert result['name'] == 'my-index'
            assert result['dimension'] == 512
            assert result['metric'] == 'dotproduct'


class TestDescribePineconeIndex:
    """Tests for describe_pinecone_index matching JS describePineconeIndex."""

    @pytest.mark.asyncio
    async def test_describe_index_basic(self) -> None:
        """Test basic index description."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_description = MagicMock()
            mock_description.name = 'test-index'
            mock_description.dimension = 768
            mock_description.metric = 'cosine'
            mock_description.host = 'test-index.svc.pinecone.io'
            mock_description.status = {'ready': True}
            mock_client.describe_index.return_value = mock_description
            mock_get_client.return_value = mock_client

            result = await describe_pinecone_index(name='test-index')

            mock_client.describe_index.assert_called_once_with('test-index')
            assert result['name'] == 'test-index'
            assert result['dimension'] == 768
            assert result['metric'] == 'cosine'
            assert result['host'] == 'test-index.svc.pinecone.io'

    @pytest.mark.asyncio
    async def test_describe_index_with_client_params(self) -> None:
        """Test index description with client params."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_description = MagicMock()
            mock_description.name = 'test-index'
            mock_description.dimension = 768
            mock_description.metric = 'cosine'
            mock_description.host = 'test-index.svc.pinecone.io'
            mock_description.status = {'ready': True}
            mock_client.describe_index.return_value = mock_description
            mock_get_client.return_value = mock_client

            await describe_pinecone_index(
                name='test-index',
                client_params={'api_key': 'custom-key'},
            )

            mock_get_client.assert_called_once_with({'api_key': 'custom-key'})


class TestDeletePineconeIndex:
    """Tests for delete_pinecone_index matching JS deletePineconeIndex."""

    @pytest.mark.asyncio
    async def test_delete_index_basic(self) -> None:
        """Test basic index deletion."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await delete_pinecone_index(name='test-index')

            mock_client.delete_index.assert_called_once_with('test-index')

    @pytest.mark.asyncio
    async def test_delete_index_with_client_params(self) -> None:
        """Test index deletion with client params."""
        with patch('genkit.plugins.pinecone.plugin._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await delete_pinecone_index(
                name='test-index',
                client_params={'api_key': 'custom-key'},
            )

            mock_get_client.assert_called_once_with({'api_key': 'custom-key'})
