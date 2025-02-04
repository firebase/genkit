# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
Ollama Embedders for Genkit.
"""

import ollama as ollama_api

from genkit.plugins.ollama.models import EmbeddingModelDefinition
from genkit.veneer import Genkit


def register_ollama_embedder(
    ai: Genkit,
    embedder: EmbeddingModelDefinition,
    client: ollama_api.Client,
) -> None:
    pass
