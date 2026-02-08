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

"""Tests for DeepSeek model helpers and validation logic."""

import logging

import pytest

from genkit.plugins.deepseek.models import (
    DEEPSEEK_PLUGIN_NAME,
    _get_config_value,
    _warn_reasoning_params,
    deepseek_name,
)


class TestDeepseekName:
    """Tests for deepseek_name helper."""

    def test_produces_prefixed_name(self) -> None:
        """Name is prefixed with plugin name and a slash."""
        assert deepseek_name('deepseek-chat') == 'deepseek/deepseek-chat'

    def test_plugin_name_constant(self) -> None:
        """Plugin name constant matches expected value."""
        assert DEEPSEEK_PLUGIN_NAME == 'deepseek'

    def test_arbitrary_name(self) -> None:
        """Works with arbitrary model names."""
        assert deepseek_name('my-custom') == 'deepseek/my-custom'


class TestGetConfigValue:
    """Tests for _get_config_value helper that extracts params from dict or object."""

    def test_dict_existing_key(self) -> None:
        """Returns value for existing dict key."""
        assert _get_config_value({'temperature': 0.7}, 'temperature') == 0.7

    def test_dict_missing_key_returns_none(self) -> None:
        """Returns None for missing dict key."""
        assert _get_config_value({'temperature': 0.7}, 'top_p') is None

    def test_dict_value_zero_is_not_none(self) -> None:
        """Zero is a valid value, not None."""
        assert _get_config_value({'temperature': 0}, 'temperature') == 0

    def test_object_existing_attr(self) -> None:
        """Returns value for existing object attribute."""

        class Config:
            temperature = 0.5

        assert _get_config_value(Config(), 'temperature') == 0.5

    def test_object_missing_attr_returns_none(self) -> None:
        """Returns None for missing object attribute."""

        class Config:
            pass

        assert _get_config_value(Config(), 'temperature') is None


class TestWarnReasoningParams:
    """Tests for _warn_reasoning_params warning emission.

    Reasoning models (deepseek-r1, deepseek-reasoner) silently ignore
    temperature and top_p. The function should warn users about this.
    """

    def test_no_warning_for_chat_model(self, caplog: pytest.LogCaptureFixture) -> None:
        """Chat models never produce warnings, even with temperature set."""
        with caplog.at_level(logging.WARNING):
            _warn_reasoning_params('deepseek-chat', {'temperature': 0.7})
        assert len(caplog.records) == 0

    def test_warning_for_r1_with_temperature(self, caplog: pytest.LogCaptureFixture) -> None:
        """R1 model with temperature triggers exactly one warning."""
        with caplog.at_level(logging.WARNING):
            _warn_reasoning_params('deepseek-r1', {'temperature': 0.7})
        assert len(caplog.records) == 1
        assert 'temperature' in caplog.records[0].message
        assert 'deepseek-r1' in caplog.records[0].message

    def test_warning_for_reasoner_with_top_p(self, caplog: pytest.LogCaptureFixture) -> None:
        """Reasoner model with top_p triggers a warning."""
        with caplog.at_level(logging.WARNING):
            _warn_reasoning_params('deepseek-reasoner', {'top_p': 0.9})
        assert len(caplog.records) == 1
        assert 'top_p' in caplog.records[0].message

    def test_two_warnings_for_both_params(self, caplog: pytest.LogCaptureFixture) -> None:
        """Setting both temperature and top_p triggers two warnings."""
        with caplog.at_level(logging.WARNING):
            _warn_reasoning_params('deepseek-r1', {'temperature': 0.7, 'top_p': 0.9})
        assert len(caplog.records) == 2

    def test_no_warning_when_config_is_none(self, caplog: pytest.LogCaptureFixture) -> None:
        """None config produces no warnings."""
        with caplog.at_level(logging.WARNING):
            _warn_reasoning_params('deepseek-r1', None)
        assert len(caplog.records) == 0

    def test_no_warning_for_unrelated_params(self, caplog: pytest.LogCaptureFixture) -> None:
        """Parameters not in the ignored set don't trigger warnings."""
        with caplog.at_level(logging.WARNING):
            _warn_reasoning_params('deepseek-r1', {'max_tokens': 100})
        assert len(caplog.records) == 0
