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

"""Tests for the Pinecone indexer functionality.

These tests verify parity with the JS implementation in:
js/plugins/pinecone/src/index.ts (configurePineconeIndexer function)
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.blocks.retriever import IndexerRequest
from genkit.core.typing import DocumentPart, TextPart
from genkit.plugins.pinecone.plugin import (
    CONTENT_KEY,
    CONTENT_TYPE_KEY,
    PineconeIndexer,
    PineconeIndexerOptions,
    _md5_hash,
)
from genkit.types import DocumentData


class TestPineconeIndexerOptions:
    """Tests for PineconeIndexerOptions matching JS PineconeIndexerOptionsSchema."""

    def test_default_namespace_is_none(self) -> None:
        """Test default namespace is None (matches JS optional)."""
        options = PineconeIndexerOptions()
        assert options.namespace is None

    def test_namespace_option(self) -> None:
        """Test namespace option (matches JS)."""
        options = PineconeIndexerOptions(namespace='my-namespace')
        assert options.namespace == 'my-namespace'


class TestMd5Hash:
    """Tests for _md5_hash function matching JS Md5.hashStr."""

    def test_md5_hash_produces_correct_hash(self) -> None:
        """Test MD5 hash matches expected value."""
        content = 'Hello, world!'
        result = _md5_hash(content)

        # Verify it's a valid MD5 hash (32 hex characters)
        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)

    def test_md5_hash_matches_standard_implementation(self) -> None:
        """Test MD5 hash matches Python's hashlib implementation."""
        content = 'Test content for hashing'
        result = _md5_hash(content)
        expected = hashlib.md5(content.encode('utf-8')).hexdigest()
        assert result == expected

    def test_md5_hash_consistent_for_same_input(self) -> None:
        """Test MD5 hash is deterministic (same input -> same output)."""
        content = 'Some document content'
        hash1 = _md5_hash(content)
        hash2 = _md5_hash(content)
        assert hash1 == hash2


class TestContentKeys:
    """Tests for content key constants matching JS."""

    def test_content_key_value(self) -> None:
        """Test CONTENT_KEY matches JS."""
        assert CONTENT_KEY == '_content'

    def test_content_type_key_value(self) -> None:
        """Test CONTENT_TYPE_KEY matches JS CONTENT_TYPE."""
        # JS uses '_contentType', Python uses '_content_type'
        # Both are valid as they're internal storage keys
        assert CONTENT_TYPE_KEY == '_content_type'


class TestPineconeIndexer:
    """Tests for PineconeIndexer class matching JS configurePineconeIndexer."""

    def test_indexer_initialization(self) -> None:
        """Test indexer initialization with required params."""
        mock_registry = MagicMock()
        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='googleai/text-embedding-004',
        )

        assert indexer._index_id == 'test-index'
        assert indexer._embedder == 'googleai/text-embedding-004'

    def test_indexer_with_embedder_options(self) -> None:
        """Test indexer with embedder options (matches JS)."""
        mock_registry = MagicMock()
        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            embedder_options={'dimension': 768},
        )

        assert indexer._embedder_options == {'dimension': 768}

    def test_indexer_with_client_params(self) -> None:
        """Test indexer with client params (matches JS clientParams)."""
        mock_registry = MagicMock()
        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        assert indexer._client_params == {'api_key': 'test-key'}

    def test_indexer_custom_content_key(self) -> None:
        """Test contentKey option (matches JS)."""
        mock_registry = MagicMock()
        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            content_key='custom_content',
        )

        assert indexer._content_key == 'custom_content'

    def test_indexer_default_content_key(self) -> None:
        """Test default contentKey is '_content' (matches JS)."""
        mock_registry = MagicMock()
        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
        )

        assert indexer._content_key == CONTENT_KEY

    @pytest.mark.asyncio
    async def test_indexer_upserts_vectors(self) -> None:
        """Test indexer upserts vectors to Pinecone (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()

        with patch.object(indexer, '_get_index', return_value=mock_index):
            request = IndexerRequest(
                documents=[
                    DocumentData(content=[DocumentPart(root=TextPart(text='Document content'))]),
                ],
            )

            await indexer.index(request)

            # Verify upsert was called (matches JS)
            mock_index.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_indexer_generates_md5_ids(self) -> None:
        """Test indexer generates MD5 IDs for vectors (matching JS Md5.hashStr)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()

        with patch.object(indexer, '_get_index', return_value=mock_index):
            request = IndexerRequest(
                documents=[
                    DocumentData(content=[DocumentPart(root=TextPart(text='Test content'))]),
                ],
            )

            await indexer.index(request)

            # Verify IDs are MD5 hashes (32 hex chars)
            call_args = mock_index.upsert.call_args
            vectors = call_args[1]['vectors']
            assert all(len(v['id']) == 32 for v in vectors)
            assert all(c in '0123456789abcdef' for v in vectors for c in v['id'])

    @pytest.mark.asyncio
    async def test_indexer_stores_content_in_metadata(self) -> None:
        """Test indexer stores content in metadata (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()

        with patch.object(indexer, '_get_index', return_value=mock_index):
            request = IndexerRequest(
                documents=[
                    DocumentData(content=[DocumentPart(root=TextPart(text='Document content'))]),
                ],
            )

            await indexer.index(request)

            call_args = mock_index.upsert.call_args
            vectors = call_args[1]['vectors']
            # Verify content is stored in metadata under content_key
            assert CONTENT_KEY in vectors[0]['metadata']

    @pytest.mark.asyncio
    async def test_indexer_uses_namespace(self) -> None:
        """Test indexer uses namespace option (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()

        with patch.object(indexer, '_get_index', return_value=mock_index):
            request = IndexerRequest(
                documents=[
                    DocumentData(content=[DocumentPart(root=TextPart(text='Document content'))]),
                ],
                options={'namespace': 'my-namespace'},
            )

            await indexer.index(request)

            call_args = mock_index.upsert.call_args
            assert call_args[1]['namespace'] == 'my-namespace'

    @pytest.mark.asyncio
    async def test_indexer_handles_empty_documents(self) -> None:
        """Test indexer handles empty document list gracefully."""
        mock_registry = MagicMock()
        indexer = PineconeIndexer(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
        )

        request = IndexerRequest(documents=[])

        # Should not raise, just return early
        await indexer.index(request)


class TestPineconeIndexerRef:
    """Tests for pinecone_indexer_ref function matching JS pineconeIndexerRef."""

    def test_indexer_ref_format(self) -> None:
        """Test indexer ref creates correct reference string."""
        from genkit.plugins.pinecone import pinecone_indexer_ref

        ref = pinecone_indexer_ref(index_id='my-index')
        assert ref == 'pinecone/my-index'

    def test_indexer_ref_with_display_name(self) -> None:
        """Test indexer ref with display name (ignored, for JS parity)."""
        from genkit.plugins.pinecone import pinecone_indexer_ref

        ref = pinecone_indexer_ref(
            index_id='my-index',
            display_name='My Custom Label',
        )
        # Display name is ignored in Python, ref is still the same
        assert ref == 'pinecone/my-index'
