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

from genkit.plugins.google_genai.google import GoogleAI, VertexAI, googleai_name, vertexai_name
from genkit.plugins.google_genai.models.embedder import (
    EmbeddingTaskType,
    GeminiEmbeddingModels,
    VertexEmbeddingModels,
)
from genkit.plugins.google_genai.models.gemini import GeminiConfigSchema, GoogleAIGeminiVersion, VertexAIGeminiVersion
from genkit.plugins.google_genai.models.imagen import ImagenVersion


def package_name() -> str:
    """Get the package name for the Vertex AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.google_genai'


__all__ = [
    package_name.__name__,
    GoogleAI.__name__,
    VertexAI.__name__,
    googleai_name.__name__,
    vertexai_name.__name__,
    GeminiEmbeddingModels.__name__,
    VertexEmbeddingModels.__name__,
    GoogleAIGeminiVersion.__name__,
    VertexAIGeminiVersion.__name__,
    EmbeddingTaskType.__name__,
    GeminiConfigSchema.__name__,
    ImagenVersion.__name__,
]
