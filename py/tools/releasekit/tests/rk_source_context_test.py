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

"""Tests for SourceContext, find_key_line, and read_source_snippet.

These helpers provide source-location context for health check
diagnostics, enabling Rust-style error output with file paths,
line numbers, and code snippets.
"""

from __future__ import annotations

from pathlib import Path

from releasekit.preflight import PreflightResult, SourceContext, find_key_line, read_source_snippet

SAMPLE_TOML = """\
[project]
name = "test-pkg"
version = "1.0.0"
description = "A test package"
requires-python = ">=3.10"

[project.urls]
Homepage = "https://example.com"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""


class TestSourceContext:
    """Tests for the SourceContext dataclass."""

    def test_str_with_line(self) -> None:
        """Format includes line number when > 0."""
        sc = SourceContext(path='foo/pyproject.toml', line=5)
        if str(sc) != 'foo/pyproject.toml:5':
            raise AssertionError(f'Expected foo/pyproject.toml:5, got {sc}')

    def test_str_without_line(self) -> None:
        """Format omits line number when 0."""
        sc = SourceContext(path='foo/pyproject.toml')
        if str(sc) != 'foo/pyproject.toml':
            raise AssertionError(f'Expected foo/pyproject.toml, got {sc}')

    def test_str_with_line_zero(self) -> None:
        """Explicit line=0 omits line number."""
        sc = SourceContext(path='bar.toml', line=0)
        if str(sc) != 'bar.toml':
            raise AssertionError(f'Expected bar.toml, got {sc}')

    def test_defaults(self) -> None:
        """Default values are sensible."""
        sc = SourceContext(path='x.toml')
        if sc.line != 0:
            raise AssertionError(f'Expected line=0, got {sc.line}')
        if sc.key != '':
            raise AssertionError(f'Expected empty key, got {sc.key!r}')
        if sc.label != '':
            raise AssertionError(f'Expected empty label, got {sc.label!r}')

    def test_all_fields(self) -> None:
        """All fields are stored correctly."""
        sc = SourceContext(path='a.toml', line=10, key='version', label='bad')
        if sc.path != 'a.toml':
            raise AssertionError(f'path: {sc.path}')
        if sc.line != 10:
            raise AssertionError(f'line: {sc.line}')
        if sc.key != 'version':
            raise AssertionError(f'key: {sc.key}')
        if sc.label != 'bad':
            raise AssertionError(f'label: {sc.label}')

    def test_frozen(self) -> None:
        """SourceContext is immutable."""
        sc = SourceContext(path='a.toml', line=1)
        try:
            sc.line = 2  # type: ignore[misc]
            raise AssertionError('Should be frozen')
        except AttributeError:
            pass


class TestFindKeyLine:
    """Tests for find_key_line() TOML key/section line lookup."""

    def test_find_simple_key(self) -> None:
        """Finds a simple key assignment."""
        if find_key_line(SAMPLE_TOML, 'name') != 2:
            raise AssertionError('Expected line 2 for name')

    def test_find_version_key(self) -> None:
        """Finds the version key."""
        if find_key_line(SAMPLE_TOML, 'version') != 3:
            raise AssertionError('Expected line 3 for version')

    def test_find_hyphenated_key(self) -> None:
        """Finds a hyphenated key like requires-python."""
        if find_key_line(SAMPLE_TOML, 'requires-python') != 5:
            raise AssertionError('Expected line 5 for requires-python')

    def test_find_key_no_space(self) -> None:
        """Finds key=value without space around =."""
        content = 'name="foo"\nversion="1.0"\n'
        if find_key_line(content, 'name') != 1:
            raise AssertionError('Expected line 1 for name=')

    def test_missing_key_returns_zero(self) -> None:
        """Returns 0 for a key that doesn't exist."""
        if find_key_line(SAMPLE_TOML, 'nonexistent') != 0:
            raise AssertionError('Expected 0 for missing key')

    def test_find_section_header(self) -> None:
        """Finds a [section] header."""
        if find_key_line(SAMPLE_TOML, '', section='project') != 1:
            raise AssertionError('Expected line 1 for [project]')

    def test_find_dotted_section(self) -> None:
        """Finds a [dotted.section] header."""
        if find_key_line(SAMPLE_TOML, '', section='project.urls') != 7:
            raise AssertionError('Expected line 7 for [project.urls]')

    def test_find_build_system_section(self) -> None:
        """Finds [build-system] section."""
        line = find_key_line(SAMPLE_TOML, '', section='build-system')
        if line != 10:
            raise AssertionError(f'Expected line 10 for [build-system], got {line}')

    def test_missing_section_returns_zero(self) -> None:
        """Returns 0 for a section that doesn't exist."""
        if find_key_line(SAMPLE_TOML, '', section='tool.ruff') != 0:
            raise AssertionError('Expected 0 for missing section')

    def test_empty_content(self) -> None:
        """Returns 0 for empty content."""
        if find_key_line('', 'name') != 0:
            raise AssertionError('Expected 0 for empty content')
        if find_key_line('', '', section='project') != 0:
            raise AssertionError('Expected 0 for empty content section search')

    def test_section_with_trailing_space(self) -> None:
        """Finds section headers that have trailing content after ]."""
        content = '[project] # comment\nname = "x"\n'
        # Our search looks for startswith, so this should match.
        line = find_key_line(content, '', section='project')
        # The header has trailing content, but stripped starts with [project].
        # find_key_line checks for exact match or startswith(target + ' ').
        if line != 1:
            raise AssertionError(f'Expected line 1, got {line}')


