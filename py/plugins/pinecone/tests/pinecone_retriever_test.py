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

"""Tests for the Pinecone retriever functionality.

These tests verify parity with the JS implementation in:
js/plugins/pinecone/src/index.ts (configurePineconeRetriever function)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.blocks.retriever import RetrieverRequest
from genkit.core.action import ActionRunContext
from genkit.core.typing import DocumentPart, TextPart
from genkit.plugins.pinecone.plugin import (
    CONTENT_KEY,
    MAX_K,
    PineconeRetriever,
    PineconeRetrieverOptions,
)
from genkit.types import DocumentData


class TestPineconeRetrieverOptions:
    """Tests for PineconeRetrieverOptions matching JS PineconeRetrieverOptionsSchema."""

    def test_default_k_value(self) -> None:
        """Test default k value matches JS CommonRetrieverOptionsSchema."""
        options = PineconeRetrieverOptions()
        assert options.k == 10

    def test_k_max_value(self) -> None:
        """Test k max value is 1000 (matching JS .max(1000))."""
        assert MAX_K == 1000
        # Pydantic should enforce max
        options = PineconeRetrieverOptions(k=1000)
        assert options.k == 1000

    def test_namespace_option(self) -> None:
        """Test namespace option (matches JS schema)."""
        options = PineconeRetrieverOptions(namespace='my-namespace')
        assert options.namespace == 'my-namespace'

    def test_filter_option(self) -> None:
        """Test filter option for metadata filtering (matches JS)."""
        options = PineconeRetrieverOptions(
            filter={'category': 'science'},
        )
        assert options.filter == {'category': 'science'}

    def test_all_options_combined(self) -> None:
        """Test all options can be combined."""
        options = PineconeRetrieverOptions(
            k=50,
            namespace='test-namespace',
            filter={'type': 'doc'},
        )
        assert options.k == 50
        assert options.namespace == 'test-namespace'
        assert options.filter is not None


class TestPineconeRetriever:
    """Tests for PineconeRetriever class matching JS configurePineconeRetriever."""

    def test_retriever_initialization(self) -> None:
        """Test retriever initialization with required params."""
        mock_registry = MagicMock()
        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='googleai/text-embedding-004',
        )

        assert retriever._index_id == 'test-index'
        assert retriever._embedder == 'googleai/text-embedding-004'

    def test_retriever_with_embedder_options(self) -> None:
        """Test retriever with embedder options (matches JS)."""
        mock_registry = MagicMock()
        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            embedder_options={'model': 'custom'},
        )

        assert retriever._embedder_options == {'model': 'custom'}

    def test_retriever_with_client_params(self) -> None:
        """Test retriever with client params (matches JS clientParams/PineconeConfiguration)."""
        mock_registry = MagicMock()
        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        assert retriever._client_params == {'api_key': 'test-key'}

    def test_retriever_custom_content_key(self) -> None:
        """Test contentKey option (matches JS)."""
        mock_registry = MagicMock()
        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            content_key='custom_content',
        )

        assert retriever._content_key == 'custom_content'

    def test_retriever_default_content_key(self) -> None:
        """Test default contentKey is '_content' (matches JS CONTENT_KEY)."""
        mock_registry = MagicMock()
        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
        )

        assert retriever._content_key == CONTENT_KEY
        assert retriever._content_key == '_content'

    @pytest.mark.asyncio
    async def test_retriever_uses_namespace(self) -> None:
        """Test retriever uses namespace option (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()
        mock_index.query.return_value = {'matches': []}

        with patch.object(retriever, '_get_index', return_value=mock_index):
            request = RetrieverRequest(
                query=DocumentData(content=[DocumentPart(root=TextPart(text='search query'))]),
                options=PineconeRetrieverOptions(
                    k=10,
                    namespace='my-namespace',
                ),
            )

            ctx = MagicMock(spec=ActionRunContext)
            await retriever.retrieve(request, ctx)

            # Verify namespace was passed
            call_args = mock_index.query.call_args
            assert call_args[1]['namespace'] == 'my-namespace'

    @pytest.mark.asyncio
    async def test_retriever_uses_filter(self) -> None:
        """Test retriever uses filter option (matching JS)."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()
        mock_index.query.return_value = {'matches': []}

        with patch.object(retriever, '_get_index', return_value=mock_index):
            request = RetrieverRequest(
                query=DocumentData(content=[DocumentPart(root=TextPart(text='search query'))]),
                options=PineconeRetrieverOptions(
                    filter={'category': 'tech'},
                ),
            )

            ctx = MagicMock(spec=ActionRunContext)
            await retriever.retrieve(request, ctx)

            call_args = mock_index.query.call_args
            assert call_args[1]['filter'] == {'category': 'tech'}

    @pytest.mark.asyncio
    async def test_retriever_query_params_match_js(self) -> None:
        """Test retriever query params match JS implementation."""
        mock_registry = MagicMock()
        mock_embedder_action = MagicMock()
        mock_embedder_action.arun = AsyncMock(
            return_value=MagicMock(response=MagicMock(embeddings=[MagicMock(embedding=[0.1, 0.2, 0.3])]))
        )
        mock_registry.resolve_embedder = AsyncMock(return_value=mock_embedder_action)

        retriever = PineconeRetriever(
            registry=mock_registry,
            index_id='test-index',
            embedder='test/embedder',
            client_params={'api_key': 'test-key'},
        )

        mock_index = MagicMock()
        mock_index.query.return_value = {'matches': []}

        with patch.object(retriever, '_get_index', return_value=mock_index):
            request = RetrieverRequest(
                query=DocumentData(content=[DocumentPart(root=TextPart(text='search query'))]),
                options=PineconeRetrieverOptions(k=20),
            )

            ctx = MagicMock(spec=ActionRunContext)
            await retriever.retrieve(request, ctx)

            call_args = mock_index.query.call_args
            # Match JS: includeValues: false, includeMetadata: true
            assert call_args[1]['include_values'] is False
            assert call_args[1]['include_metadata'] is True
            assert call_args[1]['top_k'] == 20


class TestPineconeRetrieverRef:
    """Tests for pinecone_retriever_ref function matching JS pineconeRetrieverRef."""

    def test_retriever_ref_format(self) -> None:
        """Test retriever ref creates correct reference string."""
        from genkit.plugins.pinecone import pinecone_retriever_ref

        ref = pinecone_retriever_ref(index_id='my-index')
        assert ref == 'pinecone/my-index'

    def test_retriever_ref_with_display_name(self) -> None:
        """Test retriever ref with display name (ignored, for JS parity)."""
        from genkit.plugins.pinecone import pinecone_retriever_ref

        ref = pinecone_retriever_ref(
            index_id='my-index',
            display_name='My Custom Label',
        )
        # Display name is ignored in Python, ref is still the same
        assert ref == 'pinecone/my-index'
