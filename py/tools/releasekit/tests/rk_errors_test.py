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

"""Tests for releasekit.errors module."""

from __future__ import annotations

import dataclasses
import io
from unittest.mock import patch

from releasekit.errors import (
    ERRORS,
    E,
    ErrorCode,
    ErrorInfo,
    ReleaseKitError,
    ReleaseKitWarning,
    explain,
    render_error,
    render_warning,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_config_codes_start_with_rk_config(self) -> None:
        """Configuration error codes should start with RK-CONFIG."""
        config_codes = [c for c in ErrorCode if c.value.startswith('RK-CONFIG')]
        assert len(config_codes) >= 4

    def test_all_codes_have_rk_prefix(self) -> None:
        """Every error code must start with 'RK-'."""
        for code in ErrorCode:
            assert code.value.startswith('RK-'), f'{code.name} does not start with RK-'

    def test_no_duplicate_values(self) -> None:
        """Error code values must be unique."""
        values = [c.value for c in ErrorCode]
        assert len(values) == len(set(values)), 'Duplicate error code values found'

    def test_e_alias(self) -> None:
        """E should be an alias for ErrorCode."""
        assert E is ErrorCode
        assert E.CONFIG_NOT_FOUND is ErrorCode.CONFIG_NOT_FOUND


class TestErrorInfo:
    """Tests for ErrorInfo dataclass."""

    def test_frozen(self) -> None:
        """ErrorInfo instances should be immutable."""
        assert dataclasses.is_dataclass(ErrorInfo)
        info = ErrorInfo(code=E.CONFIG_NOT_FOUND, message='test')
        raised = False
        try:
            info.__setattr__('message', 'changed')
        except AttributeError:
            raised = True
        assert raised, 'ErrorInfo should be frozen'

    def test_default_hint(self) -> None:
        """Hint should default to empty string."""
        info = ErrorInfo(code=E.CONFIG_NOT_FOUND, message='test')
        assert info.hint == ''

    def test_with_hint(self) -> None:
        """Hint should be settable via constructor."""
        info = ErrorInfo(code=E.CONFIG_NOT_FOUND, message='test', hint='fix it')
        assert info.hint == 'fix it'


class TestReleaseKitError:
    """Tests for ReleaseKitError exception."""

    def test_message_includes_code(self) -> None:
        """Exception message should include the RK-XXXX code."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='test message')
        assert 'RK-CONFIG-NOT-FOUND' in str(err)
        assert 'test message' in str(err)

    def test_code_property(self) -> None:
        """Code property should return the ErrorCode."""
        err = ReleaseKitError(code=E.BUILD_FAILED, message='build broke')
        assert err.code is E.BUILD_FAILED

    def test_hint_property(self) -> None:
        """Hint property should return the hint string."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='missing', hint='run init')
        assert err.hint == 'run init'

    def test_hint_default_empty(self) -> None:
        """Hint should default to empty string."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='missing')
        assert err.hint == ''

    def test_is_exception(self) -> None:
        """ReleaseKitError should be an Exception."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='test')
        assert isinstance(err, Exception)

    def test_info_attribute(self) -> None:
        """Error should carry an ErrorInfo instance."""
        err = ReleaseKitError(code=E.GRAPH_CYCLE_DETECTED, message='cycle found')
        assert isinstance(err.info, ErrorInfo)
        assert err.info.code is E.GRAPH_CYCLE_DETECTED


class TestReleaseKitWarning:
    """Tests for ReleaseKitWarning."""

    def test_is_user_warning(self) -> None:
        """ReleaseKitWarning should be a UserWarning subclass."""
        warn = ReleaseKitWarning(code=E.PREFLIGHT_GH_UNAVAILABLE, message='gh missing')
        assert isinstance(warn, UserWarning)

    def test_code_and_hint(self) -> None:
        """Warning should carry code and hint."""
        warn = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='shallow clone',
            hint='fetch --unshallow',
        )
        assert warn.code is E.PREFLIGHT_SHALLOW_CLONE
        assert warn.hint == 'fetch --unshallow'


class TestErrorCatalog:
    """Tests for the ERRORS catalog."""

    def test_catalog_entries_have_messages(self) -> None:
        """Every catalog entry should have a non-empty message."""
        for code, info in ERRORS.items():
            assert info.message, f'{code.value} has empty message'

    def test_catalog_codes_match(self) -> None:
        """ErrorInfo.code should match the key in the ERRORS dict."""
        for code, info in ERRORS.items():
            assert info.code is code, f'Key {code.value} does not match info.code {info.code.value}'


