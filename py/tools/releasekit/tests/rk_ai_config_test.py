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

"""Tests for [ai] config section parsing and AiConfig/AiFeaturesConfig."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from releasekit.ai import _discover_plugins
from releasekit.config import (
    _DEFAULT_AI_MODELS,
    AiConfig,
    AiFeaturesConfig,
    WorkspaceConfig,
    _parse_ai,
    resolve_workspace_ai_config,
)
from releasekit.errors import ReleaseKitError


class TestAiConfigDefaults:
    """Test default AiConfig values."""

    def test_defaults(self) -> None:
        """Test defaults."""
        cfg = AiConfig()
        assert cfg.enabled is True
        assert cfg.models == _DEFAULT_AI_MODELS
        assert cfg.temperature == 0.2
        assert cfg.max_output_tokens == 4096
        assert isinstance(cfg.features, AiFeaturesConfig)

    def test_features_defaults(self) -> None:
        """Test features defaults."""
        f = AiFeaturesConfig()
        assert f.summarize is True
        assert f.enhance is True
        assert f.detect_breaking is True
        assert f.classify is False
        assert f.scope is False
        assert f.migration_guide is True
        assert f.tailor_announce is False
        assert f.draft_advisory is False
        assert f.ai_hints is False


class TestParseAi:
    """Test _parse_ai() validation."""

    def test_empty_section(self) -> None:
        """Test empty section."""
        cfg = _parse_ai({})
        assert cfg.enabled is True
        assert cfg.models == _DEFAULT_AI_MODELS

    def test_custom_models(self) -> None:
        """Test custom models."""
        cfg = _parse_ai({'models': ['ollama/gemma3:12b', 'google-genai/gemini-3.0-flash-preview']})
        assert cfg.models == ['ollama/gemma3:12b', 'google-genai/gemini-3.0-flash-preview']

    def test_disabled(self) -> None:
        """Test disabled."""
        cfg = _parse_ai({'enabled': False})
        assert cfg.enabled is False

    def test_custom_temperature(self) -> None:
        """Test custom temperature."""
        cfg = _parse_ai({'temperature': 0.5})
        assert cfg.temperature == 0.5

    def test_custom_max_tokens(self) -> None:
        """Test custom max tokens."""
        cfg = _parse_ai({'max_output_tokens': 8192})
        assert cfg.max_output_tokens == 8192

    def test_features_override(self) -> None:
        """Test features override."""
        cfg = _parse_ai({'features': {'summarize': False, 'classify': True}})
        assert cfg.features.summarize is False
        assert cfg.features.classify is True
        assert cfg.features.enhance is True  # default preserved

    def test_invalid_key_rejected(self) -> None:
        """Test invalid key rejected."""
        with pytest.raises(ReleaseKitError, match='Unknown key'):
            _parse_ai({'bogus_key': True})

    def test_invalid_enabled_type(self) -> None:
        """Test invalid enabled type."""
        with pytest.raises(ReleaseKitError, match='ai.enabled must be a boolean'):
            _parse_ai({'enabled': 'yes'})

    def test_invalid_models_type(self) -> None:
        """Test invalid models type."""
        with pytest.raises(ReleaseKitError, match='ai.models must be a list'):
            _parse_ai({'models': 'ollama/gemma3:4b'})

    def test_invalid_model_item_type(self) -> None:
        """Test invalid model item type."""
        with pytest.raises(ReleaseKitError, match='ai.models\\[0\\] must be a string'):
            _parse_ai({'models': [123]})

    def test_model_missing_provider_slash(self) -> None:
        """Test model missing provider slash."""
        with pytest.raises(ReleaseKitError, match='provider/model'):
            _parse_ai({'models': ['gemma3:4b']})

    def test_temperature_out_of_range(self) -> None:
        """Test temperature out of range."""
        with pytest.raises(ReleaseKitError, match='between 0.0 and 1.0'):
            _parse_ai({'temperature': 1.5})

    def test_temperature_negative(self) -> None:
        """Test temperature negative."""
        with pytest.raises(ReleaseKitError, match='between 0.0 and 1.0'):
            _parse_ai({'temperature': -0.1})

    def test_temperature_wrong_type(self) -> None:
        """Test temperature wrong type."""
        with pytest.raises(ReleaseKitError, match='ai.temperature must be a number'):
            _parse_ai({'temperature': 'low'})

    def test_max_tokens_zero(self) -> None:
        """Test max tokens zero."""
        with pytest.raises(ReleaseKitError, match='positive integer'):
            _parse_ai({'max_output_tokens': 0})

    def test_max_tokens_negative(self) -> None:
        """Test max tokens negative."""
        with pytest.raises(ReleaseKitError, match='positive integer'):
            _parse_ai({'max_output_tokens': -100})

    def test_features_invalid_key(self) -> None:
        """Test features invalid key."""
        with pytest.raises(ReleaseKitError, match='Unknown key'):
            _parse_ai({'features': {'nonexistent_feature': True}})

    def test_features_invalid_value_type(self) -> None:
        """Test features invalid value type."""
        with pytest.raises(ReleaseKitError, match='must be a boolean'):
            _parse_ai({'features': {'summarize': 'yes'}})

    def test_features_not_a_table(self) -> None:
        """Test features not a table."""
        with pytest.raises(ReleaseKitError, match='ai.features must be a table'):
            _parse_ai({'features': 'invalid'})

    def test_integer_temperature_accepted(self) -> None:
        """Temperature of 0 or 1 (int) should be accepted."""
        cfg = _parse_ai({'temperature': 0})
        assert cfg.temperature == 0.0
        cfg = _parse_ai({'temperature': 1})
        assert cfg.temperature == 1.0

    def test_plugins_default_empty(self) -> None:
        """Plugins default to empty list."""
        cfg = _parse_ai({})
        assert cfg.plugins == []

    def test_plugins_explicit_list(self) -> None:
        """Explicit plugins list is accepted."""
        cfg = _parse_ai({'plugins': ['ollama', 'google-genai']})
        assert cfg.plugins == ['ollama', 'google-genai']

    def test_plugins_single_item(self) -> None:
        """Single-item plugins list is accepted."""
        cfg = _parse_ai({'plugins': ['anthropic']})
        assert cfg.plugins == ['anthropic']

    def test_plugins_not_a_list(self) -> None:
        """Plugins must be a list."""
        with pytest.raises(ReleaseKitError, match='ai.plugins must be a list'):
            _parse_ai({'plugins': 'ollama'})

    def test_plugins_item_not_string(self) -> None:
        """Each plugin must be a string."""
        with pytest.raises(ReleaseKitError, match=r'ai\.plugins\[0\] must be a string'):
            _parse_ai({'plugins': [123]})

    def test_plugins_mixed_types(self) -> None:
        """Mixed types in plugins list rejected."""
        with pytest.raises(ReleaseKitError, match=r'ai\.plugins\[1\] must be a string'):
            _parse_ai({'plugins': ['ollama', 42]})

    def test_announce_feature_default_false(self) -> None:
        """Announce feature defaults to False."""
        cfg = _parse_ai({})
        assert cfg.features.announce is False

    def test_announce_feature_enabled(self) -> None:
        """Announce feature can be enabled."""
        cfg = _parse_ai({'features': {'announce': True}})
        assert cfg.features.announce is True

    def test_announce_feature_disabled(self) -> None:
        """Announce feature can be explicitly disabled."""
        cfg = _parse_ai({'features': {'announce': False}})
        assert cfg.features.announce is False


class TestResolveWorkspaceAiConfig:
    """Test resolve_workspace_ai_config() merging."""

    def test_no_workspace_override(self) -> None:
        """When ws.ai is None, global config returned as-is."""
        global_ai = AiConfig(
            models=['ollama/gemma3:4b'],
            temperature=0.3,
            plugins=['ollama'],
        )
        ws = WorkspaceConfig(label='py')
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result is global_ai

    def test_workspace_overrides_models(self) -> None:
        """Workspace models override global models."""
        global_ai = AiConfig(models=['ollama/gemma3:4b'])
        ws_ai = AiConfig(models=['google-genai/gemini-3.0-flash-preview'])
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.models == ['google-genai/gemini-3.0-flash-preview']

    def test_workspace_overrides_temperature(self) -> None:
        """Workspace temperature overrides global."""
        global_ai = AiConfig(temperature=0.2)
        ws_ai = AiConfig(temperature=0.8)
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.temperature == 0.8

    def test_workspace_inherits_unset_fields(self) -> None:
        """Workspace inherits global fields it doesn't override."""
        global_ai = AiConfig(
            models=['ollama/gemma3:4b'],
            temperature=0.3,
            codename_theme='space',
            plugins=['ollama'],
        )
        # Only override temperature — everything else should inherit.
        ws_ai = AiConfig(temperature=0.9)
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.models == ['ollama/gemma3:4b']
        assert result.temperature == 0.9
        assert result.codename_theme == 'space'
        assert result.plugins == ['ollama']

    def test_workspace_overrides_plugins(self) -> None:
        """Workspace plugins override global plugins."""
        global_ai = AiConfig(plugins=['ollama'])
        ws_ai = AiConfig(plugins=['google-genai', 'anthropic'])
        ws = WorkspaceConfig(label='js', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.plugins == ['google-genai', 'anthropic']

    def test_workspace_overrides_enabled(self) -> None:
        """Workspace can disable AI even if globally enabled."""
        global_ai = AiConfig(enabled=True)
        ws_ai = AiConfig(enabled=False)
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.enabled is False

    def test_workspace_overrides_features(self) -> None:
        """Workspace feature toggles override global ones."""
        global_ai = AiConfig(
            features=AiFeaturesConfig(summarize=True, announce=False),
        )
        ws_ai = AiConfig(
            features=AiFeaturesConfig(announce=True),
        )
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.features.announce is True
        assert result.features.summarize is True  # inherited from global

    def test_workspace_overrides_blocklist_file(self) -> None:
        """Workspace blocklist_file overrides global."""
        global_ai = AiConfig(blocklist_file='global.txt')
        ws_ai = AiConfig(blocklist_file='workspace.txt')
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.blocklist_file == 'workspace.txt'

    def test_workspace_empty_blocklist_inherits_global(self) -> None:
        """Empty workspace blocklist_file inherits global."""
        global_ai = AiConfig(blocklist_file='global.txt')
        ws_ai = AiConfig(blocklist_file='')
        ws = WorkspaceConfig(label='py', ai=ws_ai)
        result = resolve_workspace_ai_config(global_ai, ws)
        assert result.blocklist_file == 'global.txt'


class TestDiscoverPlugins:
    """Test _discover_plugins() from ai.py."""

    def test_auto_discover_from_model_prefixes(self) -> None:
        """Plugins auto-discovered from model string prefixes."""

        class FakeOllama:
            pass

        with patch('releasekit.ai.importlib.import_module') as mock_import:
            mock_module = type('M', (), {'Ollama': FakeOllama})()
            mock_import.return_value = mock_module
            plugins = _discover_plugins(['ollama/gemma3:4b'])
            mock_import.assert_called_once_with('genkit.plugins.ollama')
            assert len(plugins) == 1
            assert isinstance(plugins[0], FakeOllama)

    def test_explicit_plugins_override_auto_discover(self) -> None:
        """Explicit plugins list overrides model-prefix auto-discovery."""

        class FakeGenai:
            pass

        with patch('releasekit.ai.importlib.import_module') as mock_import:
            mock_module = type('M', (), {'GoogleGenai': FakeGenai})()
            mock_import.return_value = mock_module
            plugins = _discover_plugins(
                ['ollama/gemma3:4b'],  # model says ollama
                explicit_plugins=['google-genai'],  # but we force google-genai
            )
            mock_import.assert_called_once_with('genkit.plugins.google_genai')
            assert len(plugins) == 1
            assert isinstance(plugins[0], FakeGenai)

    def test_missing_plugin_logs_warning(self) -> None:
        """Missing plugin produces warning, not error."""
        with patch('releasekit.ai.importlib.import_module', side_effect=ImportError('not found')):
            plugins = _discover_plugins(['ollama/gemma3:4b'])
            assert plugins == []

    def test_unknown_provider_logs_warning(self) -> None:
        """Unknown provider produces warning, not error."""
        plugins = _discover_plugins(['unknown-provider/some-model'])
        assert plugins == []

    def test_multiple_providers_discovered(self) -> None:
        """Multiple providers from model list are all discovered."""

        class FakeOllama:
            pass

        class FakeGenai:
            pass

        call_count = 0

        def fake_import(module_path: str):  # noqa: ANN202
            nonlocal call_count
            call_count += 1
            if 'ollama' in module_path:
                return type('M', (), {'Ollama': FakeOllama})()
            if 'google_genai' in module_path:
                return type('M', (), {'GoogleGenai': FakeGenai})()
            raise ImportError

        with patch('releasekit.ai.importlib.import_module', side_effect=fake_import):
            plugins = _discover_plugins([
                'ollama/gemma3:4b',
                'google-genai/gemini-3.0-flash-preview',
            ])
            assert len(plugins) == 2
            assert call_count == 2

    def test_model_without_slash_ignored(self) -> None:
        """Model strings without '/' are ignored for auto-discovery."""
        plugins = _discover_plugins(['bare-model-name'])
        assert plugins == []
