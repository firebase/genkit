# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from genkit.ai.embedding import EmbedRequest, EmbedResponse
from genkit.plugins.vertex_ai.embedding import Embedder, EmbeddingModels


@pytest.mark.parametrize('version', [x for x in EmbeddingModels])
def test_generate_response(mocker, version):
    """Tests generate method for embeddings."""
    mocked_respond = []
    request = EmbedRequest(documents=['Text1', 'Text2', 'Text3'])
    embedder = Embedder(version)
    genai_model_mock = mocker.MagicMock()
    model_response_mock = mocker.MagicMock()
    model_response_mock.text = mocked_respond
    genai_model_mock.generate_content.return_value = model_response_mock
    mocker.patch(
        'genkit.plugins.vertex_ai.embedding.Embedder.embedding_model',
        genai_model_mock,
    )

    response = embedder.generate(request)
    assert isinstance(response, EmbedResponse)
    assert response.embeddings == mocked_respond
