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

"""This plugin provides integration with Google Cloud's Vertex AI Vector Search."""

from genkit.plugins.vertex_ai.vector_search.retriever import (
    BigQueryRetriever,
    FirestoreRetriever,
    RetrieverOptionsSchema,
)
from genkit.plugins.vertex_ai.vector_search.params import (
    VertexAIVectorSearchOptions,
    vertexai_retrieve_params,
)
from genkit.plugins.vertex_ai.vector_search.vector_search import (
    VectorSearchConfig,
    vertexai_vector_search_name,
)


def package_name() -> str:
    """Get the package name for the Vertex AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.vertex_ai.vector_search'


__all__ = [
    package_name.__name__,
    vertexai_vector_search_name.__name__,
    VectorSearchConfig.__name__,
    VertexAIVectorSearchOptions.__name__,
    vertexai_retrieve_params.__name__,
    BigQueryRetriever.__name__,
    FirestoreRetriever.__name__,
    RetrieverOptionsSchema.__name__,
]
