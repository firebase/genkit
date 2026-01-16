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

"""Tests for xAI plugin."""

from unittest.mock import MagicMock, patch

from genkit.core.error import GenkitError
from genkit.core.registry import ActionKind
from genkit.plugins.xai import XAI, xai_name
from genkit.plugins.xai.model_info import SUPPORTED_XAI_MODELS, get_model_info


def test_xai_name():
    assert xai_name('grok-3') == 'xai/grok-3'


def test_init_with_api_key():
    plugin = XAI(api_key='test-key')
    assert plugin._xai_client is not None
    assert plugin.models == list(SUPPORTED_XAI_MODELS.keys())


def test_init_without_api_key_raises():
    with patch.dict('os.environ', {}, clear=True):
        try:
            XAI()
            assert False, 'Expected GenkitError'
        except GenkitError:
            pass


def test_init_with_env_var():
    with patch.dict('os.environ', {'XAI_API_KEY': 'env-key'}):
        plugin = XAI()
        assert plugin._xai_client is not None


def test_custom_models():
    plugin = XAI(api_key='test-key', models=['grok-3', 'grok-3-mini'])
    assert plugin.models == ['grok-3', 'grok-3-mini']


def test_plugin_initialize():
    registry = MagicMock()
    plugin = XAI(api_key='test-key')
    plugin.initialize(registry)
    assert registry.define_model.call_count == len(SUPPORTED_XAI_MODELS)


def test_resolve_action_model():
    registry = MagicMock()
    plugin = XAI(api_key='test-key')
    plugin.resolve_action(registry, ActionKind.MODEL, 'xai/grok-3')
    registry.define_model.assert_called_once()


def test_supported_models():
    assert len(SUPPORTED_XAI_MODELS) >= 4
    for name, info in SUPPORTED_XAI_MODELS.items():
        assert info.label.startswith('xAI - ')
        assert len(info.versions) > 0
        assert info.supports.tools


def test_get_model_info_known():
    info = get_model_info('grok-3')
    assert 'grok-3' in info.versions[0]
    assert info.supports.multiturn


def test_get_model_info_unknown():
    info = get_model_info('unknown-model')
    assert 'unknown-model' in info.label
