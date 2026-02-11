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

"""Tests for releasekit.tags — git tag creation and GitHub Release management."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.tags import TagResult, create_tags, delete_tags, format_tag
from releasekit.versions import PackageVersion, ReleaseManifest


# -- Test doubles ----------------------------------------------------------


class FakeVCS:
    """Minimal VCS double for tag tests.

    Records all tag/push/delete operations for assertions.
    """

    def __init__(
        self,
        *,
        existing_tags: set[str] | None = None,
        tag_error: str | None = None,
        push_error: str | None = None,
    ) -> None:
        """Initialize with optional existing tags and error injection.

        Args:
            existing_tags: Tags that already exist (tag_exists returns True).
            tag_error: If set, vcs.tag() raises RuntimeError with this message.
            push_error: If set, vcs.push() raises RuntimeError with this message.
        """
        self.existing_tags: set[str] = existing_tags or set()
        self.tag_error = tag_error
        self.push_error = push_error
        self.created_tags: list[tuple[str, str]] = []  # (tag_name, message)
        self.deleted_tags: list[tuple[str, bool]] = []  # (tag_name, remote)
        self.push_calls: list[dict[str, object]] = []

    def tag_exists(self, tag_name: str) -> bool:
        """Check if a tag exists."""
        return tag_name in self.existing_tags

    def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> None:
        """Create a tag (records for assertion)."""
        if self.tag_error:
            raise RuntimeError(self.tag_error)
        self.created_tags.append((tag_name, message or ''))
        # Track as existing after creation.
        self.existing_tags.add(tag_name)

    def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> None:
        """Delete a tag (records for assertion)."""
        self.deleted_tags.append((tag_name, remote))
        self.existing_tags.discard(tag_name)

    def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        dry_run: bool = False,
    ) -> None:
        """Push tags (records for assertion)."""
        if self.push_error:
            raise RuntimeError(self.push_error)
        self.push_calls.append({'tags': tags, 'remote': remote})

    def is_clean(self, *, dry_run: bool = False) -> bool:
        """Stub — always clean."""
        return True

    def is_shallow(self) -> bool:
        """Stub — not shallow."""
        return False

    def current_sha(self) -> str:
        """Stub SHA."""
        return 'abc123'

    def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        """Stub log."""
        return []

    def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Stub diff."""
        return []

    def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> None:
        """Stub commit."""


class FakeForge:
    """Minimal Forge double for release tests.

    Records all release creation/deletion operations.
    """

    def __init__(
        self,
        *,
        available: bool = True,
        create_error: str | None = None,
        delete_error: str | None = None,
    ) -> None:
        """Initialize with availability and error injection.

        Args:
            available: Whether is_available() returns True.
            create_error: If set, create_release() raises with this message.
            delete_error: If set, delete_release() raises with this message.
        """
        self._available = available
        self._create_error = create_error
        self._delete_error = delete_error
        self.releases_created: list[dict[str, object]] = []
        self.releases_deleted: list[str] = []

    def is_available(self) -> bool:
        """Check if the forge CLI is available."""
        return self._available

    def create_release(
        self,
        tag: str,
        *,
        title: str | None = None,
        body: str = '',
        draft: bool = False,
        prerelease: bool = False,
        assets: list[Path] | None = None,
        dry_run: bool = False,
    ) -> None:
        """Create a release (records for assertion)."""
        if self._create_error:
            raise RuntimeError(self._create_error)
        self.releases_created.append({
            'tag': tag,
            'title': title,
            'body': body,
            'draft': draft,
            'prerelease': prerelease,
            'assets': assets or [],
        })

    def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> None:
        """Delete a release (records for assertion)."""
        if self._delete_error:
            raise RuntimeError(self._delete_error)
        self.releases_deleted.append(tag)


# -- Fixtures & helpers ----------------------------------------------------


def _make_manifest(
    *names: str,
    version: str = '0.5.0',
    old_version: str = '0.4.0',
) -> ReleaseManifest:
    """Create a test manifest with the given package names."""
    packages = [
        PackageVersion(
            name=name,
            old_version=old_version,
            new_version=version,
            bump='minor',
            reason='feat: something',
            tag=f'{name}-v{version}',
        )
        for name in names
    ]
    return ReleaseManifest(
        git_sha='abc123',
        umbrella_tag=f'v{version}',
        packages=packages,
    )


