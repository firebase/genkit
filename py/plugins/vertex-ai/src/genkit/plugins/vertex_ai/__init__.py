# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Vertex AI plugin for Genkit.

This plugin provides integration with Google Cloud's Vertex AI platform,
enabling the use of Vertex AI models and services within the Genkit framework.
"""

from genkit.plugins.vertex_ai.plugin_api import VertexAI, vertexai_name


def package_name() -> str:
    """Get the package name for the Vertex AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.vertex_ai'


__all__ = ['package_name', 'VertexAI', 'vertexai_name']