class TestReadSourceSnippet:
    """Tests for read_source_snippet() file excerpt reader."""

    def test_reads_center_with_context(self, tmp_path: Path) -> None:
        """Reads lines around the center line."""
        f = tmp_path / 'test.toml'
        f.write_text(SAMPLE_TOML, encoding='utf-8')
        snippet = read_source_snippet(str(f), 5, context_lines=2)
        if len(snippet) != 5:
            raise AssertionError(f'Expected 5 lines, got {len(snippet)}')
        # Center line should be line 5.
        if snippet[2] != (5, 'requires-python = ">=3.10"'):
            raise AssertionError(f'Center line mismatch: {snippet[2]}')

    def test_edge_start(self, tmp_path: Path) -> None:
        """Reading near the start of file doesn't go negative."""
        f = tmp_path / 'test.toml'
        f.write_text(SAMPLE_TOML, encoding='utf-8')
        snippet = read_source_snippet(str(f), 1, context_lines=2)
        if snippet[0][0] != 1:
            raise AssertionError(f'First line should be 1, got {snippet[0][0]}')

    def test_edge_end(self, tmp_path: Path) -> None:
        """Reading near the end of file doesn't exceed file length."""
        f = tmp_path / 'test.toml'
        f.write_text(SAMPLE_TOML, encoding='utf-8')
        total_lines = len(SAMPLE_TOML.splitlines())
        snippet = read_source_snippet(str(f), total_lines, context_lines=2)
        if snippet[-1][0] != total_lines:
            raise AssertionError(f'Last line should be {total_lines}, got {snippet[-1][0]}')

    def test_line_zero_returns_empty(self) -> None:
        """Line 0 returns empty list."""
        snippet = read_source_snippet('/dev/null', 0)
        if snippet:
            raise AssertionError('Expected empty for line=0')

    def test_negative_line_returns_empty(self) -> None:
        """Negative line returns empty list."""
        snippet = read_source_snippet('/dev/null', -1)
        if snippet:
            raise AssertionError('Expected empty for negative line')

    def test_missing_file_returns_empty(self) -> None:
        """Non-existent file returns empty list."""
        snippet = read_source_snippet('/nonexistent/file.toml', 5)
        if snippet:
            raise AssertionError('Expected empty for missing file')

    def test_accepts_path_object(self, tmp_path: Path) -> None:
        """Accepts pathlib.Path as well as str."""
        f = tmp_path / 'test.toml'
        f.write_text('line1\nline2\nline3\n', encoding='utf-8')
        snippet = read_source_snippet(f, 2, context_lines=0)
        if len(snippet) != 1:
            raise AssertionError(f'Expected 1 line, got {len(snippet)}')
        if snippet[0] != (2, 'line2'):
            raise AssertionError(f'Expected (2, "line2"), got {snippet[0]}')


class TestPreflightResultSourceContext:
    """Tests for PreflightResult accepting SourceContext in context lists."""

    def test_warning_with_source_context(self) -> None:
        """Warnings can include SourceContext objects."""
        result = PreflightResult()
        ctx = SourceContext(path='a.toml', line=3, key='name', label='bad name')
        result.add_warning('test', 'msg', hint='fix it', context=[ctx, 'plain.toml'])
        if len(result.context['test']) != 2:
            raise AssertionError(f'Expected 2 context items, got {len(result.context["test"])}')
        if not isinstance(result.context['test'][0], SourceContext):
            raise AssertionError('First item should be SourceContext')
        if not isinstance(result.context['test'][1], str):
            raise AssertionError('Second item should be str')

    def test_failure_with_source_context(self) -> None:
        """Failures can include SourceContext objects."""
        result = PreflightResult()
        ctx = SourceContext(path='b.toml', line=10)
        result.add_failure('test', 'msg', hint='fix', context=[ctx])
        if len(result.context['test']) != 1:
            raise AssertionError('Expected 1 context item')
        if result.context['test'][0].line != 10:  # type: ignore[union-attr]
            raise AssertionError('Line should be 10')

    def test_no_context(self) -> None:
        """No context is stored when context=None."""
        result = PreflightResult()
        result.add_warning('test', 'msg')
        if 'test' in result.context:
            raise AssertionError('Should not have context entry')

    def test_hint_stored(self) -> None:
        """Hints are stored for both warnings and failures."""
        result = PreflightResult()
        result.add_warning('w', 'msg', hint='fix w')
        result.add_failure('f', 'msg', hint='fix f')
        if result.hints.get('w') != 'fix w':
            raise AssertionError('Warning hint not stored')
        if result.hints.get('f') != 'fix f':
            raise AssertionError('Failure hint not stored')

    def test_empty_hint_not_stored(self) -> None:
        """Empty hints are not stored."""
        result = PreflightResult()
        result.add_warning('w', 'msg', hint='')
        if 'w' in result.hints:
            raise AssertionError('Empty hint should not be stored')
