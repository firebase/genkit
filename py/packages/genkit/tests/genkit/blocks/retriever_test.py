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


"""Tests for Genkit retrievers and indexers."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from genkit.blocks.retriever import (
    IndexerOptions,
    RetrieverOptions,
    RetrieverResponse,
    RetrieverSupports,
    create_indexer_ref,
    create_retriever_ref,
    define_indexer,
    define_retriever,
    indexer_action_metadata,
    retriever_action_metadata,
)
from genkit.core.action import ActionMetadata
from genkit.core.schema import to_json_schema


def test_retriever_action_metadata():
    """Test for retriever_action_metadata with basic options."""
    options = RetrieverOptions(label='Test Retriever')
    action_metadata = retriever_action_metadata(
        name='test_retriever',
        options=options,
    )

    assert isinstance(action_metadata, ActionMetadata)
    assert action_metadata.input_json_schema is not None
    assert action_metadata.output_json_schema is not None
    assert action_metadata.metadata == {
        'retriever': {
            'label': options.label,
            'customOptions': None,
        }
    }


def test_retriever_action_metadata_with_supports_and_config_schema():
    """Test for retriever_action_metadata with supports and config_schema."""

    class CustomConfig(BaseModel):
        k: int

    options = RetrieverOptions(
        label='Advanced Retriever',
        supports=RetrieverSupports(media=True),
        config_schema=to_json_schema(CustomConfig),
    )
    action_metadata = retriever_action_metadata(
        name='advanced_retriever',
        options=options,
    )
    assert isinstance(action_metadata, ActionMetadata)
    assert action_metadata.metadata is not None
    assert action_metadata.metadata.get('retriever') is not None
    assert action_metadata.metadata['retriever']['label'] == 'Advanced Retriever'
    assert action_metadata.metadata['retriever']['supports'] == {
        'media': True,
    }
    assert action_metadata.metadata['retriever']['customOptions'] == {
        'title': 'CustomConfig',
        'type': 'object',
        'properties': {
            'k': {'title': 'K', 'type': 'integer'},
        },
        'required': ['k'],
    }


def test_retriever_action_metadata_no_options():
    """Test retriever_action_metadata when no options are provided."""
    action_metadata = retriever_action_metadata(name='default_retriever')
    assert isinstance(action_metadata, ActionMetadata)
    assert action_metadata.metadata == {'retriever': {'customOptions': None}}


def test_create_retriever_ref_basic():
    """Test basic creation of RetrieverRef."""
    ref = create_retriever_ref('my-retriever')
    assert ref.name == 'my-retriever'
    assert ref.config is None
    assert ref.version is None


def test_create_retriever_ref_with_config():
    """Test creation of RetrieverRef with configuration."""
    config = {'k': 5}
    ref = create_retriever_ref('configured-retriever', config=config)
    assert ref.name == 'configured-retriever'
    assert ref.config == config
    assert ref.version is None


def test_create_retriever_ref_with_version():
    """Test creation of RetrieverRef with a version."""
    ref = create_retriever_ref('versioned-retriever', version='v1.0')
    assert ref.name == 'versioned-retriever'
    assert ref.config is None
    assert ref.version == 'v1.0'


def test_create_retriever_ref_with_config_and_version():
    """Test creation of RetrieverRef with both config and version."""
    config = {'k': 10}
    ref = create_retriever_ref('full-retriever', config=config, version='beta')
    assert ref.name == 'full-retriever'
    assert ref.config == config
    assert ref.version == 'beta'


@pytest.mark.asyncio
async def test_define_retriever():
    """Test define_retriever registration."""
    registry = MagicMock()
    fn = AsyncMock(return_value=RetrieverResponse(documents=[]))

    define_retriever(registry, 'test_retriever', fn)

    registry.register_action.assert_called_once()
    call_args = registry.register_action.call_args
    assert call_args.kwargs['kind'] == 'retriever'
    assert call_args.kwargs['name'] == 'test_retriever'


@pytest.mark.asyncio
async def test_define_indexer():
    """Test define_indexer registration."""
    registry = MagicMock()
    fn = AsyncMock()

    define_indexer(registry, 'test_indexer', fn)

    registry.register_action.assert_called_once()
    call_args = registry.register_action.call_args
    assert call_args.kwargs['kind'] == 'indexer'
    assert call_args.kwargs['name'] == 'test_indexer'


def test_indexer_action_metadata():
    """Test for indexer_action_metadata with basic options."""
    options = IndexerOptions(label='Test Indexer')
    action_metadata = indexer_action_metadata(
        name='test_indexer',
        options=options,
    )

    assert isinstance(action_metadata, ActionMetadata)
    assert action_metadata.input_json_schema is not None
    assert action_metadata.output_json_schema is not None
    assert action_metadata.metadata == {
        'indexer': {
            'label': options.label,
            'customOptions': None,
        }
    }


def test_create_indexer_ref_basic():
    """Test basic creation of IndexerRef."""
    ref = create_indexer_ref('my-indexer')
    assert ref.name == 'my-indexer'
    assert ref.config is None
    assert ref.version is None
