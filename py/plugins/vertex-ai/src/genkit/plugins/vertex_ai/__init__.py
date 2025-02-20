# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
from genkit.plugins.vertex_ai.gemini import GeminiVersion
from genkit.plugins.vertex_ai.plugin_api import VertexAI, vertexai_name


def package_name() -> str:
    return 'genkit.plugins.vertex_ai'


__all__ = ['package_name', 'VertexAI', 'vertexai_name', 'GeminiVersion']
