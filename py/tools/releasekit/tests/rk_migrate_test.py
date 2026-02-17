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

"""Tests for releasekit.migrate — automatic tag detection and bootstrap.

Covers:
- Tag classification against workspace tag formats
- Umbrella tag classification
- Secondary tag format classification
- Unclassified tag handling
- Semver sorting and latest-per-workspace selection
- Commit SHA resolution
- TOML writing (bootstrap_sha)
- Full migrate() orchestration (dry-run and live)
- Edge cases: no tags, no workspaces, no matches, single workspace filter
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import tomlkit
from releasekit.config import ReleaseConfig, WorkspaceConfig
from releasekit.migrate import (
    MIGRATION_SOURCES,
    ClassifiedTag,
    MigrationSource,
    ReleasePleaseSource,
    classify_tags,
    migrate_from_source,
    pick_latest,
    resolve_commit_shas,
    write_bootstrap_sha,
)
from tests._fakes import FakeVCS

# Fixtures


def _ws(
    label: str = 'py',
    tag_format: str = '{name}@{version}',
    umbrella_tag: str = 'py/v{version}',
    secondary_tag_format: str = '',
) -> WorkspaceConfig:
    """Create a WorkspaceConfig with the given tag formats."""
    return WorkspaceConfig(
        label=label,
        ecosystem='python',
        tool='uv',
        root='py',
        tag_format=tag_format,
        umbrella_tag=umbrella_tag,
        secondary_tag_format=secondary_tag_format,
    )


def _config(
    workspaces: dict[str, WorkspaceConfig] | None = None,
    config_path: Path | None = None,
) -> ReleaseConfig:
    """Create a ReleaseConfig with the given workspaces."""
    return ReleaseConfig(
        workspaces=workspaces or {},
        config_path=config_path,
    )


# classify_tags


class TestClassifyTags:
    """Tests for classify_tags()."""

    def test_per_package_tag_matches(self) -> None:
        """Per-package tags are classified correctly."""
        ws = {'py': _ws(tag_format='{name}@{version}')}
        classified, unclassified = classify_tags(['genkit@0.5.0'], ws)

        assert len(classified) == 1
        assert classified[0].tag == 'genkit@0.5.0'
        assert classified[0].workspace_label == 'py'
        assert classified[0].package_name == 'genkit'
        assert classified[0].version == '0.5.0'
        assert classified[0].is_umbrella is False
        assert unclassified == []

    def test_umbrella_tag_matches(self) -> None:
        """Umbrella tags are classified correctly."""
        ws = {'py': _ws(umbrella_tag='py/v{version}')}
        classified, _unclassified = classify_tags(['py/v0.5.0'], ws)

        assert len(classified) == 1
        assert classified[0].tag == 'py/v0.5.0'
        assert classified[0].workspace_label == 'py'
        assert classified[0].package_name == ''
        assert classified[0].version == '0.5.0'
        assert classified[0].is_umbrella is True

    def test_secondary_tag_format_matches(self) -> None:
        """Secondary tag format is tried when primary doesn't match."""
        ws = {
            'py': _ws(
                tag_format='{name}@{version}',
                secondary_tag_format='{name}-v{version}',
            )
        }
        classified, _unclassified = classify_tags(['genkit-v0.4.0'], ws)

        assert len(classified) == 1
        assert classified[0].tag == 'genkit-v0.4.0'
        assert classified[0].package_name == 'genkit'
        assert classified[0].version == '0.4.0'

    def test_unclassified_tags(self) -> None:
        """Tags that don't match any format are unclassified."""
        ws = {'py': _ws(tag_format='{name}@{version}')}
        classified, unclassified = classify_tags(['random-tag', 'v1.0'], ws)

        assert classified == []
        assert sorted(unclassified) == ['random-tag', 'v1.0']

    def test_mixed_classified_and_unclassified(self) -> None:
        """Mix of matching and non-matching tags."""
        ws = {'py': _ws(tag_format='{name}@{version}')}
        tags = ['genkit@0.5.0', 'random-tag', 'genkit@0.4.0']
        classified, unclassified = classify_tags(tags, ws)

        assert len(classified) == 2
        assert unclassified == ['random-tag']

    def test_multiple_workspaces(self) -> None:
        """Tags are matched against the correct workspace."""
        ws = {
            'py': _ws(label='py', tag_format='{name}@{version}', umbrella_tag='py/v{version}'),
            'js': _ws(label='js', tag_format='@genkit-ai/{name}@{version}', umbrella_tag='js/v{version}'),
        }
        tags = ['genkit@0.5.0', 'py/v0.5.0', 'js/v1.0.0']
        classified, _unclassified = classify_tags(tags, ws)

        assert len(classified) == 3
        labels = {ct.tag: ct.workspace_label for ct in classified}
        assert labels['genkit@0.5.0'] == 'py'
        assert labels['py/v0.5.0'] == 'py'
        assert labels['js/v1.0.0'] == 'js'

    def test_empty_tags(self) -> None:
        """Empty tag list returns empty results."""
        ws = {'py': _ws()}
        classified, unclassified = classify_tags([], ws)
        assert classified == []
        assert unclassified == []

    def test_empty_workspaces(self) -> None:
        """No workspaces means all tags are unclassified."""
        classified, unclassified = classify_tags(['genkit@0.5.0'], {})
        assert classified == []
        assert unclassified == ['genkit@0.5.0']

    def test_prerelease_tag(self) -> None:
        """Pre-release version tags are classified correctly."""
        ws = {'py': _ws(tag_format='{name}@{version}')}
        classified, _ = classify_tags(['genkit@1.0.0-rc.1'], ws)

        assert len(classified) == 1
        assert classified[0].version == '1.0.0-rc.1'


