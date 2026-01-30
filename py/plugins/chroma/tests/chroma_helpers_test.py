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

"""Tests for Chroma helper functions.

These tests verify parity with the JS implementation in:
js/plugins/chroma/src/index.ts (createChromaCollection, deleteChromaCollection)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.plugins.chroma.plugin import (
    _get_client,
    _get_client_async,
    create_chroma_collection,
    delete_chroma_collection,
)


class TestGetClient:
    """Tests for _get_client function matching JS ChromaClient instantiation."""

    def test_get_client_with_no_params(self) -> None:
        """Test creating client with no params (ephemeral client)."""
        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.Client.return_value = mock_client

            result = _get_client(None)

            mock_chromadb.Client.assert_called_once()
            assert result == mock_client

    def test_get_client_with_path(self) -> None:
        """Test creating persistent client with path (matches JS)."""
        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client

            result = _get_client({'path': '/data/chroma'})

            mock_chromadb.PersistentClient.assert_called_once_with(path='/data/chroma')
            assert result == mock_client

    def test_get_client_with_host_port(self) -> None:
        """Test creating HTTP client (matches JS remote Chroma)."""
        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.HttpClient.return_value = mock_client

            _get_client({
                'host': 'chroma.example.com',
                'port': 8080,
            })

            mock_chromadb.HttpClient.assert_called_once()
            call_kwargs = mock_chromadb.HttpClient.call_args[1]
            assert call_kwargs['host'] == 'chroma.example.com'
            assert call_kwargs['port'] == 8080

    def test_get_client_with_headers(self) -> None:
        """Test creating HTTP client with headers."""
        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.HttpClient.return_value = mock_client

            _get_client({
                'host': 'chroma.example.com',
                'headers': {'Authorization': 'Bearer token'},
            })

            call_kwargs = mock_chromadb.HttpClient.call_args[1]
            assert call_kwargs['headers'] == {'Authorization': 'Bearer token'}


class TestGetClientAsync:
    """Tests for _get_client_async matching JS resolve() function."""

    @pytest.mark.asyncio
    async def test_get_client_async_with_dict(self) -> None:
        """Test async client creation with dict params."""
        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client

            result = await _get_client_async({'path': '/data/chroma'})

            assert result == mock_client

    @pytest.mark.asyncio
    async def test_get_client_async_with_callable(self) -> None:
        """Test async client creation with async callable (matches JS Promise<ChromaClientParams>)."""

        async def get_params() -> dict:
            return {'path': '/async/path'}

        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client

            await _get_client_async(get_params)

            mock_chromadb.PersistentClient.assert_called_once_with(path='/async/path')

    @pytest.mark.asyncio
    async def test_get_client_async_with_none(self) -> None:
        """Test async client creation with None."""
        with patch('genkit.plugins.chroma.plugin.chromadb') as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.Client.return_value = mock_client

            await _get_client_async(None)

            mock_chromadb.Client.assert_called_once()


class TestCreateChromaCollection:
    """Tests for create_chroma_collection matching JS createChromaCollection."""

    @pytest.mark.asyncio
    async def test_create_collection_basic(self) -> None:
        """Test basic collection creation."""
        with patch('genkit.plugins.chroma.plugin._get_client_async', new_callable=AsyncMock) as mock_get_client:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.create_collection.return_value = mock_collection
            mock_get_client.return_value = mock_client

            result = await create_chroma_collection(name='test-collection')

            mock_client.create_collection.assert_called_once_with(
                name='test-collection',
                metadata=None,
            )
            assert result == mock_collection

    @pytest.mark.asyncio
    async def test_create_collection_with_metadata(self) -> None:
        """Test collection creation with metadata (matching JS)."""
        with patch('genkit.plugins.chroma.plugin._get_client_async', new_callable=AsyncMock) as mock_get_client:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.create_collection.return_value = mock_collection
            mock_get_client.return_value = mock_client

            await create_chroma_collection(
                name='test-collection',
                metadata={'hnsw:space': 'cosine'},
            )

            mock_client.create_collection.assert_called_once_with(
                name='test-collection',
                metadata={'hnsw:space': 'cosine'},
            )

    @pytest.mark.asyncio
    async def test_create_collection_with_client_params(self) -> None:
        """Test collection creation with client params."""
        with patch('genkit.plugins.chroma.plugin._get_client_async', new_callable=AsyncMock) as mock_get_client:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.create_collection.return_value = mock_collection
            mock_get_client.return_value = mock_client

            await create_chroma_collection(
                name='test-collection',
                client_params={'path': '/data'},
            )

            mock_get_client.assert_called_once_with({'path': '/data'})


class TestDeleteChromaCollection:
    """Tests for delete_chroma_collection matching JS deleteChromaCollection."""

    @pytest.mark.asyncio
    async def test_delete_collection_basic(self) -> None:
        """Test basic collection deletion."""
        with patch('genkit.plugins.chroma.plugin._get_client_async', new_callable=AsyncMock) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await delete_chroma_collection(name='test-collection')

            mock_client.delete_collection.assert_called_once_with(name='test-collection')

    @pytest.mark.asyncio
    async def test_delete_collection_with_client_params(self) -> None:
        """Test collection deletion with client params."""
        with patch('genkit.plugins.chroma.plugin._get_client_async', new_callable=AsyncMock) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            await delete_chroma_collection(
                name='test-collection',
                client_params={'host': 'chroma.example.com'},
            )

            mock_get_client.assert_called_once()
