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

"""Unittests for VertexAI Model Garden Plugin."""

import pytest
from genkit.core.action.types import ActionKind
from genkit.plugins.vertex_ai.model_garden.modelgarden_plugin import ModelGardenPlugin


@pytest.mark.parametrize(
    'model_name, expected_supports',
    [
        (
            'modelgarden/anthropic/claude-3-5-sonnet-v2@20241022',
            {
                'multiturn': True,
                'media': True,
                'tools': True,
                'system_role': True,
                'output': ['text', 'json_mode'],
            },
        ),
        (
            'modelgarden/anthropic/claude-3-haiku@20240307',
            {
                'multiturn': True,
                'media': True,
                'tools': True,
                'system_role': True,
                'output': ['text', 'json_mode'],
            },
        ),
        (
            'modelgarden/anthropic/unknown-model',
            {
                'multiturn': True,
                'media': True,
                'tools': True,
                'system_role': True,
                'output': ['text', 'json'],
            },
        ),
    ],
)
def test_create_model_action_anthropic(model_name, expected_supports):
    """Test _create_model_action for Anthropic models."""
    plugin = ModelGardenPlugin(project_id='test-project', location='us-central1')
    
    # define_model is not called directly, but we can test _create_model_action
    # or resolve which calls it
    action = plugin._create_model_action(model_name)
    
    assert action is not None
    assert action.metadata is not None
    assert 'model' in action.metadata
    
    model_info = action.metadata['model']
    supports = model_info['supports']
    
    # Check that all expected keys are present and match
    for key, value in expected_supports.items():
        assert supports[key] == value

