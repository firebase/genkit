# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Cloud Vertex AI Plugin for Genkit."""
import logging
from collections.abc import Callable

import vertexai

from genkit.plugins.vertex_ai.gemini import execute_gemini_request
from genkit.plugins.vertex_ai.options import (
    PluginOptions,
    get_plugin_parameters,
)
from genkit.veneer.veneer import Genkit

LOG = logging.getLogger(__name__)


def vertexAI(options: PluginOptions | None) -> Callable[[Genkit], None]:

    def plugin(ai: Genkit) -> None:
        project_id, location, credentials = get_plugin_parameters(options)
        vertexai.init(project=project_id,
                      location=location,
                      credentials=credentials)

        ai.define_model(
            name=gemini('gemini-1.5-flash'),
            fn=execute_gemini_request,
            metadata={
                'model': {
                    'supports': {'multiturn': True},
                }
            },
        )

    return plugin


def gemini(name: str) -> str:
    return f'vertexai/{name}'
