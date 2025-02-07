# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Google Cloud Vertex AI Plugin for Genkit."""
from genkit.plugins.vertex_ai.plugin_api import vertexAI, gemini
from genkit.plugins.vertex_ai.options import PluginOptions


__all__ = ['package_name', 'vertexAI', 'gemini', 'PluginOptions']
