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

"""Tests for the Pinecone plugin."""

from unittest.mock import MagicMock

import pytest

from genkit.core.action.types import ActionKind
from genkit.plugins.pinecone import (
    Pinecone,
    PineconeIndexConfig,
    PineconeIndexerOptions,
    PineconeRetrieverOptions,
    pinecone,
    pinecone_indexer_ref,
    pinecone_retriever_ref,
)


def test_plugin_name() -> None:
    """Test plugin has correct name."""
    plugin = Pinecone()
    assert plugin.name == 'pinecone'


def test_init_empty_config() -> None:
    """Test plugin initialization with no config."""
    plugin = Pinecone()
    assert plugin._indexes == []


def test_init_with_indexes() -> None:
    """Test plugin initialization with index configs."""
    config = PineconeIndexConfig(
        index_id='test-index',
        embedder='googleai/text-embedding-004',
    )
    plugin = Pinecone(indexes=[config])
    assert len(plugin._indexes) == 1
    assert plugin._indexes[0].index_id == 'test-index'


def test_pinecone_factory_function() -> None:
    """Test pinecone() factory function creates plugin correctly."""
    plugin = pinecone(
        indexes=[
            {
                'index_id': 'my-index',
                'embedder': 'test/embedder',
            }
        ]
    )
    assert isinstance(plugin, Pinecone)
    assert len(plugin._indexes) == 1


def test_pinecone_retriever_ref() -> None:
    """Test pinecone_retriever_ref creates correct reference string."""
    ref = pinecone_retriever_ref(index_id='my-index')
    assert ref == 'pinecone/my-index'


def test_pinecone_indexer_ref() -> None:
    """Test pinecone_indexer_ref creates correct reference string."""
    ref = pinecone_indexer_ref(index_id='my-index')
    assert ref == 'pinecone/my-index'


def test_pinecone_index_config_defaults() -> None:
    """Test PineconeIndexConfig default values."""
    config = PineconeIndexConfig(
        index_id='test',
        embedder='test/embedder',
    )
    assert config.index_id == 'test'
    assert config.embedder == 'test/embedder'
    assert config.embedder_options is None


def test_pinecone_retriever_options_defaults() -> None:
    """Test PineconeRetrieverOptions default values."""
    options = PineconeRetrieverOptions()
    assert options.k == 10
    assert options.namespace is None
    assert options.filter is None


def test_pinecone_indexer_options_defaults() -> None:
    """Test PineconeIndexerOptions default values."""
    options = PineconeIndexerOptions()
    assert options.namespace is None


@pytest.mark.asyncio
async def test_init_stores_registry() -> None:
    """Test that init() stores the registry for later use."""
    plugin = Pinecone()
    mock_registry = MagicMock()

    result = await plugin.init(mock_registry)

    assert result == []
    assert plugin._registry == mock_registry


@pytest.mark.asyncio
async def test_list_actions_with_indexes() -> None:
    """Test list_actions returns metadata for configured indexes."""
    config1 = PineconeIndexConfig(
        index_id='index1',
        embedder='test/embedder',
    )
    config2 = PineconeIndexConfig(
        index_id='index2',
        embedder='test/embedder',
    )
    plugin = Pinecone(indexes=[config1, config2])

    actions = await plugin.list_actions()

    # Should have 2 retrievers + 2 indexers = 4 actions
    assert len(actions) == 4

    retriever_actions = [a for a in actions if a.kind == ActionKind.RETRIEVER]
    indexer_actions = [a for a in actions if a.kind == ActionKind.INDEXER]

    assert len(retriever_actions) == 2
    assert len(indexer_actions) == 2


@pytest.mark.asyncio
async def test_list_actions_empty() -> None:
    """Test list_actions with no configured indexes."""
    plugin = Pinecone()

    actions = await plugin.list_actions()
    assert actions == []


@pytest.mark.asyncio
async def test_resolve_returns_none_for_unknown_action() -> None:
    """Test resolve returns None for unknown action names."""
    plugin = Pinecone()
    plugin._registry = MagicMock()

    result = await plugin.resolve(ActionKind.MODEL, 'pinecone/test')
    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_none_for_other_namespace() -> None:
    """Test resolve returns None for actions not in pinecone namespace."""
    plugin = Pinecone()
    plugin._registry = MagicMock()

    result = await plugin.resolve(ActionKind.RETRIEVER, 'other/index')
    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_none_for_unconfigured_index() -> None:
    """Test resolve returns None for indexes that aren't configured."""
    plugin = Pinecone()
    mock_registry = MagicMock()
    await plugin.init(mock_registry)

    result = await plugin.resolve(ActionKind.RETRIEVER, 'pinecone/nonexistent')
    assert result is None
