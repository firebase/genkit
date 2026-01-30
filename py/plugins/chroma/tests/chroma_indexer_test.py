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

"""Tests for the Chroma indexer functionality.

These tests verify parity with the JS implementation in:
js/plugins/chroma/src/index.ts (chromaIndexer function)
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.blocks.retriever import IndexerRequest
from genkit.core.typing import DocumentPart, TextPart
from genkit.plugins.chroma.plugin import (
    ChromaIndexer,
    ChromaIndexerOptions,
    _md5_hash,
)
from genkit.types import DocumentData


class TestChromaIndexerOptions:
    """Tests for ChromaIndexerOptions matching JS ChromaIndexerOptionsSchema."""

    def test_indexer_options_empty(self) -> None:
        """Test indexer options can be empty (matches JS z.null().optional())."""
        options = ChromaIndexerOptions()
        # No additional options in current implementation
        assert options is not None


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


class TestChromaIndexer:
    """Tests for ChromaIndexer class matching JS chromaIndexer."""

    def test_indexer_initialization(self) -> None:
        """Test indexer initialization with required params."""
        mock_registry = MagicMock()
        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='googleai/text-embedding-004',
        )

        assert indexer._collection_name == 'test-collection'
        assert indexer._embedder == 'googleai/text-embedding-004'

    def test_indexer_with_embedder_options(self) -> None:
        """Test indexer with embedder options (matches JS)."""
        mock_registry = MagicMock()
        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
            embedder_options={'dimension': 768},
        )

        assert indexer._embedder_options == {'dimension': 768}

    def test_indexer_with_client_params(self) -> None:
        """Test indexer with client params (matches JS clientParams)."""
        mock_registry = MagicMock()
        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
            client_params={'path': '/data/chroma'},
        )

        assert indexer._client_params == {'path': '/data/chroma'}

    def test_indexer_create_collection_if_missing(self) -> None:
        """Test createCollectionIfMissing option (matches JS)."""
        mock_registry = MagicMock()
        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
            create_collection_if_missing=True,
        )

        assert indexer._create_collection_if_missing is True

    @pytest.mark.asyncio
    async def test_indexer_stores_documents(self) -> None:
        """Test indexer stores documents with embeddings (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        mock_collection = MagicMock()

        with patch.object(indexer, '_get_collection', AsyncMock(return_value=mock_collection)):
            request = IndexerRequest(
                documents=[
                    DocumentData(content=[DocumentPart(root=TextPart(text='Document content'))]),
                ],
            )

            await indexer.index(request)

            # Verify collection.add was called
            mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_indexer_generates_md5_ids(self) -> None:
        """Test indexer generates MD5 IDs for documents (matching JS Md5.hashStr)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        mock_collection = MagicMock()

        with patch.object(indexer, '_get_collection', AsyncMock(return_value=mock_collection)):
            request = IndexerRequest(
                documents=[
                    DocumentData(content=[DocumentPart(root=TextPart(text='Test content'))]),
                ],
            )

            await indexer.index(request)

            # Verify IDs are MD5 hashes (32 hex chars)
            call_args = mock_collection.add.call_args
            ids = call_args[1]['ids']
            assert all(len(doc_id) == 32 for doc_id in ids)
            assert all(c in '0123456789abcdef' for doc_id in ids for c in doc_id)

    @pytest.mark.asyncio
    async def test_indexer_stores_metadata(self) -> None:
        """Test indexer stores document metadata (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        mock_collection = MagicMock()

        with patch.object(indexer, '_get_collection', AsyncMock(return_value=mock_collection)):
            request = IndexerRequest(
                documents=[
                    DocumentData(
                        content=[DocumentPart(root=TextPart(text='Document with metadata'))],
                        metadata={'author': 'test'},
                    ),
                ],
            )

            await indexer.index(request)

            call_args = mock_collection.add.call_args
            metadatas = call_args[1]['metadatas']
            # Metadata should include data_type (matching JS)
            assert 'data_type' in metadatas[0]

    @pytest.mark.asyncio
    async def test_indexer_handles_empty_documents(self) -> None:
        """Test indexer handles empty document list gracefully."""
        mock_registry = MagicMock()
        indexer = ChromaIndexer(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        request = IndexerRequest(documents=[])

        # Should not raise, just return early
        await indexer.index(request)


class TestChromaIndexerRef:
    """Tests for chroma_indexer_ref function matching JS chromaIndexerRef."""

    def test_indexer_ref_format(self) -> None:
        """Test indexer ref creates correct reference string."""
        from genkit.plugins.chroma import chroma_indexer_ref

        ref = chroma_indexer_ref(collection_name='my-collection')
        assert ref == 'chroma/my-collection'

    def test_indexer_ref_with_display_name(self) -> None:
        """Test indexer ref with display name (ignored, for JS parity)."""
        from genkit.plugins.chroma import chroma_indexer_ref

        ref = chroma_indexer_ref(
            collection_name='my-collection',
            display_name='My Custom Label',
        )
        # Display name is ignored in Python, ref is still the same
        assert ref == 'chroma/my-collection'
