# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Vertex AI plugin for Genkit.

This plugin provides integration with Google Cloud's Vertex AI platform,
enabling the use of Vertex AI models and services within the Genkit framework.
"""

from genkit.plugins.vertex_ai.embedding import EmbeddingModels
from genkit.plugins.vertex_ai.gemini import GeminiVersion
from genkit.plugins.vertex_ai.imagen import ImagenVersion
from genkit.plugins.vertex_ai.plugin_api import VertexAI, vertexai_name


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
    GeminiVersion.__name__,
    ImagenVersion.__name__,
]
