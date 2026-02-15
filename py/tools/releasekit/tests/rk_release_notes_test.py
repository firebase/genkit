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

"""Tests for releasekit.release_notes — umbrella release notes generation."""

from __future__ import annotations

import pytest
from releasekit.changelog import Changelog, ChangelogEntry, ChangelogSection
from releasekit.release_notes import (
    PackageSummary,
    ReleaseNotes,
    generate_release_notes,
    render_release_notes,
)
from releasekit.versions import PackageVersion, ReleaseManifest
from tests._fakes import FakeVCS


class TestRenderReleaseNotes:
    """Tests for render_release_notes function."""

    def test_basic_render(self) -> None:
        """Render a single-package release note with features."""
        notes = ReleaseNotes(
            version='v0.5.0',
            summaries=[
                PackageSummary(
                    name='genkit',
                    old_version='0.4.0',
                    new_version='0.5.0',
                    changelog=Changelog(
                        version='0.5.0',
                        sections=[
                            ChangelogSection(
                                heading='Features',
                                entries=[
                                    ChangelogEntry(type='feat', description='add streaming', sha='abc1234'),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        )
        md = render_release_notes(notes)
        if '# Release v0.5.0' not in md:
            raise AssertionError(f'Missing title:\n{md}')
        if '### genkit (0.4.0 → 0.5.0)' not in md:
            raise AssertionError(f'Missing package heading:\n{md}')
        if '- add streaming (abc1234)' not in md:
            raise AssertionError(f'Missing entry:\n{md}')

    def test_custom_title(self) -> None:
        """Custom title overrides the default."""
        notes = ReleaseNotes(version='v0.5.0', title='Custom Title')
        md = render_release_notes(notes)
        if '# Custom Title' not in md:
            raise AssertionError(f'Missing custom title:\n{md}')

    def test_custom_preamble(self) -> None:
        """Custom preamble text appears in the output."""
        notes = ReleaseNotes(version='v0.5.0', preamble='Big release!')
        md = render_release_notes(notes)
        if 'Big release!' not in md:
            raise AssertionError(f'Missing preamble:\n{md}')

    def test_empty_summaries(self) -> None:
        """Empty summaries produce a default preamble."""
        notes = ReleaseNotes(version='v0.5.0')
        md = render_release_notes(notes)
        if '0 package(s) updated.' not in md:
            raise AssertionError(f'Missing default preamble:\n{md}')

    def test_multiple_packages(self) -> None:
        """Multiple packages each get their own heading."""
        notes = ReleaseNotes(
            version='v0.5.0',
            summaries=[
                PackageSummary(
                    name='genkit',
                    old_version='0.4.0',
                    new_version='0.5.0',
                    changelog=Changelog(version='0.5.0'),
                ),
                PackageSummary(
                    name='genkit-plugin-google-genai',
                    old_version='0.4.0',
                    new_version='0.5.0',
                    changelog=Changelog(version='0.5.0'),
                ),
            ],
        )
        md = render_release_notes(notes)
        if '2 package(s) updated.' not in md:
            raise AssertionError(f'Missing default preamble:\n{md}')
        if '### genkit' not in md:
            raise AssertionError(f'Missing genkit heading:\n{md}')
        if '### genkit-plugin-google-genai' not in md:
            raise AssertionError(f'Missing plugin heading:\n{md}')


class TestGenerateReleaseNotes:
    """Tests for generate_release_notes function."""

    @pytest.mark.asyncio
    async def test_generates_per_package(self) -> None:
        """Generate one summary per bumped package."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(
                    name='genkit',
                    old_version='0.4.0',
                    new_version='0.5.0',
                    bump='minor',
                ),
            ],
        )
        vcs = FakeVCS(
            log_lines=['aaa1111 feat: add streaming'],
            tags={'genkit-v0.4.0'},
        )
        notes = await generate_release_notes(
            manifest=manifest,
            vcs=vcs,
            tag_format='{name}-v{version}',
        )
        if len(notes.summaries) != 1:
            raise AssertionError(f'Expected 1 summary, got {len(notes.summaries)}')
        if notes.summaries[0].name != 'genkit':
            raise AssertionError(f'Expected genkit, got {notes.summaries[0].name}')

    @pytest.mark.asyncio
    async def test_skips_unchanged_packages(self) -> None:
        """Skipped packages are excluded from release notes."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(
                    name='genkit',
                    old_version='0.5.0',
                    new_version='0.5.0',
                    bump='none',
                    skipped=True,
                ),
            ],
        )
        vcs = FakeVCS()
        notes = await generate_release_notes(manifest=manifest, vcs=vcs)
        if len(notes.summaries) != 0:
            raise AssertionError(f'Expected 0 summaries for skipped package, got {len(notes.summaries)}')

    @pytest.mark.asyncio
    async def test_no_previous_tag(self) -> None:
        """When previous tag doesn't exist, includes all history."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.1.0',
            packages=[
                PackageVersion(
                    name='genkit',
                    old_version='0.0.0',
                    new_version='0.1.0',
                    bump='minor',
                ),
            ],
        )
        vcs = FakeVCS(
            log_lines=['aaa1111 feat: initial release'],
            tags=set(),
        )
        notes = await generate_release_notes(manifest=manifest, vcs=vcs)
        if len(notes.summaries) != 1:
            raise AssertionError(f'Expected 1 summary, got {len(notes.summaries)}')

    @pytest.mark.asyncio
    async def test_round_trip(self) -> None:
        """Generate + render produces valid markdown."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS(
            log_lines=['aaa1111 feat: add streaming (#42)'],
            tags={'genkit-v0.4.0'},
        )
        notes = await generate_release_notes(manifest=manifest, vcs=vcs, date='2026-02-10')
        md = render_release_notes(notes)
        if '### genkit (0.4.0 → 0.5.0)' not in md:
            raise AssertionError(f'Missing package heading:\n{md}')