# -- Tests: format_tag ----------------------------------------------------


class TestFormatTag:
    """Tests for format_tag helper."""

    def test_per_package_format(self) -> None:
        """Standard per-package tag format."""
        result = format_tag('{name}-v{version}', name='genkit', version='0.5.0')
        if result != 'genkit-v0.5.0':
            raise AssertionError(f'Expected genkit-v0.5.0, got {result}')

    def test_umbrella_format(self) -> None:
        """Umbrella tag format (no name)."""
        result = format_tag('v{version}', version='0.5.0')
        if result != 'v0.5.0':
            raise AssertionError(f'Expected v0.5.0, got {result}')

    def test_custom_format(self) -> None:
        """Custom tag format with prefix."""
        result = format_tag('py/{name}@{version}', name='genkit', version='1.0.0')
        if result != 'py/genkit@1.0.0':
            raise AssertionError(f'Expected py/genkit@1.0.0, got {result}')


# -- Tests: TagResult -----------------------------------------------------


class TestTagResult:
    """Tests for TagResult dataclass."""

    def test_ok_when_no_failures(self) -> None:
        """Result is ok when no tags failed."""
        result = TagResult(created=['v0.5.0'])
        if not result.ok:
            raise AssertionError('Expected ok=True')

    def test_not_ok_when_failed(self) -> None:
        """Result is not ok when a tag failed."""
        result = TagResult(failed={'v0.5.0': 'error'})
        if result.ok:
            raise AssertionError('Expected ok=False')


# -- Tests: create_tags ----------------------------------------------------


