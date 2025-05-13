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

"""This plugin provides integration with Google Cloud's Vertex AI platform.

It enables the use of Vertex AI models and services within the Genkit framework.
"""

from genkit.plugins.vertex_ai.embedding import (
    EmbeddingModels,
    EmbeddingsTaskType,
)
from genkit.plugins.vertex_ai.gemini import GeminiVersion
from genkit.plugins.vertex_ai.imagen import ImagenOptions, ImagenVersion
from genkit.plugins.vertex_ai.plugin_api import VertexAI, vertexai_name
from genkit.plugins.vertex_ai.vector_search.vector_search import VertexAIVectorSearch


def package_name() -> str:
    """Get the package name for the Vertex AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.vertex_ai'


__all__ = [
    package_name.__name__,
    VertexAI.__name__,
    vertexai_name.__name__,
    EmbeddingModels.__name__,
    EmbeddingsTaskType.__name__,
    GeminiVersion.__name__,
    ImagenVersion.__name__,
    ImagenOptions.__name__,
    VertexAIVectorSearch.__name__,
]
