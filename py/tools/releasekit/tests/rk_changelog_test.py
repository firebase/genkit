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

"""Tests for releasekit.changelog — structured changelog generation."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from releasekit.changelog import (
    Changelog,
    ChangelogEntry,
    ChangelogSection,
    _render_entry,
    generate_changelog,
    render_changelog,
    write_changelog,
)
from tests._fakes import FakeVCS as _BaseFakeVCS


class FakeVCS(_BaseFakeVCS):
    """FakeVCS that also records the ``first_parent`` flag from ``log()``."""

    last_first_parent: bool = False

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
        first_parent: bool = False,
        no_merges: bool = False,
        max_commits: int = 0,
    ) -> list[str]:
        """Return canned log lines and record first_parent."""
        self.last_first_parent = first_parent
        return await super().log(
            since_tag=since_tag,
            paths=paths,
            format=format,
            first_parent=first_parent,
            no_merges=no_merges,
            max_commits=max_commits,
        )


class TestChangelogEntry:
    """Tests for ChangelogEntry dataclass."""

    def test_basic(self) -> None:
        """Basic entry has type and empty scope."""
        entry = ChangelogEntry(type='feat', description='add streaming')
        if entry.type != 'feat':
            raise AssertionError(f'Expected feat, got {entry.type}')
        if entry.scope != '':
            raise AssertionError(f'Expected empty scope, got {entry.scope}')

    def test_with_scope_and_pr(self) -> None:
        """Entry with scope and PR number preserves both fields."""
        entry = ChangelogEntry(
            type='fix',
            description='race condition',
            scope='publisher',
            pr_number='1234',
            sha='abc1234',
        )
        if entry.scope != 'publisher':
            raise AssertionError(f'Expected publisher, got {entry.scope}')
        if entry.pr_number != '1234':
            raise AssertionError(f'Expected 1234, got {entry.pr_number}')


class TestRenderChangelog:
    """Tests for render_changelog function."""

    def test_simple_changelog(self) -> None:
        """Render a changelog with one section and one entry."""
        changelog = Changelog(
            version='0.5.0',
            sections=[
                ChangelogSection(
                    heading='Features',
                    entries=[
                        ChangelogEntry(type='feat', description='add streaming', sha='abc1234'),
                    ],
                ),
            ],
        )
        md = render_changelog(changelog)
        if '## 0.5.0' not in md:
            raise AssertionError(f'Missing version heading in:\n{md}')
        if '### Features' not in md:
            raise AssertionError(f'Missing section heading in:\n{md}')
        if '- add streaming (abc1234)' not in md:
            raise AssertionError(f'Missing entry in:\n{md}')

    def test_with_date(self) -> None:
        """Date appears in the version heading."""
        changelog = Changelog(version='0.5.0', date='2026-02-10', sections=[])
        md = render_changelog(changelog)
        if '## 0.5.0 (2026-02-10)' not in md:
            raise AssertionError(f'Missing date in heading:\n{md}')

    def test_with_scope(self) -> None:
        """Scoped entries render with bold scope prefix."""
        changelog = Changelog(
            version='1.0.0',
            sections=[
                ChangelogSection(
                    heading='Bug Fixes',
                    entries=[
                        ChangelogEntry(
                            type='fix',
                            description='race condition',
                            scope='publisher',
                            sha='def5678',
                            pr_number='42',
                        ),
                    ],
                ),
            ],
        )
        md = render_changelog(changelog)
        if '- **publisher**: race condition (def5678, #42)' not in md:
            raise AssertionError(f'Missing scoped entry in:\n{md}')

    def test_empty_sections(self) -> None:
        """Empty sections still include the version heading."""
        changelog = Changelog(version='0.5.0', sections=[])
        md = render_changelog(changelog)
        if '## 0.5.0' not in md:
            raise AssertionError(f'Missing version heading in:\n{md}')


class TestGenerateChangelog:
    """Tests for generate_changelog function."""

    @pytest.mark.asyncio
    async def test_groups_by_type(self) -> None:
        """Commits are grouped into sections by type."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming support',
                'bbb2222 fix: race condition in publisher',
                'ccc3333 feat(auth): add OAuth2',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        headings = [s.heading for s in changelog.sections]
        if 'Features' not in headings:
            raise AssertionError(f'Missing Features section: {headings}')
        if 'Bug Fixes' not in headings:
            raise AssertionError(f'Missing Bug Fixes section: {headings}')

    @pytest.mark.asyncio
    async def test_features_before_fixes(self) -> None:
        """Features section appears before Bug Fixes."""
        vcs = FakeVCS(
            log_lines=[
                'bbb2222 fix: a bug',
                'aaa1111 feat: a feature',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        headings = [s.heading for s in changelog.sections]
        feat_idx = headings.index('Features')
        fix_idx = headings.index('Bug Fixes')
        if feat_idx > fix_idx:
            raise AssertionError(f'Features ({feat_idx}) should come before Bug Fixes ({fix_idx})')

    @pytest.mark.asyncio
    async def test_breaking_changes_first(self) -> None:
        """Breaking changes get their own section at the top."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 feat!: remove deprecated API',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='1.0.0')

        headings = [s.heading for s in changelog.sections]
        if headings[0] != 'Breaking Changes':
            raise AssertionError(f'Expected Breaking Changes first, got {headings}')

    @pytest.mark.asyncio
    async def test_excludes_default_types(self) -> None:
        """chore, ci, build, test, style are excluded by default."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 chore: update deps',
                'ccc3333 ci: fix workflow',
                'ddd4444 test: add test',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        types = {e.type for e in all_entries}
        if 'chore' in types:
            raise AssertionError('chore should be excluded')
        if 'feat' not in types:
            raise AssertionError('feat should be included')

    @pytest.mark.asyncio
    async def test_include_all_types(self) -> None:
        """Empty exclude set includes everything."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 chore: update deps',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0', exclude_types=frozenset())

        all_entries = [e for s in changelog.sections for e in s.entries]
        types = {e.type for e in all_entries}
        if 'chore' not in types:
            raise AssertionError('chore should be included with empty exclude set')

    @pytest.mark.asyncio
    async def test_extracts_pr_reference(self) -> None:
        """PR references (#1234) are extracted from descriptions."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming (#42)',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        entry = changelog.sections[0].entries[0]
        if entry.pr_number != '42':
            raise AssertionError(f'Expected PR 42, got {entry.pr_number}')
        if '#42' in entry.description:
            raise AssertionError(f'PR ref should be removed from description: {entry.description}')

    @pytest.mark.asyncio
    async def test_non_conventional_commits_skipped(self) -> None:
        """Non-conventional commit messages are silently skipped."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 just a regular commit message',
                'ccc3333 Merge pull request #123',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        if len(all_entries) != 1:
            raise AssertionError(f'Expected 1 entry, got {len(all_entries)}')

    @pytest.mark.asyncio
    async def test_empty_log(self) -> None:
        """Empty git log produces empty changelog."""
        vcs = FakeVCS(log_lines=[])
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        if changelog.sections:
            raise AssertionError(f'Expected no sections, got {len(changelog.sections)}')

    @pytest.mark.asyncio
    async def test_scope_preserved(self) -> None:
        """Commit scope is preserved in entries."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat(auth): add OAuth2',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        entry = changelog.sections[0].entries[0]
        if entry.scope != 'auth':
            raise AssertionError(f'Expected scope auth, got {entry.scope}')

    @pytest.mark.asyncio
    async def test_breaking_chore_not_excluded(self) -> None:
        """Breaking changes are never excluded, even if the type is excluded."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 chore!: drop Python 3.9 support',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='1.0.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        if len(all_entries) != 1:
            raise AssertionError(f'Breaking chore should be included, got {len(all_entries)}')

    @pytest.mark.asyncio
    async def test_perf_included(self) -> None:
        """perf: type is included by default."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 perf: optimize hot path',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        headings = [s.heading for s in changelog.sections]
        if 'Performance' not in headings:
            raise AssertionError(f'Expected Performance section: {headings}')

    @pytest.mark.asyncio
    async def test_render_round_trip(self) -> None:
        """Generate + render produces valid markdown."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming (#42)',
                'bbb2222 fix(publisher): race condition',
                'ccc3333 feat!: remove deprecated API',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='1.0.0', date='2026-02-10')
        md = render_changelog(changelog)

        if '## 1.0.0 (2026-02-10)' not in md:
            raise AssertionError(f'Missing heading:\n{md}')
        if '### Breaking Changes' not in md:
            raise AssertionError(f'Missing breaking section:\n{md}')
        if '### Features' not in md:
            raise AssertionError(f'Missing features section:\n{md}')
        if '### Bug Fixes' not in md:
            raise AssertionError(f'Missing fixes section:\n{md}')

    @pytest.mark.asyncio
    async def test_first_parent_passed_to_vcs(self) -> None:
        """generate_changelog passes first_parent=True to vcs.log()."""
        vcs = FakeVCS(log_lines=['aaa1111 feat: something'])
        await generate_changelog(vcs=vcs, version='0.5.0')

        if not vcs.last_first_parent:
            raise AssertionError('Expected first_parent=True to be passed to vcs.log()')


class TestWriteChangelog:
    """Tests for write_changelog — writing CHANGELOG.md to disk."""

    def test_creates_new_file(self, tmp_path: Path) -> None:
        """Creates a new CHANGELOG.md when none exists."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        rendered = '## 0.5.0 (2026-02-10)\n\n### Features\n\n- add streaming (abc1234)\n'

        result = write_changelog(changelog_path, rendered)

        if not result:
            raise AssertionError('Should return True for new file')
        content = changelog_path.read_text(encoding='utf-8')
        if '# Changelog' not in content:
            raise AssertionError(f'Missing heading:\n{content}')
        if '## 0.5.0' not in content:
            raise AssertionError(f'Missing version section:\n{content}')

    def test_prepends_to_existing(self, tmp_path: Path) -> None:
        """Prepends new section below # Changelog heading in existing file."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        existing = '# Changelog\n\n## 0.4.0 (2026-01-01)\n\n### Bug Fixes\n\n- old fix\n'
        changelog_path.write_text(existing, encoding='utf-8')

        rendered = '## 0.5.0 (2026-02-10)\n\n### Features\n\n- new feature\n'
        result = write_changelog(changelog_path, rendered)

        if not result:
            raise AssertionError('Should return True')
        content = changelog_path.read_text(encoding='utf-8')
        # New version should appear before old version.
        idx_new = content.index('## 0.5.0')
        idx_old = content.index('## 0.4.0')
        if idx_new > idx_old:
            raise AssertionError(f'New version should come before old:\n{content}')
        # Old content should still be present.
        if '- old fix' not in content:
            raise AssertionError(f'Old content missing:\n{content}')

    def test_skips_duplicate_version(self, tmp_path: Path) -> None:
        """Skips writing if version heading already exists in file."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        existing = '# Changelog\n\n## 0.5.0 (2026-02-10)\n\n### Features\n\n- existing\n'
        changelog_path.write_text(existing, encoding='utf-8')

        rendered = '## 0.5.0 (2026-02-10)\n\n### Features\n\n- duplicate\n'
        result = write_changelog(changelog_path, rendered)

        if result:
            raise AssertionError('Should return False for duplicate')
        content = changelog_path.read_text(encoding='utf-8')
        if '- duplicate' in content:
            raise AssertionError(f'Duplicate content should not be written:\n{content}')

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """Dry run returns True but does not create the file."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        rendered = '## 0.5.0\n\n### Features\n\n- something\n'

        result = write_changelog(changelog_path, rendered, dry_run=True)

        if not result:
            raise AssertionError('Dry run should return True')
        if changelog_path.exists():
            raise AssertionError('Dry run should not create file')

    def test_prepends_without_heading(self, tmp_path: Path) -> None:
        """Prepends with heading when existing file has no # Changelog heading."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        existing = '## 0.4.0\n\n- old stuff\n'
        changelog_path.write_text(existing, encoding='utf-8')

        rendered = '## 0.5.0\n\n### Features\n\n- new stuff\n'
        result = write_changelog(changelog_path, rendered)

        if not result:
            raise AssertionError('Should return True')
        content = changelog_path.read_text(encoding='utf-8')
        if not content.startswith('# Changelog'):
            raise AssertionError(f'Should start with heading:\n{content}')
        if '- old stuff' not in content:
            raise AssertionError(f'Old content missing:\n{content}')

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Creates parent directories if they don't exist."""
        changelog_path = tmp_path / 'nested' / 'pkg' / 'CHANGELOG.md'
        rendered = '## 0.1.0\n\n### Features\n\n- init\n'

        result = write_changelog(changelog_path, rendered)

        if not result:
            raise AssertionError('Should return True')
        if not changelog_path.exists():
            raise AssertionError('File should exist')


class TestLinkedIssues:
    """Tests for linked issue extraction and rendering in changelog entries."""

    @pytest.mark.asyncio
    async def test_fixes_extracted(self) -> None:
        """Fixes #N is extracted from commit messages."""
        vcs = FakeVCS(
            log_lines=[
                'abc1234 fix(auth): resolve login bug (#42) Fixes #100',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')
        assert len(changelog.sections) == 1
        entry = changelog.sections[0].entries[0]
        assert '100' in entry.issues

    @pytest.mark.asyncio
    async def test_closes_extracted(self) -> None:
        """Closes #N is extracted from commit messages."""
        vcs = FakeVCS(
            log_lines=[
                'abc1234 feat: add feature Closes #200',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')
        entry = changelog.sections[0].entries[0]
        assert '200' in entry.issues

    @pytest.mark.asyncio
    async def test_resolves_extracted(self) -> None:
        """Resolves #N is extracted from commit messages."""
        vcs = FakeVCS(
            log_lines=[
                'abc1234 fix: patch thing Resolves #300',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')
        entry = changelog.sections[0].entries[0]
        assert '300' in entry.issues

    @pytest.mark.asyncio
    async def test_multiple_issues(self) -> None:
        """Multiple issue refs are all extracted."""
        vcs = FakeVCS(
            log_lines=[
                'abc1234 feat: big change Fixes #10 Closes #20',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')
        entry = changelog.sections[0].entries[0]
        assert '10' in entry.issues
        assert '20' in entry.issues

    @pytest.mark.asyncio
    async def test_no_issues(self) -> None:
        """Commits without issue refs have empty issues tuple."""
        vcs = FakeVCS(
            log_lines=[
                'abc1234 feat: plain feature',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')
        entry = changelog.sections[0].entries[0]
        assert entry.issues == ()

    def test_render_entry_with_issues(self) -> None:
        """Rendered entry includes 'closes #N' suffix."""
        entry = ChangelogEntry(
            type='fix',
            description='resolve bug',
            sha='abc1234',
            issues=('100', '200'),
        )
        rendered = _render_entry(entry)
        assert 'closes #100, #200' in rendered

    def test_render_entry_without_issues(self) -> None:
        """Rendered entry without issues has no closes suffix."""
        entry = ChangelogEntry(
            type='feat',
            description='add thing',
            sha='abc1234',
        )
        rendered = _render_entry(entry)
        assert 'closes' not in rendered


class TestNullByteRegression:
    r"""Regression tests for the embedded null byte fix.

    The default log_format in generate_changelog must use git's ``%x00``
    escape (which git interprets in output) rather than a literal Python
    ``\\x00`` byte.  A literal null byte in the format string causes
    ``ValueError: embedded null byte`` when passed to ``subprocess.Popen``
    on Linux because ``execve(2)`` rejects null bytes in argv.

    See: https://github.com/firebase/genkit/actions/runs/.../job/...
    """

    def test_default_log_format_has_no_literal_null_bytes(self) -> None:
        """Default log_format must not contain literal null bytes.

        Literal null bytes in command-line arguments cause ValueError on
        Linux.  The format string should use git's ``%x00`` escape instead.
        """
        sig = inspect.signature(generate_changelog)
        default_fmt = sig.parameters['log_format'].default
        if '\x00' in default_fmt:
            raise AssertionError(
                f'log_format default contains literal null byte: {default_fmt!r}. '
                'Use git escape %x00 instead of Python \\x00.'
            )
        if '%x00' not in default_fmt:
            raise AssertionError(f'log_format default should use %x00 escape: {default_fmt!r}')

    @pytest.mark.asyncio
    async def test_null_byte_separated_lines_parsed(self) -> None:
        r"""Lines with \\x00 separators are parsed into SHA, author, subject."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111\x00Alice\x00feat: add streaming',
                'bbb2222\x00Bob\x00fix: race condition',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        assert len(all_entries) == 2
        descriptions = {e.description for e in all_entries}
        assert 'add streaming' in descriptions
        assert 'race condition' in descriptions

    @pytest.mark.asyncio
    async def test_null_byte_author_extracted(self) -> None:
        """Author field is extracted from null-byte-separated lines."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111\x00Alice\x00feat: add streaming',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        entry = changelog.sections[0].entries[0]
        assert entry.author == 'Alice'

    @pytest.mark.asyncio
    async def test_space_separated_fallback(self) -> None:
        """Legacy space-separated lines still work (no author)."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        entry = changelog.sections[0].entries[0]
        assert entry.author == ''
        assert entry.description == 'add streaming'

    @pytest.mark.asyncio
    async def test_malformed_null_byte_line_skipped(self) -> None:
        """Lines with only one null-byte field are skipped (< 3 parts)."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111\x00incomplete',
                'bbb2222\x00Bob\x00feat: valid commit',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        assert len(all_entries) == 1
        assert all_entries[0].description == 'valid commit'

    @pytest.mark.asyncio
    async def test_mixed_formats(self) -> None:
        """Mix of null-byte-separated and space-separated lines both parse."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111\x00Alice\x00feat: from null format',
                'bbb2222 fix: from space format',
            ]
        )
        changelog = await generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        assert len(all_entries) == 2
        authors = {e.author for e in all_entries}
        assert 'Alice' in authors
        assert '' in authors
