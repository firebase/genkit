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

"""Unittests for VertexAI Model Garden Models."""

from unittest.mock import patch

import pytest

from genkit.plugins.vertex_ai.model_garden.model_garden import ModelGarden


@pytest.fixture
@patch('genkit.plugins.vertex_ai.model_garden.model_garden.OpenAIClient')
def model_garden_instance(client):
    """Model Garden fixture."""
    return ModelGarden(model='test', location='us-central1', project_id='project')


@pytest.mark.parametrize(
    'model_name, expected',
    [
        (
            'meta/llama-3.1-405b-instruct-maas',
            {
                'name': 'ModelGarden - Meta - llama-3.1',
                'supports': {
                    'constrained': None,
                    'content_type': None,
                    'context': None,
                    'long_running': False,
                    'multiturn': True,
                    'media': False,
                    'tools': True,
                    'system_role': True,
                    'output': [
                        'json_mode',
                        'text',
                    ],
                    'tool_choice': None,
                },
            },
        ),
        (
            'meta/lazaro-model-pro-max',
            {
                'name': 'ModelGarden - meta/lazaro-model-pro-max',
                'supports': {
                    'constrained': None,
                    'content_type': None,
                    'context': None,
                    'long_running': None,
                    'multiturn': True,
                    'media': True,
                    'tools': True,
                    'system_role': True,
                    'output': [
                        'json_mode',
                        'text',
                    ],
                    'tool_choice': None,
                },
            },
        ),

    ],
)
def test_get_model_info(model_name, expected, model_garden_instance) -> None:
    """Unittest for get_model_info."""
    model_garden_instance.name = model_name

    result = model_garden_instance.get_model_info()

    assert result == expected


from genkit.plugins.vertex_ai.model_garden.modelgarden_plugin import ModelGardenPlugin
from genkit.plugins.vertex_ai.model_garden.llama import SUPPORTED_LLAMA_MODELS
from genkit.plugins.vertex_ai.model_garden.mistral import SUPPORTED_MISTRAL_MODELS

class TestLlamaIntegration:
    def test_llama_model_lookup(self):
        """Test that Llama models are correctly identified and configured."""
        plugin = ModelGardenPlugin(project_id='test-project', location='us-central1')
        model_name = 'modelgarden/meta/llama-3.2-90b-vision-instruct-maas'
        
        action = plugin._create_model_action(model_name)
        
        assert action is not None
        assert action.name == model_name
        
        metadata = action.metadata['model']
        expected_supports = SUPPORTED_LLAMA_MODELS['meta/llama-3.2-90b-vision-instruct-maas'].supports.model_dump()
        
        # Verify capabilities match definition
        assert metadata['supports'] == expected_supports
        assert metadata['supports']['multiturn'] is True
        assert metadata['supports']['tools'] is True


class TestMistralIntegration:
    @patch('mistralai_gcp.MistralGoogleCloud')
    def test_mistral_model_lookup_native(self, mock_client_cls):
        """Test that Mistral models trigger native client path."""
        plugin = ModelGardenPlugin(project_id='test-project', location='us-central1')
        model_name = 'modelgarden/mistral-medium-3'
        
        action = plugin._create_model_action(model_name)
        
        # Should instantiate MistralGoogleCloud
        mock_client_cls.assert_called_once()
        
        assert action is not None
        assert action.name == model_name
        
        metadata = action.metadata['model']
        # Check supports from mistral.py
        expected = SUPPORTED_MISTRAL_MODELS['mistral-medium-3'].supports.model_dump()
        assert metadata['supports'] == expected
        assert metadata['supports']['output'] == ['text']
