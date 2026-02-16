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

"""Tests for releasekit.changesets — changeset file support."""

from __future__ import annotations

from pathlib import Path

from releasekit.changesets import (
    Changeset,
    changeset_summaries,
    consume_changesets,
    merge_changeset_bumps,
    read_changesets,
)
from releasekit.commit_parsing import BumpType
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# ---------------------------------------------------------------------------
# read_changesets
# ---------------------------------------------------------------------------


class TestReadChangesets:
    """Tests for read_changesets()."""

    def test_reads_valid_changeset(self, tmp_path: Path) -> None:
        """Parse a valid changeset file."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        (cs_dir / 'add-streaming.md').write_text(
            '---\n"genkit": minor\n"genkit-plugin-firebase": patch\n---\n\nAdd streaming support.\n',
            encoding='utf-8',
        )
        result = read_changesets(cs_dir)
        assert len(result) == 1
        assert result[0].bumps == {
            'genkit': BumpType.MINOR,
            'genkit-plugin-firebase': BumpType.PATCH,
        }
        assert result[0].summary == 'Add streaming support.'

    def test_ignores_readme(self, tmp_path: Path) -> None:
        """README.md is ignored."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        (cs_dir / 'README.md').write_text('# Changesets\n', encoding='utf-8')
        result = read_changesets(cs_dir)
        assert len(result) == 0

    def test_skips_invalid_frontmatter(self, tmp_path: Path) -> None:
        """File without frontmatter is skipped."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        (cs_dir / 'bad.md').write_text('No frontmatter here.\n', encoding='utf-8')
        result = read_changesets(cs_dir)
        assert len(result) == 0

    def test_skips_empty_bumps(self, tmp_path: Path) -> None:
        """File with empty frontmatter is skipped."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        (cs_dir / 'empty.md').write_text('---\n---\n\nNothing.\n', encoding='utf-8')
        result = read_changesets(cs_dir)
        assert len(result) == 0

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent directory returns empty list."""
        result = read_changesets(tmp_path / 'nonexistent')
        assert result == []

    def test_multiple_changesets(self, tmp_path: Path) -> None:
        """Multiple changeset files are all read."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        (cs_dir / 'a.md').write_text('---\n"pkg-a": major\n---\n\nBreaking.\n', encoding='utf-8')
        (cs_dir / 'b.md').write_text('---\n"pkg-b": patch\n---\n\nFix.\n', encoding='utf-8')
        result = read_changesets(cs_dir)
        assert len(result) == 2

    def test_unquoted_package_name(self, tmp_path: Path) -> None:
        """Package names without quotes are parsed."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        (cs_dir / 'c.md').write_text('---\ngenkit: minor\n---\n\nFeat.\n', encoding='utf-8')
        result = read_changesets(cs_dir)
        assert len(result) == 1
        assert 'genkit' in result[0].bumps


# ---------------------------------------------------------------------------
# merge_changeset_bumps
# ---------------------------------------------------------------------------


class TestMergeChangesetBumps:
    """Tests for merge_changeset_bumps()."""

    def test_changeset_overrides_lower_bump(self) -> None:
        """Changeset major overrides commit patch."""
        commit_bumps = {'pkg-a': BumpType.PATCH}
        changesets = [Changeset(path=Path('a.md'), bumps={'pkg-a': BumpType.MAJOR})]
        merged = merge_changeset_bumps(commit_bumps, changesets)
        assert merged['pkg-a'] == BumpType.MAJOR

    def test_commit_wins_when_higher(self) -> None:
        """Commit major beats changeset patch."""
        commit_bumps = {'pkg-a': BumpType.MAJOR}
        changesets = [Changeset(path=Path('a.md'), bumps={'pkg-a': BumpType.PATCH})]
        merged = merge_changeset_bumps(commit_bumps, changesets)
        assert merged['pkg-a'] == BumpType.MAJOR

    def test_changeset_adds_new_package(self) -> None:
        """Changeset can add bumps for packages not in commits."""
        commit_bumps = {'pkg-a': BumpType.PATCH}
        changesets = [Changeset(path=Path('a.md'), bumps={'pkg-b': BumpType.MINOR})]
        merged = merge_changeset_bumps(commit_bumps, changesets)
        assert merged['pkg-a'] == BumpType.PATCH
        assert merged['pkg-b'] == BumpType.MINOR

    def test_empty_changesets(self) -> None:
        """Empty changesets returns commit bumps unchanged."""
        commit_bumps = {'pkg-a': BumpType.PATCH}
        merged = merge_changeset_bumps(commit_bumps, [])
        assert merged == commit_bumps

    def test_multiple_changesets_merge(self) -> None:
        """Multiple changesets for same package take highest."""
        commit_bumps: dict[str, BumpType] = {}
        changesets = [
            Changeset(path=Path('a.md'), bumps={'pkg-a': BumpType.PATCH}),
            Changeset(path=Path('b.md'), bumps={'pkg-a': BumpType.MINOR}),
        ]
        merged = merge_changeset_bumps(commit_bumps, changesets)
        assert merged['pkg-a'] == BumpType.MINOR


# ---------------------------------------------------------------------------
# changeset_summaries
# ---------------------------------------------------------------------------


class TestChangesetSummaries:
    """Tests for changeset_summaries()."""

    def test_extracts_summaries(self) -> None:
        """Summaries are extracted per package."""
        changesets = [
            Changeset(path=Path('a.md'), bumps={'pkg-a': BumpType.MINOR}, summary='Add feature'),
            Changeset(path=Path('b.md'), bumps={'pkg-a': BumpType.PATCH, 'pkg-b': BumpType.PATCH}, summary='Fix bug'),
        ]
        result = changeset_summaries(changesets)
        assert result['pkg-a'] == ['Add feature', 'Fix bug']
        assert result['pkg-b'] == ['Fix bug']

    def test_empty_summary_skipped(self) -> None:
        """Changesets with no summary are skipped."""
        changesets = [
            Changeset(path=Path('a.md'), bumps={'pkg-a': BumpType.MINOR}, summary=''),
        ]
        result = changeset_summaries(changesets)
        assert result == {}


# ---------------------------------------------------------------------------
# consume_changesets
# ---------------------------------------------------------------------------


class TestConsumeChangesets:
    """Tests for consume_changesets()."""

    def test_deletes_files(self, tmp_path: Path) -> None:
        """Consumed changeset files are deleted."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        f = cs_dir / 'a.md'
        f.write_text('---\n"pkg": minor\n---\n\nFeat.\n', encoding='utf-8')
        changesets = [Changeset(path=f, bumps={'pkg': BumpType.MINOR})]
        deleted = consume_changesets(changesets)
        assert len(deleted) == 1
        assert not f.exists()

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """Dry run does not delete files."""
        cs_dir = tmp_path / '.changeset'
        cs_dir.mkdir()
        f = cs_dir / 'a.md'
        f.write_text('---\n"pkg": minor\n---\n\nFeat.\n', encoding='utf-8')
        changesets = [Changeset(path=f, bumps={'pkg': BumpType.MINOR})]
        deleted = consume_changesets(changesets, dry_run=True)
        assert len(deleted) == 1
        assert f.exists()
