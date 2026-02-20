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

"""Tests for releasekit.versions (ReleaseManifest + PackageVersion)."""

from __future__ import annotations

import json
from pathlib import Path

from releasekit.versions import PackageVersion, ReleaseManifest


class TestPackageVersion:
    """Tests for the PackageVersion dataclass."""

    def test_defaults(self) -> None:
        """Default fields are set correctly."""
        pv = PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0')
        assert pv.bump == 'none'
        assert pv.reason == ''
        assert pv.skipped is False
        assert pv.tag == ''

    def test_all_fields(self) -> None:
        """All fields are set when provided."""
        pv = PackageVersion(
            name='genkit',
            old_version='0.4.0',
            new_version='0.5.0',
            bump='minor',
            reason='feat: add streaming',
            skipped=False,
            tag='genkit-v0.5.0',
        )
        assert pv.name == 'genkit'
        assert pv.old_version == '0.4.0'
        assert pv.new_version == '0.5.0'
        assert pv.bump == 'minor'
        assert pv.reason == 'feat: add streaming'
        assert pv.tag == 'genkit-v0.5.0'

    def test_frozen(self) -> None:
        """PackageVersion is immutable."""
        pv = PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0')
        try:
            pv.name = 'other'  # type: ignore[misc]
            raise AssertionError('Expected FrozenInstanceError')
        except AttributeError:
            pass


class TestReleaseManifest:
    """Tests for the ReleaseManifest dataclass."""

    def test_empty_manifest(self) -> None:
        """Empty manifest has sensible defaults."""
        m = ReleaseManifest(git_sha='abc123')
        assert m.git_sha == 'abc123'
        assert m.umbrella_tag == ''
        assert m.packages == []
        assert m.created_at == ''

    def test_bumped_and_skipped(self) -> None:
        """The bumped and skipped properties filter correctly."""
        m = ReleaseManifest(
            git_sha='abc',
            packages=[
                PackageVersion(name='a', old_version='1.0.0', new_version='1.1.0', bump='minor'),
                PackageVersion(name='b', old_version='1.0.0', new_version='1.0.0', skipped=True),
                PackageVersion(name='c', old_version='2.0.0', new_version='3.0.0', bump='major'),
            ],
        )
        assert len(m.bumped) == 2
        assert len(m.skipped) == 1
        assert m.bumped[0].name == 'a'
        assert m.bumped[1].name == 'c'
        assert m.skipped[0].name == 'b'

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Round-trip save → load preserves all data."""
        original = ReleaseManifest(
            git_sha='deadbeef',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(
                    name='genkit',
                    old_version='0.4.0',
                    new_version='0.5.0',
                    bump='minor',
                    reason='feat: streaming',
                    tag='genkit-v0.5.0',
                ),
                PackageVersion(
                    name='genkit-plugin-foo',
                    old_version='0.4.0',
                    new_version='0.4.0',
                    skipped=True,
                    reason='unchanged',
                ),
            ],
            created_at='2026-02-10T00:00:00Z',
        )

        path = tmp_path / 'manifest.json'
        original.save(path)

        # File exists and is valid JSON.
        assert path.exists()
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['git_sha'] == 'deadbeef'
        assert len(data['packages']) == 2

        # Round-trip load.
        loaded = ReleaseManifest.load(path)
        assert loaded.git_sha == original.git_sha
        assert loaded.umbrella_tag == original.umbrella_tag
        assert loaded.created_at == original.created_at
        assert len(loaded.packages) == 2
        assert loaded.packages[0].name == 'genkit'
        assert loaded.packages[0].new_version == '0.5.0'
        assert loaded.packages[1].skipped is True

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Loading a non-existent file raises OSError."""
        try:
            ReleaseManifest.load(tmp_path / 'nonexistent.json')
            raise AssertionError('Expected OSError')
        except OSError:
            pass

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Loading invalid JSON raises ValueError."""
        path = tmp_path / 'bad.json'
        path.write_text('not json', encoding='utf-8')
        try:
            ReleaseManifest.load(path)
            raise AssertionError('Expected ValueError')
        except ValueError:
            pass

    def test_save_to_readonly_dir(self, tmp_path: Path) -> None:
        """Saving to a read-only location raises OSError."""
        path = tmp_path / 'readonly' / 'manifest.json'
        # Directory doesn't exist and we don't create it.
        try:
            ReleaseManifest(git_sha='abc').save(path)
            raise AssertionError('Expected OSError')
        except OSError:
            pass

    def test_load_missing_git_sha(self, tmp_path: Path) -> None:
        """Loading a manifest without git_sha raises ValueError."""
        path = tmp_path / 'no_sha.json'
        path.write_text('{"packages": []}', encoding='utf-8')
        try:
            ReleaseManifest.load(path)
            raise AssertionError('Expected ValueError')
        except ValueError as exc:
            assert 'git_sha' in str(exc)
