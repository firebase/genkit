# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

from genkit.plugins.compat_oai.models.model_info import (
    SUPPORTED_OPENAI_MODELS,
)
from genkit.plugins.compat_oai.openai_plugin import OpenAI, openai_model
from genkit.veneer.registry import GenkitRegistry


def test_openai_plugin_initialize():
    """Test OpenAI plugin registry initialization."""
    registry = MagicMock(spec=GenkitRegistry)
    plugin = OpenAI(api_key='test-key')

    with patch(
        'genkit.plugins.compat_oai.models.OpenAIModelHandler.get_model_handler'
    ) as mock_get_handler:
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler

        plugin.initialize(registry)

        assert mock_get_handler.call_count == len(SUPPORTED_OPENAI_MODELS)
        assert registry.define_model.call_count == len(SUPPORTED_OPENAI_MODELS)


def test_openai_model_function():
    """Test openai_model function."""
    assert openai_model('gpt-4') == 'openai/gpt-4'
