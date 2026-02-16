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

"""Release tagging: tag merge commit and create platform Release.

Orchestrates the "tag" step of the releasekit model. When a Release
PR is merged, this module:

1. Finds the merged PR by label (``autorelease: pending``).
2. Extracts the embedded manifest from the PR body.
3. Creates per-package tags and an umbrella tag on the merge commit.
4. Creates a platform Release (GitHub Release, GitLab Release, or
   Bitbucket annotated tag — see compatibility notes below).
5. Updates labels: removes ``autorelease: pending``, adds ``autorelease: tagged``.

This step is forge-agnostic. It works across all supported backends with
graceful degradation:

============================  ==========================================
Forge                         Behavior
============================  ==========================================
GitHub (``GitHubCLIBackend``) Full support: draft → published, labels.
GitLab (``GitLabCLIBackend``) No draft releases. Labels work on MRs.
Bitbucket (``BitbucketAPIBackend``) No native releases (tags only).
                              Labels are no-ops (logged warnings).
============================  ==========================================

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                            │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Tag step                │ After the Release PR is merged, tag the     │
    │                         │ merge commit so we know exactly which code  │
    │                         │ was released.                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Embedded manifest       │ JSON in the PR body that tells us which     │
    │                         │ packages were bumped and to what version.   │
    │                         │ We parse it to know what to tag.            │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Graceful degradation    │ Forges that don't support labels or draft   │
    │                         │ releases still work — we just skip those    │
    │                         │ operations and log a warning.               │
    └─────────────────────────┴─────────────────────────────────────────────┘

Tag flow::

    Release PR merged
         │
         ▼
    forge.list_prs(label="autorelease: pending", state="merged")
         │
         ▼
    extract manifest from PR body (JSON between marker comments)
         │
         ▼
    for each bumped package:
        vcs.tag("{name}-v{version}", sha=merge_commit)
         │
         ▼
    vcs.tag("v{umbrella_version}", sha=merge_commit)
    vcs.push(tags=True)
         │
         ▼
    forge.create_release(umbrella_tag, body=release_notes)
         │
         ▼
    forge.remove_labels("autorelease: pending")
    forge.add_labels("autorelease: tagged")
         │
         ▼
    ReleaseResult(tags_created=..., release_url=...)

Usage::

    from releasekit.release import tag_release

    result = await tag_release(
        vcs=git_backend,
        forge=github_backend,
        config=config,
        dry_run=False,
    )
    if result.ok:
        print(f'Tagged {len(result.tags_created)} packages')
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.vcs import VCS
from releasekit.config import ReleaseConfig, WorkspaceConfig
from releasekit.logging import get_logger
from releasekit.release_notes import generate_release_notes, render_release_notes
from releasekit.tags import TagResult, create_tags
from releasekit.versions import PackageVersion, ReleaseManifest

logger = get_logger(__name__)

_AUTORELEASE_PENDING = 'autorelease: pending'
_AUTORELEASE_TAGGED = 'autorelease: tagged'
_RELEASE_BRANCH_PREFIX = 'releasekit--release'
_MANIFEST_START = '<!-- releasekit:manifest:start -->'
_MANIFEST_END = '<!-- releasekit:manifest:end -->'


@dataclass
class ReleaseResult:
    """Outcome of a release (tag) run.

    Attributes:
        manifest: The parsed manifest from the PR body.
        tag_result: Result of tag creation operations.
        pr_number: The PR number that was processed.
        release_url: URL of the created platform Release.
        errors: Error messages keyed by step name.
    """

    manifest: ReleaseManifest | None = None
    tag_result: TagResult | None = None
    pr_number: int = 0
    release_url: str = ''
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Return True if no errors occurred."""
        return not self.errors

    @property
    def tags_created(self) -> list[str]:
        """Return tags that were successfully created."""
        if self.tag_result is None:
            return []
        return self.tag_result.created


def extract_manifest(pr_body: str) -> ReleaseManifest | None:
    """Extract a ReleaseManifest from markdown PR body.

    Looks for JSON between ``<!-- releasekit:manifest:start -->`` and
    ``<!-- releasekit:manifest:end -->`` marker comments.

    Args:
        pr_body: The full PR/MR body text.

    Returns:
        A :class:`ReleaseManifest` if found, otherwise ``None``.
    """
    pattern = re.escape(_MANIFEST_START) + r'\s*```json\s*(.*?)\s*```\s*' + re.escape(_MANIFEST_END)
    match = re.search(pattern, pr_body, flags=re.DOTALL)
    if not match:
        logger.warning('manifest_not_found', hint='PR body does not contain embedded manifest')
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        logger.warning('manifest_parse_error', error=str(exc))
        return None

    packages = [PackageVersion(**pkg) for pkg in data.get('packages', [])]
    git_sha = data.get('git_sha', '')
    if not git_sha:
        logger.warning('manifest_missing_sha')
        return None

    return ReleaseManifest(
        git_sha=git_sha,
        umbrella_tag=data.get('umbrella_tag', ''),
        packages=packages,
        created_at=data.get('created_at', ''),
    )