class TestCreateTags:
    """Tests for create_tags function."""

    def test_creates_per_package_and_umbrella_tags(self) -> None:
        """Creates one tag per bumped package plus umbrella."""
        manifest = _make_manifest('genkit', 'genkit-plugin-foo')
        vcs = FakeVCS()

        result = create_tags(manifest=manifest, vcs=vcs)

        if not result.ok:
            raise AssertionError(f'Expected ok, got failures: {result.failed}')
        expected_tags = ['genkit-v0.5.0', 'genkit-plugin-foo-v0.5.0', 'v0.5.0']
        if result.created != expected_tags:
            raise AssertionError(f'Expected {expected_tags}, got {result.created}')
        if not result.pushed:
            raise AssertionError('Expected tags to be pushed')

    def test_skips_existing_tags(self) -> None:
        """Existing tags are skipped, not overwritten."""
        manifest = _make_manifest('genkit', 'genkit-plugin-foo')
        vcs = FakeVCS(existing_tags={'genkit-v0.5.0'})

        result = create_tags(manifest=manifest, vcs=vcs)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        if 'genkit-v0.5.0' not in result.skipped:
            raise AssertionError(f'Expected genkit-v0.5.0 in skipped: {result.skipped}')
        if 'genkit-plugin-foo-v0.5.0' not in result.created:
            raise AssertionError(f'Expected genkit-plugin-foo-v0.5.0 created: {result.created}')

    def test_skips_existing_umbrella_tag(self) -> None:
        """Existing umbrella tag is skipped."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(existing_tags={'v0.5.0'})

        result = create_tags(manifest=manifest, vcs=vcs)

        if 'v0.5.0' not in result.skipped:
            raise AssertionError(f'Expected v0.5.0 in skipped: {result.skipped}')
        if 'genkit-v0.5.0' not in result.created:
            raise AssertionError(f'Expected genkit-v0.5.0 created: {result.created}')

    def test_empty_manifest_no_tags(self) -> None:
        """Empty manifest (no bumped packages) creates no tags."""
        manifest = ReleaseManifest(git_sha='abc123', packages=[])
        vcs = FakeVCS()

        result = create_tags(manifest=manifest, vcs=vcs)

        if result.created:
            raise AssertionError(f'Expected no tags, got {result.created}')

    def test_skipped_packages_not_tagged(self) -> None:
        """Skipped packages (unchanged) are not tagged."""
        packages = [
            PackageVersion(
                name='genkit',
                old_version='0.5.0',
                new_version='0.5.0',
                bump='none',
                skipped=True,
            ),
            PackageVersion(
                name='genkit-plugin-foo',
                old_version='0.4.0',
                new_version='0.5.0',
                bump='minor',
                reason='feat: new feature',
            ),
        ]
        manifest = ReleaseManifest(git_sha='abc123', packages=packages)
        vcs = FakeVCS()

        result = create_tags(manifest=manifest, vcs=vcs)

        tag_names = [t[0] for t in vcs.created_tags]
        if 'genkit-v0.5.0' in tag_names:
            raise AssertionError('Skipped package should not be tagged')
        if 'genkit-plugin-foo-v0.5.0' not in tag_names:
            raise AssertionError('Bumped package should be tagged')

    def test_tag_error_recorded(self) -> None:
        """Tag creation failure is recorded but doesn't crash."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(tag_error='Permission denied')

        result = create_tags(manifest=manifest, vcs=vcs)

        if result.ok:
            raise AssertionError('Expected failure')
        if 'genkit-v0.5.0' not in result.failed:
            raise AssertionError(f'Expected genkit-v0.5.0 in failed: {result.failed}')

    def test_push_error_non_fatal(self) -> None:
        """Push failure is non-fatal — tags exist locally."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(push_error='Network error')

        result = create_tags(manifest=manifest, vcs=vcs)

        # Tags should still be created successfully.
        if 'genkit-v0.5.0' not in result.created:
            raise AssertionError(f'Expected genkit-v0.5.0 created: {result.created}')
        if result.pushed:
            raise AssertionError('Expected pushed=False after push error')

    def test_no_push_when_failures_exist(self) -> None:
        """Tags are not pushed when there are creation failures."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(tag_error='Failed')

        result = create_tags(manifest=manifest, vcs=vcs)

        if vcs.push_calls:
            raise AssertionError('Should not push when tag creation failed')

    def test_custom_tag_format(self) -> None:
        """Custom tag format is respected."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()

        result = create_tags(
            manifest=manifest,
            vcs=vcs,
            tag_format='py/{name}@{version}',
            umbrella_tag_format='py@{version}',
        )

        if 'py/genkit@0.5.0' not in result.created:
            raise AssertionError(f'Expected py/genkit@0.5.0 created: {result.created}')
        if 'py@0.5.0' not in result.created:
            raise AssertionError(f'Expected py@0.5.0 created: {result.created}')


# -- Tests: create_tags + forge --------------------------------------------


class TestCreateTagsWithForge:
    """Tests for create_tags with GitHub Release integration."""

    def test_creates_published_release_local_mode(self) -> None:
        """Local mode creates a published (not draft) release."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()
        forge = FakeForge()

        result = create_tags(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            release_body='## Changes\n- feat: streaming',
            publish_from='local',
        )

        if not forge.releases_created:
            raise AssertionError('Expected a release to be created')
        release = forge.releases_created[0]
        if release['draft']:
            raise AssertionError('Local mode should create published release')
        if release['tag'] != 'v0.5.0':
            raise AssertionError(f'Expected tag v0.5.0, got {release["tag"]}')
        if result.release_url == '':
            raise AssertionError('Expected release_url to be set')

    def test_creates_draft_release_ci_mode(self) -> None:
        """CI mode creates a draft release."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()
        forge = FakeForge()

        result = create_tags(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            publish_from='ci',
        )

        if not forge.releases_created:
            raise AssertionError('Expected a release to be created')
        release = forge.releases_created[0]
        if not release['draft']:
            raise AssertionError('CI mode should create draft release')

    def test_ci_mode_attaches_manifest_asset(self, tmp_path: Path) -> None:
        """CI mode attaches the manifest JSON as a release asset."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()
        forge = FakeForge()
        manifest_file = tmp_path / 'manifest.json'
        manifest_file.write_text('{}', encoding='utf-8')

        create_tags(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            publish_from='ci',
            manifest_path=manifest_file,
        )

        release = forge.releases_created[0]
        assets = release['assets']
        if not isinstance(assets, list) or len(assets) != 1:
            raise AssertionError(f'Expected 1 asset, got {assets}')
        if assets[0] != manifest_file:
            raise AssertionError(f'Expected {manifest_file}, got {assets[0]}')

    def test_forge_unavailable_skips_release(self) -> None:
        """Unavailable forge silently skips release creation."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()
        forge = FakeForge(available=False)

        result = create_tags(manifest=manifest, vcs=vcs, forge=forge)

        if forge.releases_created:
            raise AssertionError('Should not create release when forge unavailable')
        # Tags should still be created.
        if not result.ok:
            raise AssertionError('Tags should succeed even without forge')

    def test_no_forge_skips_release(self) -> None:
        """No forge backend silently skips release creation."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()

        result = create_tags(manifest=manifest, vcs=vcs, forge=None)

        if not result.ok:
            raise AssertionError('Tags should succeed without forge')

    def test_release_error_non_fatal(self) -> None:
        """Release creation failure is non-fatal."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()
        forge = FakeForge(create_error='API rate limit')

        result = create_tags(manifest=manifest, vcs=vcs, forge=forge)

        # Tags should still be created and pushed.
        if not result.ok:
            raise AssertionError('Tag operations should be ok despite release failure')
        if not result.pushed:
            raise AssertionError('Tags should still be pushed')

    def test_prerelease_flag(self) -> None:
        """Prerelease flag is passed through to the forge."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS()
        forge = FakeForge()

        create_tags(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            prerelease=True,
        )

        release = forge.releases_created[0]
        if not release['prerelease']:
            raise AssertionError('Expected prerelease=True')


