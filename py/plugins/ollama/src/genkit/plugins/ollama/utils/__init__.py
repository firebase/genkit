# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from genkit.plugins.ollama.utils.model_utils import register_ollama_model
from genkit.plugins.ollama.utils.embedding_utils import register_ollama_embedder


__all__ = [
    register_ollama_model.__name__,
    register_ollama_embedder.__name__,
]
