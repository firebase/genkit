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

"""Tests for the Chroma retriever functionality.

These tests verify parity with the JS implementation in:
js/plugins/chroma/src/index.ts (chromaRetriever function)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.blocks.retriever import RetrieverRequest
from genkit.core.action import ActionRunContext
from genkit.core.typing import DocumentPart, TextPart
from genkit.plugins.chroma.plugin import (
    ChromaRetriever,
    ChromaRetrieverOptions,
)
from genkit.types import DocumentData


class TestChromaRetrieverOptions:
    """Tests for ChromaRetrieverOptions matching JS ChromaRetrieverOptionsSchema."""

    def test_default_k_value(self) -> None:
        """Test default k value matches JS CommonRetrieverOptionsSchema."""
        options = ChromaRetrieverOptions()
        assert options.k == 10

    def test_custom_k_value(self) -> None:
        """Test custom k value."""
        options = ChromaRetrieverOptions(k=50)
        assert options.k == 50

    def test_where_filter(self) -> None:
        """Test where filter for metadata filtering (matches JS)."""
        options = ChromaRetrieverOptions(
            where={'category': 'science'},
        )
        assert options.where == {'category': 'science'}

    def test_where_document_filter(self) -> None:
        """Test whereDocument filter for content filtering (matches JS)."""
        options = ChromaRetrieverOptions(
            where_document={'$contains': 'keyword'},
        )
        assert options.where_document == {'$contains': 'keyword'}

    def test_include_fields(self) -> None:
        """Test include fields for selecting return data (matches JS IncludeOptionSchema)."""
        options = ChromaRetrieverOptions(
            include=['documents', 'embeddings', 'metadatas', 'distances'],
        )
        assert options.include is not None
        assert 'documents' in options.include
        assert 'embeddings' in options.include

    def test_all_options_combined(self) -> None:
        """Test all options can be combined."""
        options = ChromaRetrieverOptions(
            k=20,
            where={'type': 'doc'},
            where_document={'$contains': 'test'},
            include=['documents', 'metadatas'],
        )
        assert options.k == 20
        assert options.where is not None
        assert options.where_document is not None
        assert options.include is not None


class TestChromaRetriever:
    """Tests for ChromaRetriever class matching JS chromaRetriever."""

    def test_retriever_initialization(self) -> None:
        """Test retriever initialization with required params."""
        mock_registry = MagicMock()
        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='googleai/text-embedding-004',
        )

        assert retriever._collection_name == 'test-collection'
        assert retriever._embedder == 'googleai/text-embedding-004'

    def test_retriever_with_embedder_options(self) -> None:
        """Test retriever with embedder options (matches JS)."""
        mock_registry = MagicMock()
        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
            embedder_options={'model': 'custom'},
        )

        assert retriever._embedder_options == {'model': 'custom'}

    def test_retriever_with_client_params(self) -> None:
        """Test retriever with client params (matches JS clientParams)."""
        mock_registry = MagicMock()
        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
            client_params={'path': '/data/chroma'},
        )

        assert retriever._client_params == {'path': '/data/chroma'}

    def test_retriever_create_collection_if_missing(self) -> None:
        """Test createCollectionIfMissing option (matches JS)."""
        mock_registry = MagicMock()
        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
            create_collection_if_missing=True,
        )

        assert retriever._create_collection_if_missing is True

    @pytest.mark.asyncio
    async def test_retriever_returns_documents(self) -> None:
        """Test retriever returns documents in correct format (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        # Mock collection query
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [['Document 1 content', 'Document 2 content']],
            'metadatas': [[{'data_type': 'text'}, {'data_type': 'text'}]],
            'distances': [[0.1, 0.2]],
            'embeddings': None,
        }

        with patch.object(retriever, '_get_collection', AsyncMock(return_value=mock_collection)):
            request = RetrieverRequest(
                query=DocumentData(content=[DocumentPart(root=TextPart(text='search query'))]),
                options=ChromaRetrieverOptions(k=10),
            )

            ctx = MagicMock(spec=ActionRunContext)
            result = await retriever.retrieve(request, ctx)

            assert len(result.documents) == 2
            # Documents should be DocumentData instances
            assert hasattr(result.documents[0], 'content')

    @pytest.mark.asyncio
    async def test_retriever_uses_where_filter(self) -> None:
        """Test retriever passes where filter to collection (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': None,
            'embeddings': None,
        }

        with patch.object(retriever, '_get_collection', AsyncMock(return_value=mock_collection)):
            request = RetrieverRequest(
                query=DocumentData(content=[DocumentPart(root=TextPart(text='search query'))]),
                options=ChromaRetrieverOptions(
                    k=5,
                    where={'category': 'tech'},
                ),
            )

            ctx = MagicMock(spec=ActionRunContext)
            await retriever.retrieve(request, ctx)

            # Verify where filter was passed
            call_args = mock_collection.query.call_args
            assert call_args[1]['where'] == {'category': 'tech'}

    @pytest.mark.asyncio
    async def test_retriever_uses_where_document_filter(self) -> None:
        """Test retriever passes whereDocument filter (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        retriever = ChromaRetriever(
            registry=mock_registry,
            collection_name='test-collection',
            embedder='test/embedder',
        )

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': None,
            'embeddings': None,
        }

        with patch.object(retriever, '_get_collection', AsyncMock(return_value=mock_collection)):
            request = RetrieverRequest(
                query=DocumentData(content=[DocumentPart(root=TextPart(text='search query'))]),
                options=ChromaRetrieverOptions(
                    where_document={'$contains': 'important'},
                ),
            )

            ctx = MagicMock(spec=ActionRunContext)
            await retriever.retrieve(request, ctx)

            call_args = mock_collection.query.call_args
            assert call_args[1]['where_document'] == {'$contains': 'important'}


class TestChromaRetrieverRef:
    """Tests for chroma_retriever_ref function matching JS chromaRetrieverRef."""

    def test_retriever_ref_format(self) -> None:
        """Test retriever ref creates correct reference string."""
        from genkit.plugins.chroma import chroma_retriever_ref

        ref = chroma_retriever_ref(collection_name='my-collection')
        assert ref == 'chroma/my-collection'

    def test_retriever_ref_with_display_name(self) -> None:
        """Test retriever ref with display name (ignored, for JS parity)."""
        from genkit.plugins.chroma import chroma_retriever_ref

        ref = chroma_retriever_ref(
            collection_name='my-collection',
            display_name='My Custom Label',
        )
        # Display name is ignored in Python, ref is still the same
        assert ref == 'chroma/my-collection'
