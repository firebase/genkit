# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""
Ollama Plugin for Genkit.
"""

import logging
from typing import Callable

import ollama as ollama_api

from genkit.plugins.ollama.models import OllamaPluginParams
from genkit.plugins.ollama.utils import (
    register_ollama_embedder,
    register_ollama_model,
)
from genkit.veneer import Genkit

LOG = logging.getLogger(__name__)


def Ollama(plugin_params: OllamaPluginParams) -> Callable[[Genkit], None]:
    client = ollama_api.Client(
        host=plugin_params.server_address.unicode_string()
    )

    def plugin(ai: Genkit) -> None:
        for model in plugin_params.models:
            register_ollama_model(
                ai=ai,
                model=model,
                client=client,
            )

        for embedder in plugin_params.embedders:
            register_ollama_embedder(
                ai=ai,
                embedder=embedder,
                client=client,
            )

    return plugin
