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

"""Tests for log configuration and secret masking.

Covers _mask_value, _redact_secrets, _want_json, _want_colors,
and setup_logging for both JSON and console modes.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/log_config_test.py -v
"""

from unittest.mock import patch

from src.log_config import (
    _mask_value,  # noqa: PLC2701 - testing private function
    _redact_secrets,  # noqa: PLC2701 - testing private function
    _want_colors,  # noqa: PLC2701 - testing private function
    _want_json,  # noqa: PLC2701 - testing private function
    setup_logging,
)


class TestMaskValue:
    """Tests for _mask_value."""

    def test_short_value_fully_masked(self) -> None:
        """Values <= 8 chars are fully masked."""
        assert _mask_value("12345678") == "****"
        assert _mask_value("abc") == "****"
        assert _mask_value("") == "****"

    def test_long_value_partially_masked(self) -> None:
        """Values > 8 chars keep first 4 and last 2."""
        result = _mask_value("AIzaSyD1234567890abcXY")
        assert result.startswith("AIza")
        assert result.endswith("XY")
        assert "****" in result or "***" in result

    def test_nine_char_value(self) -> None:
        """Exactly 9 chars: first 4 + 3 stars + last 2."""
        result = _mask_value("123456789")
        assert result == "1234***89"

    def test_preserves_length_hint(self) -> None:
        """Masked output length matches original (first4 + stars + last2)."""
        value = "sk-1234567890abcdef"
        result = _mask_value(value)
        assert len(result) == len(value)


class TestRedactSecrets:
    """Tests for _redact_secrets structlog processor."""

    def test_redacts_known_field_name(self) -> None:
        """Known secret field names are redacted."""
        event = {"event": "test", "api_key": "AIzaSyD123456789"}
        result = _redact_secrets(None, "info", event)
        assert result["api_key"] != "AIzaSyD123456789"
        assert result["api_key"].startswith("AIza")

    def test_redacts_gemini_api_key(self) -> None:
        """The gemini_api_key field is redacted."""
        event = {"event": "test", "gemini_api_key": "my-secret-key-value"}
        result = _redact_secrets(None, "info", event)
        assert "secret" not in result["gemini_api_key"]

    def test_redacts_password(self) -> None:
        """The password field is redacted."""
        event = {"event": "test", "password": "hunter2abcdef"}
        result = _redact_secrets(None, "info", event)
        assert result["password"] != "hunter2abcdef"  # noqa: S105 - test data, not a real password

    def test_redacts_sentry_dsn(self) -> None:
        """The sentry_dsn field is redacted."""
        event = {"event": "test", "sentry_dsn": "https://abc@sentry.io/123"}
        result = _redact_secrets(None, "info", event)
        assert result["sentry_dsn"] != "https://abc@sentry.io/123"

    def test_redacts_by_pattern(self) -> None:
        """Fields matching secret patterns are redacted."""
        event = {"event": "test", "my_api_key_header": "sk-1234567890"}
        result = _redact_secrets(None, "info", event)
        assert result["my_api_key_header"] != "sk-1234567890"

    def test_redacts_authorization(self) -> None:
        """The authorization field is redacted by exact name match."""
        event = {"event": "test", "authorization": "Bearer eyJhbGciOi"}
        result = _redact_secrets(None, "info", event)
        assert result["authorization"] != "Bearer eyJhbGciOi"

    def test_preserves_non_secret_fields(self) -> None:
        """Non-secret fields are left untouched."""
        event = {"event": "test", "method": "POST", "path": "/health", "status": "200"}
        result = _redact_secrets(None, "info", event)
        assert result["method"] == "POST"
        assert result["path"] == "/health"
        assert result["status"] == "200"

    def test_skips_non_string_values(self) -> None:
        """Non-string values (int, dict, etc.) are left untouched."""
        event = {"event": "test", "api_key": 12345, "token": None}
        result = _redact_secrets(None, "info", event)
        assert result["api_key"] == 12345
        assert result["token"] is None

    def test_handles_hyphenated_field_names(self) -> None:
        """Hyphenated field names like api-key are normalized and redacted."""
        event = {"event": "test", "api-key": "secret-value-here"}
        result = _redact_secrets(None, "info", event)
        assert result["api-key"] != "secret-value-here"

    def test_returns_event_dict(self) -> None:
        """The processor returns the modified event dict."""
        event = {"event": "test"}
        result = _redact_secrets(None, "info", event)
        assert result is event

    def test_credential_pattern_match(self) -> None:
        """Fields containing 'credential' in name are pattern-matched."""
        event = {"event": "test", "user_credential_value": "my-cred-12345"}
        result = _redact_secrets(None, "info", event)
        assert result["user_credential_value"] != "my-cred-12345"

    def test_token_exact_name_match(self) -> None:
        """The 'token' field name is an exact match."""
        event = {"event": "test", "token": "eyJhbGciOiJIUzI1NiJ9"}
        result = _redact_secrets(None, "info", event)
        assert result["token"] != "eyJhbGciOiJIUzI1NiJ9"  # noqa: S105 - test data, not a real token


class TestWantJson:
    """Tests for _want_json."""

    def test_returns_true_for_json(self) -> None:
        """Returns True when LOG_FORMAT=json."""
        with patch.dict("os.environ", {"LOG_FORMAT": "json"}):
            assert _want_json() is True

    def test_returns_true_case_insensitive(self) -> None:
        """Returns True for LOG_FORMAT=JSON (case insensitive)."""
        with patch.dict("os.environ", {"LOG_FORMAT": "JSON"}):
            assert _want_json() is True

    def test_returns_false_for_console(self) -> None:
        """Returns False when LOG_FORMAT=console."""
        with patch.dict("os.environ", {"LOG_FORMAT": "console"}):
            assert _want_json() is False

    def test_returns_false_when_unset(self) -> None:
        """Returns False when LOG_FORMAT is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert _want_json() is False


class TestWantColors:
    """Tests for _want_colors."""

    def test_returns_true_by_default(self) -> None:
        """Colors are enabled by default."""
        with patch.dict("os.environ", {}, clear=True):
            assert _want_colors() is True

    def test_returns_false_when_no_color(self) -> None:
        """Colors are disabled when NO_COLOR is set."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            assert _want_colors() is False

    def test_returns_true_when_no_color_empty(self) -> None:
        """Colors are enabled when NO_COLOR is empty string."""
        with patch.dict("os.environ", {"NO_COLOR": ""}):
            assert _want_colors() is True


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_setup_json_mode(self) -> None:
        """setup_logging in JSON mode does not crash."""
        with patch.dict("os.environ", {"LOG_FORMAT": "json"}):
            setup_logging()

    def test_setup_console_mode(self) -> None:
        """setup_logging in console mode does not crash."""
        with patch.dict("os.environ", {"LOG_FORMAT": "console"}):
            setup_logging()

    def test_setup_default_mode(self) -> None:
        """setup_logging with default env does not crash."""
        with patch.dict("os.environ", {}, clear=True):
            setup_logging()
