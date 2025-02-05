# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

import pytest
from genkit.plugins.ollama import Ollama
from genkit.plugins.ollama.models import (
    ModelDefinition,
    OllamaAPITypes,
    OllamaPluginParams,
)
from genkit.plugins.ollama.plugin_api import ollama_api
from genkit.veneer import Genkit


@pytest.fixture
def ollama_model() -> str:
    return 'ollama/gemma2:latest'


@pytest.fixture
def chat_model_plugin_params(ollama_model: str) -> OllamaPluginParams:
    return OllamaPluginParams(
        models=[
            ModelDefinition(
                name=ollama_model.split('/')[-1],
                api_type=OllamaAPITypes.CHAT,
            )
        ],
    )


@pytest.fixture
def genkit_veneer_chat_model(
    ollama_model: str,
    chat_model_plugin_params: OllamaPluginParams,
) -> Genkit:
    return Genkit(
        plugins=[
            Ollama(
                plugin_params=chat_model_plugin_params,
            )
        ],
        model=ollama_model,
    )


@pytest.fixture
def generate_model_plugin_params(ollama_model: str) -> OllamaPluginParams:
    return OllamaPluginParams(
        models=[
            ModelDefinition(
                name=ollama_model.split('/')[-1],
                api_type=OllamaAPITypes.GENERATE,
            )
        ],
    )


@pytest.fixture
def genkit_veneer_generate_model(
    ollama_model: str,
    generate_model_plugin_params: OllamaPluginParams,
) -> Genkit:
    return Genkit(
        plugins=[
            Ollama(
                plugin_params=generate_model_plugin_params,
            )
        ],
        model=ollama_model,
    )


@pytest.fixture
def mock_ollama_api_client():
    with mock.patch.object(ollama_api, 'Client') as mock_ollama_client:
        yield mock_ollama_client


@pytest.fixture
def mock_ollama_api_async_client():
    with mock.patch.object(
        ollama_api, 'AsyncClient'
    ) as mock_ollama_async_client:
        yield mock_ollama_async_client
