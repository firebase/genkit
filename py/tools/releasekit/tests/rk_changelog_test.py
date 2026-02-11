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

from releasekit.backends._run import CommandResult
from releasekit.changelog import (
    Changelog,
    ChangelogEntry,
    ChangelogSection,
    generate_changelog,
    render_changelog,
)

_OK = CommandResult(command=[], returncode=0, stdout='', stderr='')


class FakeVCS:
    """Minimal VCS double that returns canned log lines."""

    def __init__(self, log_lines: list[str] | None = None) -> None:
        """Initialize with optional canned log lines."""
        self._log_lines = log_lines or []

    def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        """Return canned log lines."""
        return self._log_lines

    def tag_exists(self, tag_name: str) -> bool:
        """No tags exist."""
        return False

    def is_clean(self, *, dry_run: bool = False) -> bool:
        """Always clean."""
        return True

    def is_shallow(self) -> bool:
        """Never shallow."""
        return False

    def current_sha(self) -> str:
        """Return a fake SHA."""
        return 'abc123'

    def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return empty diff."""
        return []

    def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op commit."""
        return _OK

    def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op tag."""
        return _OK

    def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op delete_tag."""
        return _OK

    def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op push."""
        return _OK

    def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op checkout_branch."""
        return _OK


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

    def test_groups_by_type(self) -> None:
        """Commits are grouped into sections by type."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming support',
                'bbb2222 fix: race condition in publisher',
                'ccc3333 feat(auth): add OAuth2',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        headings = [s.heading for s in changelog.sections]
        if 'Features' not in headings:
            raise AssertionError(f'Missing Features section: {headings}')
        if 'Bug Fixes' not in headings:
            raise AssertionError(f'Missing Bug Fixes section: {headings}')

    def test_features_before_fixes(self) -> None:
        """Features section appears before Bug Fixes."""
        vcs = FakeVCS(
            log_lines=[
                'bbb2222 fix: a bug',
                'aaa1111 feat: a feature',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        headings = [s.heading for s in changelog.sections]
        feat_idx = headings.index('Features')
        fix_idx = headings.index('Bug Fixes')
        if feat_idx > fix_idx:
            raise AssertionError(f'Features ({feat_idx}) should come before Bug Fixes ({fix_idx})')

    def test_breaking_changes_first(self) -> None:
        """Breaking changes get their own section at the top."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 feat!: remove deprecated API',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='1.0.0')

        headings = [s.heading for s in changelog.sections]
        if headings[0] != 'Breaking Changes':
            raise AssertionError(f'Expected Breaking Changes first, got {headings}')

    def test_excludes_default_types(self) -> None:
        """chore, ci, build, test, style are excluded by default."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 chore: update deps',
                'ccc3333 ci: fix workflow',
                'ddd4444 test: add test',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        types = {e.type for e in all_entries}
        if 'chore' in types:
            raise AssertionError('chore should be excluded')
        if 'feat' not in types:
            raise AssertionError('feat should be included')

    def test_include_all_types(self) -> None:
        """Empty exclude set includes everything."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 chore: update deps',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0', exclude_types=frozenset())

        all_entries = [e for s in changelog.sections for e in s.entries]
        types = {e.type for e in all_entries}
        if 'chore' not in types:
            raise AssertionError('chore should be included with empty exclude set')

    def test_extracts_pr_reference(self) -> None:
        """PR references (#1234) are extracted from descriptions."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming (#42)',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        entry = changelog.sections[0].entries[0]
        if entry.pr_number != '42':
            raise AssertionError(f'Expected PR 42, got {entry.pr_number}')
        if '#42' in entry.description:
            raise AssertionError(f'PR ref should be removed from description: {entry.description}')

    def test_non_conventional_commits_skipped(self) -> None:
        """Non-conventional commit messages are silently skipped."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: a feature',
                'bbb2222 just a regular commit message',
                'ccc3333 Merge pull request #123',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        if len(all_entries) != 1:
            raise AssertionError(f'Expected 1 entry, got {len(all_entries)}')

    def test_empty_log(self) -> None:
        """Empty git log produces empty changelog."""
        vcs = FakeVCS(log_lines=[])
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        if changelog.sections:
            raise AssertionError(f'Expected no sections, got {len(changelog.sections)}')

    def test_scope_preserved(self) -> None:
        """Commit scope is preserved in entries."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat(auth): add OAuth2',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        entry = changelog.sections[0].entries[0]
        if entry.scope != 'auth':
            raise AssertionError(f'Expected scope auth, got {entry.scope}')

    def test_breaking_chore_not_excluded(self) -> None:
        """Breaking changes are never excluded, even if the type is excluded."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 chore!: drop Python 3.9 support',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='1.0.0')

        all_entries = [e for s in changelog.sections for e in s.entries]
        if len(all_entries) != 1:
            raise AssertionError(f'Breaking chore should be included, got {len(all_entries)}')

    def test_perf_included(self) -> None:
        """perf: type is included by default."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 perf: optimize hot path',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='0.5.0')

        headings = [s.heading for s in changelog.sections]
        if 'Performance' not in headings:
            raise AssertionError(f'Expected Performance section: {headings}')

    def test_render_round_trip(self) -> None:
        """Generate + render produces valid markdown."""
        vcs = FakeVCS(
            log_lines=[
                'aaa1111 feat: add streaming (#42)',
                'bbb2222 fix(publisher): race condition',
                'ccc3333 feat!: remove deprecated API',
            ]
        )
        changelog = generate_changelog(vcs=vcs, version='1.0.0', date='2026-02-10')
        md = render_changelog(changelog)

        if '## 1.0.0 (2026-02-10)' not in md:
            raise AssertionError(f'Missing heading:\n{md}')
        if '### Breaking Changes' not in md:
            raise AssertionError(f'Missing breaking section:\n{md}')
        if '### Features' not in md:
            raise AssertionError(f'Missing features section:\n{md}')
        if '### Bug Fixes' not in md:
            raise AssertionError(f'Missing fixes section:\n{md}')
