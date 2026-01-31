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

"""Tests for the Chroma plugin."""

from unittest.mock import MagicMock

import pytest

from genkit.core.action.types import ActionKind
from genkit.plugins.chroma import (
    Chroma,
    ChromaCollectionConfig,
    chroma_indexer_ref,
    chroma_retriever_ref,
)


def test_plugin_name() -> None:
    """Test plugin has correct name."""
    plugin = Chroma()
    assert plugin.name == 'chroma'


def test_init_empty_config() -> None:
    """Test plugin initialization with no config."""
    plugin = Chroma()
    assert plugin._collections == []


def test_init_with_collections() -> None:
    """Test plugin initialization with collections."""
    collections = [
        ChromaCollectionConfig(
            collection_name='test-collection',
            embedder='googleai/text-embedding-004',
        ),
    ]
    plugin = Chroma(collections=collections)
    assert len(plugin._collections) == 1
    assert plugin._collections[0].collection_name == 'test-collection'


def test_chroma_retriever_ref() -> None:
    """Test chroma_retriever_ref creates correct reference string."""
    ref = chroma_retriever_ref(collection_name='my-collection')
    assert ref == 'chroma/my-collection'


def test_chroma_indexer_ref() -> None:
    """Test chroma_indexer_ref creates correct reference string."""
    ref = chroma_indexer_ref(collection_name='my-collection')
    assert ref == 'chroma/my-collection'


def test_chroma_collection_config_defaults() -> None:
    """Test ChromaCollectionConfig default values."""
    config = ChromaCollectionConfig(
        collection_name='test',
        embedder='test/embedder',
    )
    assert config.collection_name == 'test'
    assert config.embedder == 'test/embedder'
    assert config.embedder_options is None
    assert config.client_params is None
    assert config.create_collection_if_missing is False
    assert config.metadata is None


@pytest.mark.asyncio
async def test_init_stores_registry() -> None:
    """Test that init() stores the registry for later use."""
    plugin = Chroma()
    mock_registry = MagicMock()

    result = await plugin.init(mock_registry)

    assert result == []
    assert plugin._registry == mock_registry


@pytest.mark.asyncio
async def test_list_actions_with_collections() -> None:
    """Test list_actions returns metadata for configured collections."""
    collections = [
        ChromaCollectionConfig(
            collection_name='collection1',
            embedder='test/embedder',
        ),
        ChromaCollectionConfig(
            collection_name='collection2',
            embedder='test/embedder',
        ),
    ]
    plugin = Chroma(collections=collections)

    actions = await plugin.list_actions()

    # Should have 2 retrievers + 2 indexers = 4 actions
    assert len(actions) == 4

    retriever_actions = [a for a in actions if a.kind == ActionKind.RETRIEVER]
    indexer_actions = [a for a in actions if a.kind == ActionKind.INDEXER]

    assert len(retriever_actions) == 2
    assert len(indexer_actions) == 2


@pytest.mark.asyncio
async def test_list_actions_empty() -> None:
    """Test list_actions with no configured collections."""
    plugin = Chroma()

    actions = await plugin.list_actions()
    assert actions == []


@pytest.mark.asyncio
async def test_resolve_returns_none_for_unknown_action() -> None:
    """Test resolve returns None for unknown action names."""
    plugin = Chroma()
    plugin._registry = MagicMock()

    result = await plugin.resolve(ActionKind.MODEL, 'chroma/test')
    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_none_for_other_namespace() -> None:
    """Test resolve returns None for actions not in chroma namespace."""
    plugin = Chroma()
    plugin._registry = MagicMock()

    result = await plugin.resolve(ActionKind.RETRIEVER, 'other/collection')
    assert result is None


@pytest.mark.asyncio
async def test_resolve_retriever_for_configured_collection() -> None:
    """Test resolve returns action for configured collection retriever."""
    collections = [
        ChromaCollectionConfig(
            collection_name='test-collection',
            embedder='test/embedder',
        ),
    ]
    plugin = Chroma(collections=collections)
    mock_registry = MagicMock()
    await plugin.init(mock_registry)

    action = await plugin.resolve(ActionKind.RETRIEVER, 'chroma/test-collection')

    # Should return an action (not None) for configured collection
    assert action is not None


@pytest.mark.asyncio
async def test_resolve_indexer_for_configured_collection() -> None:
    """Test resolve returns action for configured collection indexer."""
    collections = [
        ChromaCollectionConfig(
            collection_name='test-collection',
            embedder='test/embedder',
        ),
    ]
    plugin = Chroma(collections=collections)
    mock_registry = MagicMock()
    await plugin.init(mock_registry)

    action = await plugin.resolve(ActionKind.INDEXER, 'chroma/test-collection')

    # Should return an action (not None) for configured collection
    assert action is not None
