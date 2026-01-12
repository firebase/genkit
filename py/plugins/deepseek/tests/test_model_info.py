# Copyright 2026 Google LLC
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

"""Tests for DeepSeek model information."""

import pytest

from genkit.plugins.deepseek.model_info import SUPPORTED_DEEPSEEK_MODELS, get_default_model_info


def test_supported_models_exist():
    """Test that supported models are defined."""
    assert 'deepseek-reasoner' in SUPPORTED_DEEPSEEK_MODELS
    assert 'deepseek-chat' in SUPPORTED_DEEPSEEK_MODELS


def test_model_order():
    """Test models are in correct order (matching JS)."""
    keys = list(SUPPORTED_DEEPSEEK_MODELS.keys())
    assert keys[0] == 'deepseek-reasoner'
    assert keys[1] == 'deepseek-chat'


def test_model_info_structure():
    """Test model info has required fields."""
    for model_name, model_info in SUPPORTED_DEEPSEEK_MODELS.items():
        assert model_info.label
        assert model_info.supports
        assert model_info.supports.multiturn is True
        assert model_info.supports.tools is True
        assert model_info.supports.media is False
        assert model_info.supports.system_role is True
        assert 'text' in model_info.supports.output
        assert 'json' in model_info.supports.output


def test_get_default_model_info():
    """Test getting default info for unknown models."""
    info = get_default_model_info('deepseek-future-model')
    assert 'deepseek-future-model' in info.label
    assert info.supports.multiturn is True
    assert info.supports.tools is True
