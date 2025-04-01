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

from unittest.mock import MagicMock, patch

from genkit.ai import Genkit
from genkit.plugins.compat_oai.models.model_info import SUPPORTED_OPENAI_MODELS
from genkit.plugins.compat_oai.openai_plugin import OpenAI, openai_model


def test_openai_plugin_initialize() -> None:
    """Test OpenAI plugin registry initialization."""
    registry = MagicMock(spec=Genkit)
    plugin = OpenAI(api_key='test-key')

    with patch('genkit.plugins.compat_oai.models.OpenAIModelHandler.get_model_handler') as mock_get_handler:
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler

        plugin.initialize(registry)

        assert mock_get_handler.call_count == len(SUPPORTED_OPENAI_MODELS)
        assert registry.define_model.call_count == len(SUPPORTED_OPENAI_MODELS)


def test_openai_model_function() -> None:
    """Test openai_model function."""
    assert openai_model('gpt-4') == 'openai/gpt-4'