# pick_latest


class TestPickLatest:
    """Tests for pick_latest()."""

    def test_picks_highest_version(self) -> None:
        """Picks the tag with the highest semver."""
        classified = [
            ClassifiedTag(tag='genkit@0.3.0', workspace_label='py', version='0.3.0'),
            ClassifiedTag(tag='genkit@0.5.0', workspace_label='py', version='0.5.0'),
            ClassifiedTag(tag='genkit@0.4.0', workspace_label='py', version='0.4.0'),
        ]
        latest = pick_latest(classified)
        assert latest['py'].version == '0.5.0'

    def test_release_beats_prerelease(self) -> None:
        """A release version beats a pre-release at the same version."""
        classified = [
            ClassifiedTag(tag='a@1.0.0-rc.1', workspace_label='py', version='1.0.0-rc.1'),
            ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0'),
        ]
        latest = pick_latest(classified)
        assert latest['py'].version == '1.0.0'

    def test_multiple_workspaces(self) -> None:
        """Each workspace gets its own latest."""
        classified = [
            ClassifiedTag(tag='a@0.5.0', workspace_label='py', version='0.5.0'),
            ClassifiedTag(tag='a@0.6.0', workspace_label='py', version='0.6.0'),
            ClassifiedTag(tag='b@1.0.0', workspace_label='js', version='1.0.0'),
            ClassifiedTag(tag='b@0.9.0', workspace_label='js', version='0.9.0'),
        ]
        latest = pick_latest(classified)
        assert latest['py'].version == '0.6.0'
        assert latest['js'].version == '1.0.0'

    def test_empty_list(self) -> None:
        """Empty input returns empty dict."""
        assert pick_latest([]) == {}

    def test_single_tag(self) -> None:
        """Single tag is the latest."""
        classified = [ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0')]
        latest = pick_latest(classified)
        assert latest['py'].version == '1.0.0'


# resolve_commit_shas


class TestResolveCommitShas:
    """Tests for resolve_commit_shas()."""

    def test_resolves_shas(self) -> None:
        """Commit SHAs are resolved from VCS."""
        vcs = FakeVCS(tag_shas={'a@1.0.0': 'abc123def456', 'b@2.0.0': 'fed654cba321'})
        classified = [
            ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0'),
            ClassifiedTag(tag='b@2.0.0', workspace_label='py', version='2.0.0'),
        ]
        asyncio.run(resolve_commit_shas(classified, vcs))

        assert classified[0].commit_sha == 'abc123def456'
        assert classified[1].commit_sha == 'fed654cba321'

    def test_missing_sha_returns_empty(self) -> None:
        """Tags not found in VCS get empty SHA."""
        vcs = FakeVCS(tag_shas={})
        classified = [ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0')]
        asyncio.run(resolve_commit_shas(classified, vcs))

        assert classified[0].commit_sha == ''

    def test_skips_already_resolved(self) -> None:
        """Tags with existing SHA are not re-resolved."""
        vcs = FakeVCS(tag_shas={'a@1.0.0': 'should_not_be_used'})
        classified = [
            ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0', commit_sha='already_set'),
        ]
        asyncio.run(resolve_commit_shas(classified, vcs))

        assert classified[0].commit_sha == 'already_set'


# write_bootstrap_sha


class TestWriteBootstrapSha:
    """Tests for write_bootstrap_sha()."""

    def test_writes_to_existing_workspace(self, tmp_path: Path) -> None:
        """Writes bootstrap_sha into an existing workspace section."""
        config_path = tmp_path / 'releasekit.toml'
        config_path.write_text(
            '[workspace.py]\necosystem = "python"\n',
            encoding='utf-8',
        )

        write_bootstrap_sha(config_path, 'py', 'abc123')

        doc = tomlkit.parse(config_path.read_text(encoding='utf-8')).unwrap()
        assert doc['workspace']['py']['bootstrap_sha'] == 'abc123'
        # Existing keys preserved.
        assert doc['workspace']['py']['ecosystem'] == 'python'

    def test_creates_workspace_section_if_missing(self, tmp_path: Path) -> None:
        """Creates the workspace section if it doesn't exist."""
        config_path = tmp_path / 'releasekit.toml'
        config_path.write_text('forge = "github"\n', encoding='utf-8')

        write_bootstrap_sha(config_path, 'py', 'abc123')

        doc = tomlkit.parse(config_path.read_text(encoding='utf-8')).unwrap()
        assert doc['workspace']['py']['bootstrap_sha'] == 'abc123'
        assert doc['forge'] == 'github'

    def test_overwrites_existing_bootstrap_sha(self, tmp_path: Path) -> None:
        """Overwrites an existing bootstrap_sha value."""
        config_path = tmp_path / 'releasekit.toml'
        config_path.write_text(
            '[workspace.py]\nbootstrap_sha = "old"\n',
            encoding='utf-8',
        )

        write_bootstrap_sha(config_path, 'py', 'new_sha')

        doc = tomlkit.parse(config_path.read_text(encoding='utf-8')).unwrap()
        assert doc['workspace']['py']['bootstrap_sha'] == 'new_sha'


# _semver_sort_key edge cases


class TestSemverSortKey:
    """Tests for _semver_sort_key via pick_latest."""

    def test_major_version_ordering(self) -> None:
        """Major version differences are ordered correctly."""
        classified = [
            ClassifiedTag(tag='a@2.0.0', workspace_label='py', version='2.0.0'),
            ClassifiedTag(tag='a@10.0.0', workspace_label='py', version='10.0.0'),
            ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0'),
        ]
        assert pick_latest(classified)['py'].version == '10.0.0'

    def test_minor_version_ordering(self) -> None:
        """Minor version differences are ordered correctly."""
        classified = [
            ClassifiedTag(tag='a@1.2.0', workspace_label='py', version='1.2.0'),
            ClassifiedTag(tag='a@1.10.0', workspace_label='py', version='1.10.0'),
            ClassifiedTag(tag='a@1.1.0', workspace_label='py', version='1.1.0'),
        ]
        assert pick_latest(classified)['py'].version == '1.10.0'

    def test_patch_version_ordering(self) -> None:
        """Patch version differences are ordered correctly."""
        classified = [
            ClassifiedTag(tag='a@1.0.2', workspace_label='py', version='1.0.2'),
            ClassifiedTag(tag='a@1.0.10', workspace_label='py', version='1.0.10'),
            ClassifiedTag(tag='a@1.0.1', workspace_label='py', version='1.0.1'),
        ]
        assert pick_latest(classified)['py'].version == '1.0.10'

    def test_prerelease_ordering(self) -> None:
        """Pre-release versions sort before their release."""
        classified = [
            ClassifiedTag(tag='a@1.0.0-alpha.1', workspace_label='py', version='1.0.0-alpha.1'),
            ClassifiedTag(tag='a@1.0.0-rc.1', workspace_label='py', version='1.0.0-rc.1'),
            ClassifiedTag(tag='a@1.0.0', workspace_label='py', version='1.0.0'),
        ]
        assert pick_latest(classified)['py'].version == '1.0.0'

    def test_invalid_version_sorts_lowest(self) -> None:
        """Non-semver versions sort below valid ones."""
        classified = [
            ClassifiedTag(tag='a@not-a-version', workspace_label='py', version='not-a-version'),
            ClassifiedTag(tag='a@0.0.1', workspace_label='py', version='0.0.1'),
        ]
        assert pick_latest(classified)['py'].version == '0.0.1'


# MigrationSource protocol + ReleasePleaseSource tests


class TestReleasePleaseSource:
    """Tests for ReleasePleaseSource."""

    def test_name(self) -> None:
        """Source name is 'release-please'."""
        src = ReleasePleaseSource()
        assert src.name == 'release-please'

    def test_detect_manifest_only(self, tmp_path: Path) -> None:
        """Detects when only manifest exists."""
        (tmp_path / '.release-please-manifest.json').write_text('{}')
        assert ReleasePleaseSource().detect(tmp_path) is True

    def test_detect_config_only(self, tmp_path: Path) -> None:
        """Detects when only config exists."""
        (tmp_path / 'release-please-config.json').write_text('{}')
        assert ReleasePleaseSource().detect(tmp_path) is True

    def test_detect_nothing(self, tmp_path: Path) -> None:
        """Returns False when no release-please files exist."""
        assert ReleasePleaseSource().detect(tmp_path) is False

    def test_convert_basic(self, tmp_path: Path) -> None:
        """Converts basic release-please config to releasekit.toml."""
        config = {
            'packages': {
                'packages/genkit': {},
                'plugins/google-genai': {},
                'plugins/vertex-ai': {},
            },
            'include-component-in-tag': True,
            'tag-separator': '-',
        }
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps(config),
        )
        (tmp_path / '.release-please-manifest.json').write_text(
            json.dumps({
                'packages/genkit': '0.5.0',
                'plugins/google-genai': '0.5.0',
                'plugins/vertex-ai': '0.5.0',
            }),
        )

        result = ReleasePleaseSource().convert(tmp_path)
        assert 'forge = "github"' in result
        assert 'tag_format' in result
        assert 'workspace' in result

        doc = tomlkit.parse(result).unwrap()
        ws = doc['workspace']['py']
        assert ws['tag_format'] == '{name}-v{version}'
        assert ws['ecosystem'] == 'python'

    def test_convert_no_component_in_tag(self, tmp_path: Path) -> None:
        """Tag format without component produces v{version}."""
        config = {
            'packages': {'.': {}},
            'include-component-in-tag': False,
        }
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps(config),
        )

        result = ReleasePleaseSource().convert(tmp_path)
        doc = tomlkit.parse(result).unwrap()
        assert doc['workspace']['py']['tag_format'] == 'v{version}'

    def test_convert_custom_separator(self, tmp_path: Path) -> None:
        """Custom tag separator is used in tag_format."""
        config = {
            'packages': {'pkg/foo': {}},
            'tag-separator': '/',
        }
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps(config),
        )

        result = ReleasePleaseSource().convert(tmp_path)
        doc = tomlkit.parse(result).unwrap()
        assert doc['workspace']['py']['tag_format'] == '{name}/v{version}'

    def test_convert_manifest_fallback(self, tmp_path: Path) -> None:
        """Uses manifest paths when config has no packages."""
        (tmp_path / 'release-please-config.json').write_text('{}')
        (tmp_path / '.release-please-manifest.json').write_text(
            json.dumps({
                'packages/core': '1.0.0',
                'packages/utils': '1.0.0',
                '.': '1.0.0',
            }),
        )

        result = ReleasePleaseSource().convert(tmp_path)
        doc = tomlkit.parse(result).unwrap()
        ws = doc['workspace']['py']
        assert 'groups' in ws
        assert 'core' in ws['groups']['packages']

    def test_convert_empty_config(self, tmp_path: Path) -> None:
        """Empty config files still produce valid TOML."""
        (tmp_path / 'release-please-config.json').write_text('{}')
        (tmp_path / '.release-please-manifest.json').write_text('{}')

        result = ReleasePleaseSource().convert(tmp_path)
        assert 'forge = "github"' in result
        doc = tomlkit.parse(result)
        assert 'workspace' in doc

    def test_convert_malformed_json(self, tmp_path: Path) -> None:
        """Malformed JSON is handled gracefully."""
        (tmp_path / 'release-please-config.json').write_text('not json')
        (tmp_path / '.release-please-manifest.json').write_text('{bad')

        result = ReleasePleaseSource().convert(tmp_path)
        assert 'forge = "github"' in result


