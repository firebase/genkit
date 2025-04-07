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

import pytest

from genkit.blocks.document import Document
from genkit.plugins.vertex_ai.embedding import (
    Embedder,
    EmbeddingModels,
    EmbeddingsTaskType,
)
from genkit.types import EmbedRequest, EmbedResponse


@pytest.mark.parametrize(
    'version, task',
    [(m, t) for t in EmbeddingsTaskType for m in EmbeddingModels],
)
def test_generate_response(mocker, version, task):
    """Tests generate method for embeddings."""
    mocked_respond = []
    docs = [
        Document.from_text(text='Text1'),
        Document.from_text(text='Text2'),
        Document.from_text(text='Text3'),
    ]
    request = EmbedRequest(input=docs, options={'task': task})
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