async def tag_release(
    *,
    vcs: VCS,
    forge: Forge | None,
    config: ReleaseConfig,
    ws_config: WorkspaceConfig,
    manifest_path: Path | None = None,
    dry_run: bool = False,
) -> ReleaseResult:
    """Run the tag step: find merged PR, tag, create Release.

    There are two ways to provide the manifest:

    1. **From a merged PR** (default): Finds the most recently merged PR
       with the ``autorelease: pending`` label, extracts the manifest
       from its body.
    2. **From a file** (``manifest_path``): Loads the manifest from a
       JSON file. Useful for local testing or when the forge is not
       available.

    Args:
        vcs: Version control backend.
        forge: Code forge backend. Pass None to skip PR lookup and
            label management.
        config: Global release configuration.
        ws_config: Per-workspace configuration.
        manifest_path: Optional path to a manifest JSON file. If
            provided, skips PR lookup.
        dry_run: If True, skip all side effects.

    Returns:
        A :class:`ReleaseResult` with tag creation outcomes.
    """
    result = ReleaseResult()
    release_branch = f'{_RELEASE_BRANCH_PREFIX}--{ws_config.label}' if ws_config.label else _RELEASE_BRANCH_PREFIX

    # 1. Get the manifest.
    manifest: ReleaseManifest | None = None
    pr_number = 0

    if manifest_path is not None:
        # Load from file.
        manifest = ReleaseManifest.load(manifest_path)
        logger.info('manifest_loaded_from_file', path=str(manifest_path))
    elif forge is not None and await forge.is_available():
        # Find merged PR with pending label on the release branch.
        prs = await forge.list_prs(
            label=_AUTORELEASE_PENDING,
            state='merged',
            head=release_branch,
            limit=1,
        )
        if not prs:
            result.errors['find_pr'] = f'No merged PR found with label {_AUTORELEASE_PENDING!r}. Nothing to tag.'
            return result

        pr_data = prs[0]
        pr_number = pr_data.get('number', 0)
        result.pr_number = pr_number

        # Get full PR body.
        full_pr = await forge.pr_data(pr_number)
        pr_body = full_pr.get('body', '')
        manifest = extract_manifest(pr_body)

        if manifest is None:
            result.errors['parse_manifest'] = f'Could not extract manifest from PR #{pr_number} body'
            return result
    else:
        result.errors['no_source'] = (
            'No manifest_path provided and forge is not available. Cannot determine what to tag.'
        )
        return result

    result.manifest = manifest
    bumped = manifest.bumped
    if not bumped:
        logger.info('tag_nothing_bumped', message='Manifest has no bumped packages.')
        return result

    # 2. Generate release notes.
    release_notes = await generate_release_notes(
        manifest=manifest,
        vcs=vcs,
        tag_format=ws_config.tag_format,
    )
    release_body = render_release_notes(release_notes)

    # 3. Create tags and Release.
    umbrella_version = bumped[0].new_version
    manifest_file = manifest_path
    if manifest_file is None and not dry_run:
        # Save manifest to temp file for the release asset.
        manifest_name = f'release-manifest--{ws_config.label}.json' if ws_config.label else 'release-manifest.json'
        manifest_file = Path(manifest_name)
        manifest.save(manifest_file)

    # Look for SLSA provenance file to attach to the release.
    provenance_file: Path | None = None
    if ws_config.slsa_provenance:
        prov_name = f'provenance-{ws_config.label}.intoto.jsonl' if ws_config.label else 'provenance.intoto.jsonl'
        candidate = Path(ws_config.root) / prov_name
        if candidate.exists():
            provenance_file = candidate

    tag_result = await create_tags(
        manifest=manifest,
        vcs=vcs,
        forge=forge,
        tag_format=ws_config.tag_format,
        umbrella_tag_format=ws_config.umbrella_tag,
        label=ws_config.label,
        release_body=release_body,
        release_title=f'Release v{umbrella_version}',
        manifest_path=manifest_file,
        provenance_path=provenance_file,
        publish_from=config.publish_from,
        dry_run=dry_run,
    )
    result.tag_result = tag_result
    result.release_url = tag_result.release_url

    if not tag_result.ok:
        for tag, error in tag_result.failed.items():
            result.errors[f'tag:{tag}'] = error
        return result

    # 4. Update labels on the PR.
    if forge is not None and pr_number and await forge.is_available():
        if not dry_run:
            await forge.remove_labels(pr_number, [_AUTORELEASE_PENDING], dry_run=dry_run)
            await forge.add_labels(pr_number, [_AUTORELEASE_TAGGED], dry_run=dry_run)
        logger.info('labels_updated', pr=pr_number, removed=_AUTORELEASE_PENDING, added=_AUTORELEASE_TAGGED)

    logger.info(
        'release_complete',
        tags_created=len(tag_result.created),
        tags_skipped=len(tag_result.skipped),
        release_url=result.release_url,
    )
    return result


__all__ = [
    'ReleaseResult',
    'extract_manifest',
    'tag_release',
]
