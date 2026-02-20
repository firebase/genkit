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

"""Tests for releasekit.logging module."""

from __future__ import annotations

import logging
from unittest.mock import patch

import releasekit.logging as rl
from releasekit.logging import (
    _REDACTED,
    _build_secret_values,
    _scrub,
    configure_logging,
    get_logger,
    redact_sensitive_values,
)


class TestConfigureLogging:
    """Tests for configure_logging()."""

    def test_default_level_is_info(self) -> None:
        """Default logging level should be INFO."""
        configure_logging()
        assert logging.root.level == logging.INFO

    def test_verbose_sets_debug(self) -> None:
        """Verbose flag should set DEBUG level."""
        configure_logging(verbose=True)
        assert logging.root.level == logging.DEBUG

    def test_quiet_sets_warning(self) -> None:
        """Quiet flag should set WARNING level."""
        configure_logging(quiet=True)
        assert logging.root.level == logging.WARNING

    def test_json_log_does_not_crash(self) -> None:
        """JSON log mode should configure without errors."""
        configure_logging(json_log=True)
        log = get_logger()
        log.info('test_json', key='value')

    def test_idempotent(self) -> None:
        """Calling configure_logging twice should not crash."""
        configure_logging()
        configure_logging(verbose=True)
        assert logging.root.level == logging.DEBUG


class TestGetLogger:
    """Tests for get_logger()."""

    def test_returns_bound_logger(self) -> None:
        """get_logger should return a structlog BoundLogger."""
        configure_logging()
        log = get_logger('test')
        assert log is not None

    def test_default_name(self) -> None:
        """Default logger name should be 'releasekit'."""
        configure_logging()
        log = get_logger()
        assert log is not None

    def test_logger_can_log(self) -> None:
        """Logger should be able to emit messages without crashing."""
        configure_logging(quiet=True)
        log = get_logger('test')
        log.info('test message', key='value')
        log.debug('debug message')
        log.warning('warning message')


class TestRedactSensitiveValues:
    """Tests for the structlog redaction processor."""

    def test_redacts_secret_in_event(self) -> None:
        """Secret value in event string is replaced with [REDACTED]."""
        old = rl._secret_values
        try:
            rl._secret_values = frozenset({'super-secret-key-123'})
            result = redact_sensitive_values(
                None,
                'info',
                {'event': 'key is super-secret-key-123', 'level': 'info'},
            )
            assert result['event'] == f'key is {_REDACTED}'
            assert result['level'] == 'info'
        finally:
            rl._secret_values = old

    def test_redacts_secret_in_kwargs(self) -> None:
        """Secret value in arbitrary kwarg is redacted."""
        old = rl._secret_values
        try:
            rl._secret_values = frozenset({'my-token-value'})
            result = redact_sensitive_values(
                None,
                'warning',
                {'event': 'auth', 'token': 'Bearer my-token-value'},
            )
            assert result['token'] == f'Bearer {_REDACTED}'
        finally:
            rl._secret_values = old

    def test_noop_when_no_secrets(self) -> None:
        """Processor is a no-op when no secret values are loaded."""
        old = rl._secret_values
        try:
            rl._secret_values = frozenset()
            event = {'event': 'hello', 'data': 'world'}
            result = redact_sensitive_values(None, 'info', event)
            assert result is event  # same dict object, untouched
        finally:
            rl._secret_values = old

    def test_non_string_values_pass_through(self) -> None:
        """Non-string values (int, bool, None) are not modified."""
        old = rl._secret_values
        try:
            rl._secret_values = frozenset({'secret'})
            result = redact_sensitive_values(
                None,
                'info',
                {'event': 'test', 'count': 42, 'flag': True, 'empty': None},
            )
            assert result['count'] == 42
            assert result['flag'] is True
            assert result['empty'] is None
        finally:
            rl._secret_values = old

    def test_multiple_secrets_redacted(self) -> None:
        """Multiple different secrets in the same string are all redacted."""
        old = rl._secret_values
        try:
            rl._secret_values = frozenset({'secret-aaa', 'secret-bbb'})
            result = redact_sensitive_values(
                None,
                'info',
                {'event': 'keys: secret-aaa and secret-bbb'},
            )
            assert 'secret-aaa' not in result['event']
            assert 'secret-bbb' not in result['event']
            assert _REDACTED in result['event']
        finally:
            rl._secret_values = old

    def test_short_secrets_not_redacted(self) -> None:
        """Secrets shorter than 8 chars are skipped to prevent over-redaction."""
        old = rl._secret_values
        try:
            rl._secret_values = frozenset({'abc'})
            result = redact_sensitive_values(
                None,
                'info',
                {'event': 'token is abc'},
            )
            assert result['event'] == 'token is abc'
        finally:
            rl._secret_values = old

    def test_scrub_returns_non_strings_unchanged(self) -> None:
        """_scrub passes through non-string types."""
        assert _scrub(42) == 42
        assert _scrub(None) is None
        assert _scrub(3.14) == 3.14


class TestBuildSecretValues:
    """Tests for _build_secret_values()."""

    def test_collects_set_env_vars(self) -> None:
        """Env vars that are set are included in the secret set."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key-123'}, clear=False):
            values = _build_secret_values()
            assert 'test-key-123' in values

    def test_ignores_empty_env_vars(self) -> None:
        """Empty env vars are not included."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': ''}, clear=False):
            values = _build_secret_values()
            assert '' not in values

    def test_ignores_unset_env_vars(self) -> None:
        """Unset env vars produce no entries."""
        with patch.dict('os.environ', {}, clear=True):
            values = _build_secret_values()
            assert len(values) == 0

    def test_configure_logging_populates_secrets(self) -> None:
        """configure_logging() should populate _secret_values from env."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'live-key-xyz'}, clear=False):
            configure_logging(quiet=True)
            assert 'live-key-xyz' in rl._secret_values


class TestRedactionConfig:
    """Tests for redaction configurability."""

    def test_redact_secrets_false_disables_redaction(self) -> None:
        """redact_secrets=False should leave _secret_values empty."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'my-key'}, clear=False):
            configure_logging(quiet=True, redact_secrets=False)
            assert rl._secret_values == frozenset()
            assert rl._redaction_enabled is False

    def test_redact_secrets_true_enables_redaction(self) -> None:
        """redact_secrets=True (default) should populate _secret_values."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'my-key'}, clear=False):
            configure_logging(quiet=True, redact_secrets=True)
            assert 'my-key' in rl._secret_values
            assert rl._redaction_enabled is True

    def test_env_var_override_disables_redaction(self) -> None:
        """RELEASEKIT_REDACT_SECRETS=0 should disable even if param is True."""
        env = {'GEMINI_API_KEY': 'my-key', 'RELEASEKIT_REDACT_SECRETS': '0'}
        with patch.dict('os.environ', env, clear=False):
            configure_logging(quiet=True, redact_secrets=True)
            assert rl._secret_values == frozenset()
            assert rl._redaction_enabled is False

    def test_env_var_1_keeps_redaction_enabled(self) -> None:
        """RELEASEKIT_REDACT_SECRETS=1 should keep redaction on."""
        env = {'GEMINI_API_KEY': 'my-key', 'RELEASEKIT_REDACT_SECRETS': '1'}
        with patch.dict('os.environ', env, clear=False):
            configure_logging(quiet=True, redact_secrets=True)
            assert 'my-key' in rl._secret_values
            assert rl._redaction_enabled is True