class TestExplain:
    """Tests for the explain() function."""

    def test_known_code(self) -> None:
        """Explain should return a message for known codes."""
        result = explain('RK-CONFIG-NOT-FOUND')
        assert result is not None
        assert 'RK-CONFIG-NOT-FOUND' in result
        assert 'pyproject.toml' in result

    def test_unknown_code(self) -> None:
        """Explain should return None for invalid code strings."""
        result = explain('RK-DOES-NOT-EXIST')
        assert result is None

    def test_invalid_format(self) -> None:
        """Explain should return None for non-RK code strings."""
        result = explain('INVALID')
        assert result is None

    def test_code_without_catalog_entry(self) -> None:
        """Explain should return a fallback for valid codes not in catalog."""
        result = explain('RK-VERSION-INVALID')
        assert result is not None
        assert 'No detailed explanation' in result


class TestRenderError:
    """Tests for render_error function."""

    def test_plain_text_with_hint(self) -> None:
        """render_error writes plain text to a non-TTY stream."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='No config found', hint='Run init')
        buf = io.StringIO()
        render_error(err, file=buf)
        output = buf.getvalue()
        assert 'error[RK-CONFIG-NOT-FOUND]' in output
        assert 'No config found' in output
        assert 'hint: Run init' in output

    def test_plain_text_without_hint(self) -> None:
        """render_error without hint omits the hint line."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='No config found')
        buf = io.StringIO()
        render_error(err, file=buf)
        output = buf.getvalue()
        assert 'error[RK-CONFIG-NOT-FOUND]' in output
        assert 'hint' not in output


class TestRenderWarning:
    """Tests for render_warning function."""

    def test_plain_text_with_hint(self) -> None:
        """render_warning writes plain text to a non-TTY stream."""
        warn = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone',
            hint='fetch --unshallow',
        )
        buf = io.StringIO()
        render_warning(warn, file=buf)
        output = buf.getvalue()
        assert 'warning[RK-PREFLIGHT-SHALLOW-CLONE]' in output
        assert 'Shallow clone' in output
        assert 'hint: fetch --unshallow' in output

    def test_plain_text_without_hint(self) -> None:
        """render_warning without hint omits the hint line."""
        warn = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone',
        )
        buf = io.StringIO()
        render_warning(warn, file=buf)
        output = buf.getvalue()
        assert 'warning[RK-PREFLIGHT-SHALLOW-CLONE]' in output
        assert 'hint' not in output


class TestRenderErrorRich:
    """Tests for render_error with Rich (TTY) output."""

    def test_rich_tty_with_hint(self) -> None:
        """render_error uses Rich when output is a TTY."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='No config', hint='Run init')
        buf = io.StringIO()
        buf.isatty = lambda: True  # type: ignore[assignment]

        with patch('releasekit.errors._HAS_RICH', True):
            render_error(err, file=buf)

        output = buf.getvalue()
        assert 'No config' in output

    def test_rich_tty_without_hint(self) -> None:
        """render_error Rich path without hint."""
        err = ReleaseKitError(code=E.CONFIG_NOT_FOUND, message='No config')
        buf = io.StringIO()
        buf.isatty = lambda: True  # type: ignore[assignment]

        with patch('releasekit.errors._HAS_RICH', True):
            render_error(err, file=buf)

        output = buf.getvalue()
        assert 'No config' in output


class TestRenderWarningRich:
    """Tests for render_warning with Rich (TTY) output."""

    def test_rich_tty_with_hint(self) -> None:
        """render_warning uses Rich when output is a TTY."""
        warn = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone',
            hint='fetch --unshallow',
        )
        buf = io.StringIO()
        buf.isatty = lambda: True  # type: ignore[assignment]

        with patch('releasekit.errors._HAS_RICH', True):
            render_warning(warn, file=buf)

        output = buf.getvalue()
        assert 'Shallow clone' in output

    def test_rich_tty_without_hint(self) -> None:
        """render_warning Rich path without hint."""
        warn = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone',
        )
        buf = io.StringIO()
        buf.isatty = lambda: True  # type: ignore[assignment]

        with patch('releasekit.errors._HAS_RICH', True):
            render_warning(warn, file=buf)

        output = buf.getvalue()
        assert 'Shallow clone' in output
