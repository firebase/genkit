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

import unittest
from functools import partial
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.cloud.aiplatform_v1 import (
    FindNeighborsRequest,
    FindNeighborsResponse,
    IndexDatapoint,
    MatchServiceAsyncClient,
    NearestNeighbors,
    Neighbor,
)

from genkit.ai import Genkit
from genkit.blocks.document import Document, DocumentData, DocumentPart
from genkit.core.typing import Embedding
from genkit.plugins.vertex_ai.models.retriever import (
    BigQueryRetriever,
    FirestoreRetriever,
)
from genkit.types import (
    ActionRunContext,
    EmbedRequest,
    EmbedResponse,
    RetrieverRequest,
    RetrieverResponse,
    TextPart,
)


@pytest.fixture
def bq_retriever_instance():
    """Common initialization of bq retriever."""
    return BigQueryRetriever(
        ai=MagicMock(),
        name='test',
        match_service_client_generator=MagicMock(),
        embedder='embedder',
        embedder_options=None,
        bq_client=MagicMock(),
        dataset_id='dataset_id',
        table_id='table_id',
    )


def test_bigquery_retriever__init__(bq_retriever_instance):
    """Init test."""
    bq_retriever = bq_retriever_instance

    assert bq_retriever is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "options, top_k",
    [
        (
            {'limit': 10},
            10,
        ),
        (
            {},
            3,
        ),
        (
            None,
            3,
        )
    ]
)
async def test_bigquery_retriever_retrieve(
    bq_retriever_instance,
    options,
    top_k,
):
    """Test retrieve method bq retriever."""
    # Mock query embedder
    mock_embedding = MagicMock()
    mock_embedding.embeddings = [
        Embedding(
            embedding=[0.1, 0.2, 0.3],
        ),
    ]

    mock_genkit = MagicMock(spec=Genkit)
    mock_genkit.embed.return_value = mock_embedding

    bq_retriever_instance.ai = mock_genkit

    # Mock _get_closest_documents
    mock__get_closest_documents_result = [
        Document.from_text(
            text='1',
            metadata={
                'distance': 0.0,
                'id': 1
            },
        ),
        Document.from_text(
            text='2',
            metadata={
                'distance': 0.0,
                'id': 2
            },
        ),
    ]

    bq_retriever_instance._get_closest_documents = AsyncMock(
        return_value=mock__get_closest_documents_result,
    )

    # Executes
    await bq_retriever_instance.retrieve(
        RetrieverRequest(
            query=DocumentData(
                content=[
                    TextPart(
                        text='test-1'
                    ),
                ],
            ),
            options=options,
        ),
        MagicMock(spec=ActionRunContext),
    )

    # Assert mocks
    bq_retriever_instance.ai.embed.assert_called_once_with(
        embedder='embedder',
        documents=[Document(
                content=[
                    TextPart(
                        text='test-1'
                    ),
                ],
            ),
        ],
        options={},
    )

    bq_retriever_instance._get_closest_documents.assert_awaited_once_with(
        request=RetrieverRequest(
            query=DocumentData(
                content=[
                    TextPart(
                        text='test-1'
                    ),
                ],
            ),
            options=options,
        ),
        top_k=top_k,
        query_embeddings=Embedding(
            embedding=[0.1, 0.2, 0.3],
        ),
    )


@pytest.mark.asyncio
async def test_bigquery__get_closest_documents(bq_retriever_instance):
    """Test bigquery retriever _get_closest_documents."""
    # Mock find_neighbors method
    mock_vector_search_client = MagicMock(spec=MatchServiceAsyncClient)

    # find_neighbors response
    mock_nn = MagicMock()
    mock_nn.neighbors = []

    mock_nn_response = MagicMock(spec=FindNeighborsResponse)
    mock_nn_response.nearest_neighbors = [
        mock_nn,
    ]

    mock_vector_search_client.find_neighbors = AsyncMock(
        return_value=mock_nn_response,
    )

    # find_neighbors call
    bq_retriever_instance._match_service_client_generator.return_value = mock_vector_search_client

    # Mock _retrieve_neighbours_data_from_db method
    mock__retrieve_neighbours_data_from_db_result = [
        Document.from_text(
            text='1',
            metadata={
                'distance': 0.0,
                'id': 1
            }
        ),
        Document.from_text(
            text='2',
            metadata={
                'distance': 0.0,
                'id': 2
            }
        ),
    ]

    bq_retriever_instance._retrieve_neighbours_data_from_db = AsyncMock(
        return_value=mock__retrieve_neighbours_data_from_db_result,
    )

    await bq_retriever_instance._get_closest_documents(
        request=RetrieverRequest(
            query=DocumentData(
                content=[
                    TextPart(
                        text='test-1'
                    )
                ],
                metadata={
                    'index_endpoint_path': 'index_endpoint_path',
                    'api_endpoint': 'api_endpoint',
                    'deployed_index_id': 'deployed_index_id',
                }
            ),
            options={
                'limit': 10,
            }
        ),
        top_k=10,
        query_embeddings=Embedding(
            embedding=[0.1, 0.2, 0.3],
        )
    )

    # Assert calls
    mock_vector_search_client.find_neighbors.assert_awaited_once_with(
        request=FindNeighborsRequest(
            index_endpoint="index_endpoint_path",
            deployed_index_id="deployed_index_id",
            queries=[
                FindNeighborsRequest.Query(
                    datapoint=IndexDatapoint(feature_vector=[0.1, 0.2, 0.3]),
                    neighbor_count=10,
                )
            ],
        )
    )

    bq_retriever_instance._retrieve_neighbours_data_from_db.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {
            'index_endpoint_path': 'index_endpoint_path',
        },
        {
            'api_endpoint': 'api_endpoint',
        },
        {
            'deployed_index_id': 'deployed_index_id',
        },
        {
            'index_endpoint_path': 'index_endpoint_path',
            'api_endpoint': 'api_endpoint',
        },
        {
            'index_endpoint_path': 'index_endpoint_path',
            'deployed_index_id': 'deployed_index_id',
        },
        {
            'api_endpoint': 'api_endpoint',
            'deployed_index_id': 'deployed_index_id',
        }
    ]
)
async def test_bigquery__get_closest_documents_fail(
    bq_retriever_instance,
    metadata,
):
    """Test failures bigquery retriever _get_closest_documents."""
    with pytest.raises(AttributeError):
        await bq_retriever_instance._get_closest_documents(
            request=RetrieverRequest(
                query=DocumentData(
                    content=[
                        TextPart(
                            text='test-1'
                        )
                    ],
                    metadata=metadata,
                ),
                options={
                    'limit': 10,
                }
            ),
            top_k=10,
            query_embeddings=Embedding(
                embedding=[0.1, 0.2, 0.3],
            )
        )


def test_firestore_retriever__init__():
    """Init test."""
    fs_retriever = FirestoreRetriever(
        ai=MagicMock(),
        name='test',
        match_service_client_generator=MagicMock(),
        embedder='embedder',
        embedder_options=None,
        firestore_client=MagicMock(),
        collection_name='collection_name',
    )

    assert fs_retriever is not None
