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

"""Tests for releasekit.ai.resolve_ai_config (CLI/env override merging)."""

from __future__ import annotations

import pytest
from releasekit.ai import resolve_ai_config
from releasekit.config import AiConfig


@pytest.fixture()
def base_config() -> AiConfig:
    """Base config."""
    return AiConfig(
        enabled=True,
        models=['ollama/gemma3:4b', 'google-genai/gemini-3.0-flash-preview'],
    )


class TestResolveAiConfig:
    """Test CLI/env override merging."""

    def test_no_overrides(self, base_config: AiConfig) -> None:
        """Test no overrides."""
        result = resolve_ai_config(base_config)
        assert result.enabled is True
        assert result.models == base_config.models

    def test_no_ai_flag(self, base_config: AiConfig) -> None:
        """Test no ai flag."""
        result = resolve_ai_config(base_config, no_ai=True)
        assert result.enabled is False
        assert result.models == base_config.models  # models preserved

    def test_model_override(self, base_config: AiConfig) -> None:
        """Test model override."""
        result = resolve_ai_config(base_config, model='ollama/gemma3:12b')
        assert result.models == ['ollama/gemma3:12b']
        assert result.enabled is True

    def test_env_no_ai(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test env no ai."""
        monkeypatch.setenv('RELEASEKIT_NO_AI', '1')
        result = resolve_ai_config(base_config)
        assert result.enabled is False

    def test_env_no_ai_true(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test env no ai true."""
        monkeypatch.setenv('RELEASEKIT_NO_AI', 'true')
        result = resolve_ai_config(base_config)
        assert result.enabled is False

    def test_env_no_ai_yes(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test env no ai yes."""
        monkeypatch.setenv('RELEASEKIT_NO_AI', 'yes')
        result = resolve_ai_config(base_config)
        assert result.enabled is False

    def test_env_no_ai_ignored_when_zero(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test env no ai ignored when zero."""
        monkeypatch.setenv('RELEASEKIT_NO_AI', '0')
        result = resolve_ai_config(base_config)
        assert result.enabled is True

    def test_env_models(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test env models."""
        monkeypatch.setenv('RELEASEKIT_AI_MODELS', 'ollama/phi4-mini,google-genai/gemini-3.0-flash-preview')
        result = resolve_ai_config(base_config)
        assert result.models == ['ollama/phi4-mini', 'google-genai/gemini-3.0-flash-preview']

    def test_cli_model_overrides_env_models(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test cli model overrides env models."""
        monkeypatch.setenv('RELEASEKIT_AI_MODELS', 'ollama/phi4-mini')
        result = resolve_ai_config(base_config, model='ollama/gemma3:12b')
        assert result.models == ['ollama/gemma3:12b']

    def test_cli_no_ai_overrides_env_enabled(self, base_config: AiConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-ai flag wins over RELEASEKIT_NO_AI=0."""
        monkeypatch.setenv('RELEASEKIT_NO_AI', '0')
        result = resolve_ai_config(base_config, no_ai=True)
        assert result.enabled is False

    def test_temperature_preserved(self, base_config: AiConfig) -> None:
        """Test temperature preserved."""
        result = resolve_ai_config(base_config, model='ollama/gemma3:4b')
        assert result.temperature == base_config.temperature

    def test_features_preserved(self, base_config: AiConfig) -> None:
        """Test features preserved."""
        result = resolve_ai_config(base_config, no_ai=True)
        assert result.features == base_config.features