# -- Tests: delete_tags ----------------------------------------------------


class TestDeleteTags:
    """Tests for delete_tags (rollback) function."""

    def test_deletes_existing_tags(self) -> None:
        """Deletes per-package and umbrella tags that exist."""
        manifest = _make_manifest('genkit', 'genkit-plugin-foo')
        vcs = FakeVCS(existing_tags={
            'genkit-v0.5.0',
            'genkit-plugin-foo-v0.5.0',
            'v0.5.0',
        })

        result = delete_tags(manifest=manifest, vcs=vcs)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        expected = ['genkit-v0.5.0', 'genkit-plugin-foo-v0.5.0', 'v0.5.0']
        if result.created != expected:
            raise AssertionError(f'Expected {expected} deleted, got {result.created}')

    def test_skips_nonexistent_tags(self) -> None:
        """Tags that don't exist are skipped silently."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(existing_tags=set())

        result = delete_tags(manifest=manifest, vcs=vcs)

        if result.created:
            raise AssertionError(f'Should not delete non-existent tags: {result.created}')
        if 'genkit-v0.5.0' not in result.skipped:
            raise AssertionError(f'Expected genkit-v0.5.0 in skipped: {result.skipped}')

    def test_deletes_github_release(self) -> None:
        """Deletes the GitHub Release when forge is available."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(existing_tags={'genkit-v0.5.0', 'v0.5.0'})
        forge = FakeForge()

        delete_tags(manifest=manifest, vcs=vcs, forge=forge)

        if 'v0.5.0' not in forge.releases_deleted:
            raise AssertionError(f'Expected v0.5.0 deleted: {forge.releases_deleted}')

    def test_delete_release_error_non_fatal(self) -> None:
        """Release deletion failure is non-fatal."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(existing_tags={'genkit-v0.5.0', 'v0.5.0'})
        forge = FakeForge(delete_error='Not found')

        result = delete_tags(manifest=manifest, vcs=vcs, forge=forge)

        # Tag deletion should still succeed.
        if not result.ok:
            raise AssertionError('Tag deletion should succeed despite release error')

    def test_remote_delete(self) -> None:
        """Tags are deleted from remote when remote=True."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(existing_tags={'genkit-v0.5.0', 'v0.5.0'})

        delete_tags(manifest=manifest, vcs=vcs, remote=True)

        for tag_name, remote in vcs.deleted_tags:
            if not remote:
                raise AssertionError(f'Expected remote=True for {tag_name}')

    def test_local_only_delete(self) -> None:
        """Tags are deleted locally only when remote=False."""
        manifest = _make_manifest('genkit')
        vcs = FakeVCS(existing_tags={'genkit-v0.5.0', 'v0.5.0'})

        delete_tags(manifest=manifest, vcs=vcs, remote=False)

        for tag_name, remote in vcs.deleted_tags:
            if remote:
                raise AssertionError(f'Expected remote=False for {tag_name}')
