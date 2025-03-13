# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import os

from enum import StrEnum


from genkit.plugins.vertex_ai import constants as const
from genkit.core.typing import (
    ModelInfo,
    Supports,
)
from genkit.veneer.registry import GenkitRegistry
from .openai_compatiblility import OpenAICompatibleModel, OpenAIConfig


def vertexai_name(name: str) -> str:
    """Create a Vertex AI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Vertex AI action name.
    """
    return f'vertexai/{name}'

class OpenAIFormatModelVersion(StrEnum):
    """Available versions of the llama model.

    This enum defines the available versions of the llama model that
    can be used through Vertex AI.
    """
    LLAMA_3_1 = 'llama-3.1'
    LLAMA_3_2 = 'llama-3.2'


SUPPORTED_OPENAI_FORMAT_MODELS: dict[str, ModelInfo] = {
    OpenAIFormatModelVersion.LLAMA_3_1: ModelInfo(
        versions=['meta/llama3-405b-instruct-maas'],
        label='llama-3.1',
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=['text', 'json']
        )
    ),
    OpenAIFormatModelVersion.LLAMA_3_2: ModelInfo(
        versions=['meta/llama-3.2-90b-vision-instruct-maas'],
        label='llama-3.2',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=['text', 'json']
        )
    )
}


class ModelGarden:
    @classmethod
    def to_openai_compatible_model(
        cls,
        ai: GenkitRegistry,
        model: str,
        location: str,
        project_id: str
    ):
        if model not in SUPPORTED_OPENAI_FORMAT_MODELS:
            raise ValueError(f"Model '{model}' is not supported.")
        model_version = SUPPORTED_OPENAI_FORMAT_MODELS[model].versions[0]
        open_ai_compat = OpenAICompatibleModel(
            model_version,
            project_id,
            location
        )
        supports = SUPPORTED_OPENAI_FORMAT_MODELS[model].supports.model_dump()

        ai.define_model(
            name=f'vertexai/{model}',
            fn=open_ai_compat.generate,
            config_schema=OpenAIConfig,
            metadata={
                'model': {
                    'supports': supports
                }
            }

        )


