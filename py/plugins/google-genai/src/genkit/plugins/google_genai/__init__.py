# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from genkit.plugins.google_genai.google import GoogleGenai, google_genai_name
from genkit.plugins.google_genai.models.gemini import GeminiVersion
from genkit.plugins.google_genai.schemas import GoogleGenaiPluginOptions


def package_name() -> str:
    """Get the package name for the Vertex AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.vertex_ai'


__all__ = [
    package_name.__name__,
    GoogleGenai.__name__,
    GoogleGenaiPluginOptions.__name__,
    google_genai_name.__name__,
    GeminiVersion.__name__,
]
