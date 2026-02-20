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

"""Tests for render_error and render_warning (Rust-style diagnostics)."""

from __future__ import annotations

import io

from releasekit.errors import (
    E,
    ReleaseKitError,
    ReleaseKitWarning,
    render_error,
    render_warning,
)


class TestRenderError:
    """Tests for render_error()."""

    def test_includes_error_label(self) -> None:
        """Output starts with 'error[CODE]:'."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='Config missing.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if 'error[RK-CONFIG-NOT-FOUND]' not in output:
            raise AssertionError(f'Missing error label in: {output!r}')

    def test_includes_message(self) -> None:
        """Output includes the error message."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='No config found.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if 'No config found.' not in output:
            raise AssertionError(f'Missing message in: {output!r}')

    def test_includes_hint(self) -> None:
        """Output includes the hint when provided."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='Config missing.',
            hint="Run 'releasekit init'.",
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if 'hint' not in output:
            raise AssertionError(f'Missing hint label in: {output!r}')
        if 'releasekit init' not in output:
            raise AssertionError(f'Missing hint text in: {output!r}')

    def test_hint_pipe_separator(self) -> None:
        """Output uses '|' and '=' separators like Rust compiler."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='Config missing.',
            hint='Fix it.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if '  |' not in output:
            raise AssertionError(f'Missing pipe separator in: {output!r}')
        if '  = hint:' not in output:
            raise AssertionError(f'Missing = hint: in: {output!r}')

    def test_no_hint_no_separator(self) -> None:
        """No separator lines when hint is empty."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='Config missing.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if '  |' in output:
            raise AssertionError(f'Unexpected pipe in: {output!r}')
        if '  = hint:' in output:
            raise AssertionError(f'Unexpected hint in: {output!r}')

    def test_writes_to_custom_file(self) -> None:
        """Output goes to the specified file object."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='Test message.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)

        if not buf.getvalue():
            raise AssertionError('Nothing written to buffer')


class TestRenderWarning:
    """Tests for render_warning()."""

    def test_includes_warning_label(self) -> None:
        """Output starts with 'warning[CODE]:'."""
        exc = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone detected.',
        )
        buf = io.StringIO()
        render_warning(exc, file=buf)
        output = buf.getvalue()

        if 'warning[RK-PREFLIGHT-SHALLOW-CLONE]' not in output:
            raise AssertionError(f'Missing warning label in: {output!r}')

    def test_includes_message(self) -> None:
        """Output includes the warning message."""
        exc = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone.',
        )
        buf = io.StringIO()
        render_warning(exc, file=buf)
        output = buf.getvalue()

        if 'Shallow clone.' not in output:
            raise AssertionError(f'Missing message in: {output!r}')

    def test_includes_hint(self) -> None:
        """Output includes the hint."""
        exc = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone.',
            hint='Run git fetch --unshallow.',
        )
        buf = io.StringIO()
        render_warning(exc, file=buf)
        output = buf.getvalue()

        if 'hint' not in output:
            raise AssertionError(f'Missing hint in: {output!r}')
        if 'git fetch --unshallow' not in output:
            raise AssertionError(f'Missing hint text in: {output!r}')

    def test_rust_style_format(self) -> None:
        """Output follows Rust-compiler diagnostic format."""
        exc = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Shallow clone.',
            hint='Fetch full history.',
        )
        buf = io.StringIO()
        render_warning(exc, file=buf)
        lines = buf.getvalue().strip().splitlines()

        if len(lines) < 3:
            raise AssertionError(
                f'Expected at least 3 lines (label, pipe, hint), got {len(lines)}: {lines}',
            )

        if not lines[0].startswith('warning['):
            raise AssertionError(f'Line 0 should start with warning[: {lines[0]!r}')
        if '|' not in lines[1]:
            raise AssertionError(f'Line 1 should contain |: {lines[1]!r}')
        if '= hint:' not in lines[2]:
            raise AssertionError(f'Line 2 should contain = hint:: {lines[2]!r}')


class TestBracketPreservation:
    """Square brackets in messages must not be swallowed by Rich markup."""

    def test_error_preserves_brackets_in_message(self) -> None:
        """[tool.releasekit] in message is preserved verbatim."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='No [tool.releasekit] section found.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if '[tool.releasekit]' not in output:
            raise AssertionError(
                f'Brackets were stripped from message: {output!r}',
            )

    def test_error_preserves_brackets_in_hint(self) -> None:
        """[tool.releasekit] in hint is preserved verbatim."""
        exc = ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='Config error.',
            hint='Add [tool.releasekit] to pyproject.toml.',
        )
        buf = io.StringIO()
        render_error(exc, file=buf)
        output = buf.getvalue()

        if '[tool.releasekit]' not in output:
            raise AssertionError(
                f'Brackets were stripped from hint: {output!r}',
            )

    def test_warning_preserves_brackets_in_message(self) -> None:
        """[project] in warning message is preserved."""
        exc = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Missing [project] table.',
        )
        buf = io.StringIO()
        render_warning(exc, file=buf)
        output = buf.getvalue()

        if '[project]' not in output:
            raise AssertionError(
                f'Brackets were stripped from warning: {output!r}',
            )

    def test_warning_preserves_brackets_in_hint(self) -> None:
        """[tool.uv] in warning hint is preserved."""
        exc = ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Warning.',
            hint='Check [tool.uv] section.',
        )
        buf = io.StringIO()
        render_warning(exc, file=buf)
        output = buf.getvalue()

        if '[tool.uv]' not in output:
            raise AssertionError(
                f'Brackets were stripped from hint: {output!r}',
            )
