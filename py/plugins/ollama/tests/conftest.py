# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Conftest for ollama plugin."""

from collections.abc import Generator
from unittest import mock

import pytest

from genkit.ai import Genkit
from genkit.plugins.ollama import Ollama
from genkit.plugins.ollama.models import (
    ModelDefinition,
    OllamaAPITypes,
    OllamaPluginParams,
)
from genkit.plugins.ollama.plugin_api import ollama_api


@pytest.fixture
def ollama_model() -> str:
    """Ollama model to use for testing."""
    return 'ollama/gemma2:latest'


@pytest.fixture
def chat_model_plugin_params(ollama_model: str) -> OllamaPluginParams:
    """Chat model plugin parameters."""
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
    """Genkit veneer chat model.

    Args:
        ollama_model: Ollama model to use for testing.
        chat_model_plugin_params: Chat model plugin parameters.

    Returns:
        Genkit veneer chat model.
    """
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
    """Generate model plugin parameters.

    Args:
        ollama_model: Ollama model to use for testing.

    Returns:
        Generate model plugin parameters.
    """
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
    """Genkit veneer generate model.

    Args:
        ollama_model: Ollama model to use for testing.
        generate_model_plugin_params: Generate model plugin parameters.

    Returns:
        Genkit veneer generate model.
    """
    return Genkit(
        plugins=[
            Ollama(
                plugin_params=generate_model_plugin_params,
            )
        ],
        model=ollama_model,
    )


@pytest.fixture
def mock_ollama_api_client() -> Generator[None, None, None]:
    """Mock the ollama API client."""
    with mock.patch.object(ollama_api, 'Client') as mock_ollama_client:
        yield mock_ollama_client


@pytest.fixture
def mock_ollama_api_async_client() -> Generator[None, None, None]:
    """Mock the ollama API async client."""
    with mock.patch.object(ollama_api, 'AsyncClient') as mock_ollama_async_client:
        yield mock_ollama_async_client