class TestMigrateFromSource:
    """Tests for migrate_from_source()."""

    def test_source_not_detected(self, tmp_path: Path) -> None:
        """Returns empty report when source not found."""
        report = migrate_from_source(tmp_path, ReleasePleaseSource())
        assert report.detected is False
        assert report.written is False

    def test_writes_config(self, tmp_path: Path) -> None:
        """Writes releasekit.toml when source detected."""
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps({'packages': {'pkg/foo': {}}}),
        )

        report = migrate_from_source(tmp_path, ReleasePleaseSource())
        assert report.detected is True
        assert report.written is True
        assert (tmp_path / 'releasekit.toml').exists()

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run does not write files."""
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps({'packages': {'pkg/foo': {}}}),
        )

        report = migrate_from_source(
            tmp_path,
            ReleasePleaseSource(),
            dry_run=True,
        )
        assert report.detected is True
        assert report.written is False
        assert not (tmp_path / 'releasekit.toml').exists()
        assert report.toml_content  # content is computed

    def test_no_overwrite_without_force(self, tmp_path: Path) -> None:
        """Existing releasekit.toml is not overwritten without --force."""
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps({'packages': {'pkg/foo': {}}}),
        )
        (tmp_path / 'releasekit.toml').write_text('existing = true\n')

        report = migrate_from_source(tmp_path, ReleasePleaseSource())
        assert report.detected is True
        assert report.written is False
        assert (tmp_path / 'releasekit.toml').read_text() == 'existing = true\n'

    def test_force_overwrites(self, tmp_path: Path) -> None:
        """--force overwrites existing releasekit.toml."""
        (tmp_path / 'release-please-config.json').write_text(
            json.dumps({'packages': {'pkg/foo': {}}}),
        )
        (tmp_path / 'releasekit.toml').write_text('existing = true\n')

        report = migrate_from_source(
            tmp_path,
            ReleasePleaseSource(),
            force=True,
        )
        assert report.written is True
        content = (tmp_path / 'releasekit.toml').read_text()
        assert 'existing' not in content
        assert 'forge' in content


class TestMigrationSources:
    """Tests for MIGRATION_SOURCES registry."""

    def test_release_please_registered(self) -> None:
        """Release-please source is in the registry."""
        assert 'release-please' in MIGRATION_SOURCES

    def test_protocol_conformance(self) -> None:
        """ReleasePleaseSource conforms to MigrationSource protocol."""
        assert isinstance(ReleasePleaseSource(), MigrationSource)
