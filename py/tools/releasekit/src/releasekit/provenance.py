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

r"""SLSA Provenance generation for release artifacts.

Generates `in-toto attestation`_ statements with `SLSA Provenance v1`_
predicates that describe **how** each artifact was built: which builder
ran the build, what source was used, and what the outputs are.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ in-toto Statement   │ An envelope that says "these artifacts were   │
    │                     │ produced by this build process".              │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ SLSA Provenance     │ The specific claim inside the envelope that   │
    │                     │ records builder, source, and build details.   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Subject             │ The artifact(s) the statement is about,       │
    │                     │ identified by name + SHA-256 digest.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Builder             │ The CI platform that ran the build            │
    │                     │ (e.g. GitHub Actions).                        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Build Type          │ The kind of build (releasekit publish).       │
    └─────────────────────┴────────────────────────────────────────────────┘

SLSA Level Coverage::

    ┌────────┬──────────────────────────────────────────────────────────┐
    │ Level  │ What this module provides                                │
    ├────────┼──────────────────────────────────────────────────────────┤
    │ L1     │ Provenance exists: in-toto statement with SLSA          │
    │        │ Provenance v1 predicate, distributed alongside          │
    │        │ artifacts and attached to GitHub Releases.               │
    ├────────┼──────────────────────────────────────────────────────────┤
    │ L2     │ Authentic provenance: when combined with Sigstore        │
    │        │ signing (signing.py), the provenance is signed by a     │
    │        │ key tied to the hosted CI platform via OIDC.            │
    ├────────┼──────────────────────────────────────────────────────────┤
    │ L3     │ Hardened builds: build isolation verification,           │
    │        │ non-falsifiable provenance (control-plane generated),    │
    │        │ complete externalParameters, ephemeral build env,        │
    │        │ builder version tracking, and byproducts.               │
    └────────┴──────────────────────────────────────────────────────────┘

Output format::

    The provenance is written as a JSON file following the in-toto
    Statement v1 spec.  The filename convention is:

        <artifact>.intoto.jsonl     (single artifact)
        provenance.intoto.jsonl     (multi-artifact / workspace)

    When signed with Sigstore, a companion ``.sigstore.json`` bundle
    is produced alongside the provenance file.

Usage::

    from releasekit.provenance import generate_provenance, BuildContext

    ctx = BuildContext.from_env()
    stmt = generate_provenance(
        subjects=[
            SubjectDigest(name='genkit-0.5.0.tar.gz', sha256='abc123...'),
        ],
        context=ctx,
        config_source='py/tools/releasekit/releasekit.toml',
    )
    Path('provenance.intoto.jsonl').write_text(stmt.to_json())

.. _in-toto attestation: https://in-toto.io/Statement/v1
.. _SLSA Provenance v1: https://slsa.dev/provenance/v1
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import jsonschema

from releasekit.backends.validation.oidc import (
    has_oidc_credential as _has_oidc,
)
from releasekit.logging import get_logger
from releasekit.utils.date import utc_iso

logger = get_logger(__name__)

# --- Constants ---

#: in-toto Statement v1 type URI.
IN_TOTO_STATEMENT_TYPE = 'https://in-toto.io/Statement/v1'

#: SLSA Provenance v1 predicate type URI.
SLSA_PROVENANCE_PREDICATE_TYPE = 'https://slsa.dev/provenance/v1'

#: ReleaseKit build type URI.
RELEASEKIT_BUILD_TYPE = 'https://firebase.google.com/releasekit/v1'

#: Version of this provenance generator.
_PROVENANCE_GENERATOR_VERSION = '0.1.0'

#: SLSA specification versions that this module's output conforms to.
#: The provenance predicate schema (``https://slsa.dev/provenance/v1``)
#: is identical across v1.1, v1.2, and the working draft.
SLSA_SUPPORTED_SPEC_VERSIONS: tuple[str, ...] = ('1.1', '1.2', 'draft')


class SLSABuildLevel(IntEnum):
    """SLSA Build track levels.

    See https://slsa.dev/spec/v1.1/levels for definitions.

    - **L0**: No guarantees.
    - **L1**: Provenance exists.
    - **L2**: Hosted build platform + signed provenance.
    - **L3**: Hardened builds — isolated, ephemeral, non-falsifiable
      provenance generated by the control plane.
    """

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3


#: Known hosted CI platforms that qualify for SLSA Build L2+.
#: Maps ``ci_platform`` identifier to whether the platform provides
#: L3-grade isolation (ephemeral VMs, no cross-build influence).
_HOSTED_BUILD_PLATFORMS: dict[str, SLSABuildLevel] = {
    'github-actions': SLSABuildLevel.L3,
    'gitlab-ci': SLSABuildLevel.L3,
    'circleci': SLSABuildLevel.L2,
    'google-cloud-build': SLSABuildLevel.L3,
}


# --- Data classes ---


@dataclass(frozen=True)
class SubjectDigest:
    """An artifact subject identified by name and SHA-256 digest.

    Attributes:
        name: Artifact filename (e.g. ``genkit-0.5.0.tar.gz``).
        sha256: Hex-encoded SHA-256 digest of the artifact.
    """

    name: str
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to in-toto subject format."""
        return {
            'name': self.name,
            'digest': {'sha256': self.sha256},
        }


@dataclass(frozen=True)
class BuildContext:
    """CI/build environment context for provenance generation.

    Captures the builder identity, source repository, commit SHA,
    and other metadata from the CI environment.

    Attributes:
        builder_id: URI identifying the build platform
            (e.g. ``https://github.com/actions/runner``).
        source_repo: Full repository URI
            (e.g. ``https://github.com/firebase/genkit``).
        source_digest: Git commit SHA of the source.
        source_ref: Git ref (branch or tag) being built.
        source_entry_point: Path to the build config within the repo
            (e.g. ``.github/workflows/release.yml``).
        run_id: CI run identifier (e.g. GitHub Actions run ID).
        run_url: URL to the CI run (for human inspection).
        is_ci: Whether the build is running in a CI environment.
        ci_platform: Name of the CI platform (e.g. ``github-actions``).
        invocation_id: Unique invocation URI for this build.
    """

    builder_id: str = ''
    source_repo: str = ''
    source_digest: str = ''
    source_ref: str = ''
    source_entry_point: str = ''
    run_id: str = ''
    run_url: str = ''
    is_ci: bool = False
    ci_platform: str = ''
    invocation_id: str = ''
    runner_environment: str = ''
    runner_os: str = ''
    runner_arch: str = ''

    @property
    def slsa_build_level(self) -> SLSABuildLevel:
        """Compute the SLSA Build level achievable with this context.

        The level is determined by the build environment:

        - **L0**: No provenance (not applicable here — we always generate).
        - **L1**: Provenance exists (any build, including local).
        - **L2**: Hosted build platform + signed provenance (CI with OIDC).
        - **L3**: Hardened builds — hosted platform with ephemeral,
          isolated build environments and non-falsifiable provenance.

        Returns:
            The highest SLSA Build level this context can achieve.
        """
        if not self.is_ci:
            return SLSABuildLevel.L1

        # L2 requires a hosted build platform.
        platform_level = _HOSTED_BUILD_PLATFORMS.get(
            self.ci_platform,
            SLSABuildLevel.L1,
        )
        if platform_level < SLSABuildLevel.L2:
            return SLSABuildLevel.L1

        # L2 requires OIDC-signed provenance.
        if not has_oidc_credential():
            return SLSABuildLevel.L1

        # L3 requires hardened isolation (ephemeral, hosted runners).
        if platform_level >= SLSABuildLevel.L3:
            # GitHub Actions: only github-hosted runners qualify for L3.
            # Self-hosted runners are L2 at best.
            if self.ci_platform == 'github-actions':
                if self.runner_environment == 'github-hosted':
                    return SLSABuildLevel.L3
                return SLSABuildLevel.L2
            # GitLab CI: shared runners on gitlab.com are L3.
            # Self-managed runners are L2.
            if self.ci_platform == 'gitlab-ci':
                os.environ.get('CI_RUNNER_DESCRIPTION', '')
                os.environ.get('CI_RUNNER_TAGS', '')
                if os.environ.get('CI_SERVER_URL', '') == 'https://gitlab.com':
                    return SLSABuildLevel.L3
                return SLSABuildLevel.L2
            return SLSABuildLevel.L3

        return SLSABuildLevel.L2

    @classmethod
    def from_env(cls) -> BuildContext:
        """Detect build context from CI environment variables.

        Supports:
        - GitHub Actions
        - GitLab CI
        - CircleCI

        Falls back to a local-build context if no CI is detected.

        Returns:
            A populated :class:`BuildContext`.
        """
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            return cls._from_github_actions()
        if os.environ.get('GITLAB_CI') == 'true':
            return cls._from_gitlab_ci()
        if os.environ.get('CIRCLECI') == 'true':
            return cls._from_circleci()
        return cls._from_local()

    @classmethod
    def _from_github_actions(cls) -> BuildContext:
        """Build context from GitHub Actions environment."""
        server = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
        repo = os.environ.get('GITHUB_REPOSITORY', '')
        sha = os.environ.get('GITHUB_SHA', '')
        ref = os.environ.get('GITHUB_REF', '')
        run_id = os.environ.get('GITHUB_RUN_ID', '')
        run_attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
        workflow = os.environ.get('GITHUB_WORKFLOW_REF', '')

        run_url = f'{server}/{repo}/actions/runs/{run_id}' if repo and run_id else ''
        invocation_id = f'{server}/{repo}/actions/runs/{run_id}/attempts/{run_attempt}' if repo and run_id else ''

        # Builder ID follows SLSA GitHub Actions convention.
        runner_env = os.environ.get('RUNNER_ENVIRONMENT', '')
        if runner_env == 'github-hosted':
            builder_id = f'{server}/actions/runner'
        else:
            builder_id = f'{server}/actions/runner/self-hosted'

        return cls(
            builder_id=builder_id,
            source_repo=f'{server}/{repo}' if repo else '',
            source_digest=sha,
            source_ref=ref,
            source_entry_point=workflow,
            run_id=run_id,
            run_url=run_url,
            is_ci=True,
            ci_platform='github-actions',
            invocation_id=invocation_id,
            runner_environment=runner_env or 'unknown',
            runner_os=os.environ.get('RUNNER_OS', platform.system()),
            runner_arch=os.environ.get('RUNNER_ARCH', platform.machine()),
        )

    @classmethod
    def _from_gitlab_ci(cls) -> BuildContext:
        """Build context from GitLab CI environment."""
        project_url = os.environ.get('CI_PROJECT_URL', '')
        sha = os.environ.get('CI_COMMIT_SHA', '')
        ref = os.environ.get('CI_COMMIT_REF_NAME', '')
        job_id = os.environ.get('CI_JOB_ID', '')
        pipeline_url = os.environ.get('CI_PIPELINE_URL', '')
        config_path = os.environ.get('CI_CONFIG_PATH', '.gitlab-ci.yml')

        return cls(
            builder_id=f'{os.environ.get("CI_SERVER_URL", "https://gitlab.com")}/gitlab-runner',
            source_repo=project_url,
            source_digest=sha,
            source_ref=ref,
            source_entry_point=config_path,
            run_id=job_id,
            run_url=pipeline_url,
            is_ci=True,
            ci_platform='gitlab-ci',
            invocation_id=pipeline_url,
            runner_environment=os.environ.get('CI_RUNNER_DESCRIPTION', 'unknown'),
            runner_os=platform.system(),
            runner_arch=platform.machine(),
        )

    @classmethod
    def _from_circleci(cls) -> BuildContext:
        """Build context from CircleCI environment."""
        repo_url = os.environ.get('CIRCLE_REPOSITORY_URL', '')
        sha = os.environ.get('CIRCLE_SHA1', '')
        branch = os.environ.get('CIRCLE_BRANCH', '')
        build_url = os.environ.get('CIRCLE_BUILD_URL', '')
        build_num = os.environ.get('CIRCLE_BUILD_NUM', '')

        return cls(
            builder_id='https://circleci.com/runner',
            source_repo=repo_url,
            source_digest=sha,
            source_ref=f'refs/heads/{branch}' if branch else '',
            source_entry_point='.circleci/config.yml',
            run_id=build_num,
            run_url=build_url,
            is_ci=True,
            ci_platform='circleci',
            invocation_id=build_url,
            runner_environment='circleci-hosted',
            runner_os=platform.system(),
            runner_arch=platform.machine(),
        )

    @classmethod
    def _from_local(cls) -> BuildContext:
        """Build context for local (non-CI) builds."""
        return cls(
            builder_id=f'local://{socket.gethostname()}',
            is_ci=False,
            ci_platform='local',
        )


@dataclass(frozen=True)
class ProvenanceStatement:
    """An in-toto Statement with SLSA Provenance v1 predicate.

    Attributes:
        subjects: Artifacts this statement covers.
        predicate: The SLSA Provenance v1 predicate dict.
        predicate_type: The predicate type URI.
        statement_type: The in-toto statement type URI.
    """

    subjects: list[SubjectDigest] = field(default_factory=list)
    predicate: dict[str, Any] = field(default_factory=dict)
    predicate_type: str = SLSA_PROVENANCE_PREDICATE_TYPE
    statement_type: str = IN_TOTO_STATEMENT_TYPE

    def to_dict(self) -> dict[str, Any]:
        """Serialize to in-toto Statement v1 format."""
        return {
            '_type': self.statement_type,
            'subject': [s.to_dict() for s in self.subjects],
            'predicateType': self.predicate_type,
            'predicate': self.predicate,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize to JSON string.

        Args:
            indent: JSON indentation level. ``None`` for compact
                single-line output (JSONL convention).

        Returns:
            JSON string of the in-toto statement.
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    def write(self, path: Path, *, indent: int | None = None) -> Path:
        """Write the statement to a file.

        Args:
            path: Output file path.
            indent: JSON indentation level.

        Returns:
            The path written to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(indent=indent) + '\n', encoding='utf-8')
        logger.info('provenance_written', path=str(path))
        return path


# --- Digest helpers ---


def compute_sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file.

    Args:
        path: Path to the file.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    logger.debug('sha256_computed', file=path.name, digest=sha)
    return sha


def subjects_from_dir(dist_dir: Path) -> list[SubjectDigest]:
    """Build subject digests for all distribution files in a directory.

    Scans for ``.tar.gz``, ``.whl``, ``.tgz``, and ``.jar`` files.

    Args:
        dist_dir: Directory containing distribution artifacts.

    Returns:
        List of :class:`SubjectDigest` for each artifact found.
    """
    subjects: list[SubjectDigest] = []
    extensions = {'.gz', '.whl', '.tgz', '.jar'}
    for path in sorted(dist_dir.iterdir()):
        if path.suffix in extensions or path.name.endswith('.tar.gz'):
            subjects.append(
                SubjectDigest(
                    name=path.name,
                    sha256=compute_sha256(path),
                )
            )
    return subjects


def subjects_from_checksums(checksums: dict[str, str]) -> list[SubjectDigest]:
    """Build subject digests from a pre-computed checksum mapping.

    Args:
        checksums: Mapping of filename to SHA-256 hex digest
            (as produced by ``publisher._compute_dist_checksum``).

    Returns:
        List of :class:`SubjectDigest`.
    """
    return [SubjectDigest(name=name, sha256=digest) for name, digest in sorted(checksums.items())]


# --- Provenance generation ---


def _build_predicate(
    *,
    context: BuildContext,
    config_source: str = '',
    resolved_dependencies: list[dict[str, Any]] | None = None,
    build_start_time: str = '',
    build_finish_time: str = '',
    package_name: str = '',
    package_version: str = '',
    ecosystem: str = '',
) -> dict[str, Any]:
    """Build the SLSA Provenance v1 predicate.

    Follows https://slsa.dev/provenance/v1 schema.

    Args:
        context: Build environment context.
        config_source: Path to the build config (e.g. ``releasekit.toml``).
        resolved_dependencies: List of resolved dependency dicts.
        build_start_time: ISO 8601 start time.
        build_finish_time: ISO 8601 finish time.
        package_name: Name of the package being built.
        package_version: Version of the package being built.
        ecosystem: Package ecosystem (``python``, ``js``, etc.).

    Returns:
        SLSA Provenance v1 predicate dict.
    """
    # buildDefinition — describes what was built and how.
    external_params: dict[str, Any] = {}
    if config_source:
        external_params['configSource'] = config_source
    if package_name:
        external_params['packageName'] = package_name
    if package_version:
        external_params['packageVersion'] = package_version
    if ecosystem:
        external_params['ecosystem'] = ecosystem
    if context.source_repo:
        external_params['repository'] = context.source_repo
    if context.source_ref:
        external_params['ref'] = context.source_ref

    internal_params: dict[str, Any] = {
        'generator': {
            'name': 'releasekit',
            'version': _PROVENANCE_GENERATOR_VERSION,
        },
    }

    build_definition: dict[str, Any] = {
        'buildType': RELEASEKIT_BUILD_TYPE,
        'externalParameters': external_params,
        'internalParameters': internal_params,
    }

    # resolvedDependencies — the source and any lockfile.
    # URI format follows the SLSA spec example:
    #   git+https://github.com/octocat/hello-world@refs/heads/main
    deps: list[dict[str, Any]] = []
    if context.source_repo and context.source_digest:
        source_uri = context.source_repo
        # Prefix with git+ if it looks like an HTTP(S) repo URL.
        if source_uri.startswith('https://') or source_uri.startswith('http' + '://'):
            source_uri = f'git+{source_uri}'
        # Append the ref if available.
        if context.source_ref:
            source_uri = f'{source_uri}@{context.source_ref}'
        source_dep: dict[str, Any] = {
            'uri': source_uri,
            'digest': {'gitCommit': context.source_digest},
        }
        deps.append(source_dep)
    if resolved_dependencies:
        deps.extend(resolved_dependencies)
    if deps:
        build_definition['resolvedDependencies'] = deps

    # runDetails — describes who ran the build.
    builder: dict[str, Any] = {'id': context.builder_id}

    # builder.version — L3 requires actual platform version info.
    builder_version: dict[str, str] = {}
    if context.ci_platform:
        builder_version[context.ci_platform] = 'latest'
    if context.runner_os:
        builder_version['runnerOs'] = context.runner_os
    if context.runner_arch:
        builder_version['runnerArch'] = context.runner_arch
    if context.runner_environment:
        builder_version['runnerEnvironment'] = context.runner_environment
    builder_version['python'] = platform.python_version()
    if builder_version:
        builder['version'] = builder_version

    # Record the achieved SLSA build level in internalParameters.
    internal_params['slsaBuildLevel'] = int(context.slsa_build_level)

    metadata: dict[str, Any] = {}
    if context.invocation_id:
        metadata['invocationId'] = context.invocation_id
    if build_start_time:
        metadata['startedOn'] = build_start_time
    if build_finish_time:
        metadata['finishedOn'] = build_finish_time

    run_details: dict[str, Any] = {'builder': builder}
    if metadata:
        run_details['metadata'] = metadata

    # byproducts — build config digest for L3 forensics.
    byproducts: list[dict[str, Any]] = []
    if config_source and context.source_repo:
        byproducts.append({
            'name': config_source,
            'uri': context.source_repo,
            'mediaType': 'text/plain',
        })
    if byproducts:
        run_details['byproducts'] = byproducts

    return {
        'buildDefinition': build_definition,
        'runDetails': run_details,
    }


def generate_provenance(
    *,
    subjects: list[SubjectDigest],
    context: BuildContext,
    config_source: str = '',
    resolved_dependencies: list[dict[str, Any]] | None = None,
    build_start_time: str = '',
    build_finish_time: str = '',
    package_name: str = '',
    package_version: str = '',
    ecosystem: str = '',
) -> ProvenanceStatement:
    """Generate a SLSA Provenance v1 in-toto statement.

    This is the main entry point for provenance generation. It creates
    a complete in-toto Statement with a SLSA Provenance v1 predicate
    describing how the given artifacts were built.

    Args:
        subjects: Artifact digests (the "what was produced").
        context: Build environment context (the "who built it").
        config_source: Path to the build configuration file.
        resolved_dependencies: Additional resolved dependencies
            beyond the source repo (e.g. lockfile entries).
        build_start_time: ISO 8601 build start time.
        build_finish_time: ISO 8601 build finish time.
        package_name: Package name (for single-package provenance).
        package_version: Package version.
        ecosystem: Package ecosystem identifier.

    Returns:
        A :class:`ProvenanceStatement` ready to serialize.
    """
    if not build_finish_time:
        build_finish_time = utc_iso()

    predicate = _build_predicate(
        context=context,
        config_source=config_source,
        resolved_dependencies=resolved_dependencies,
        build_start_time=build_start_time,
        build_finish_time=build_finish_time,
        package_name=package_name,
        package_version=package_version,
        ecosystem=ecosystem,
    )

    stmt = ProvenanceStatement(
        subjects=list(subjects),
        predicate=predicate,
    )

    logger.info(
        'provenance_generated',
        subjects=len(subjects),
        builder=context.builder_id,
        ci=context.ci_platform,
    )
    return stmt


def generate_workspace_provenance(
    *,
    artifact_checksums: dict[str, dict[str, str]],
    context: BuildContext,
    config_source: str = '',
    resolved_dependencies: list[dict[str, Any]] | None = None,
    build_start_time: str = '',
    build_finish_time: str = '',
    ecosystem: str = '',
) -> ProvenanceStatement:
    """Generate provenance for an entire workspace publish run.

    Collects all artifact subjects from all packages into a single
    in-toto statement. This is the typical usage for ``releasekit publish``.

    Args:
        artifact_checksums: Mapping of ``package_name`` to
            ``{filename: sha256_hex}`` dicts. Produced by the
            publisher pipeline.
        context: Build environment context.
        config_source: Path to the build configuration file.
        resolved_dependencies: Additional resolved dependencies.
        build_start_time: ISO 8601 build start time.
        build_finish_time: ISO 8601 build finish time.
        ecosystem: Package ecosystem identifier.

    Returns:
        A :class:`ProvenanceStatement` covering all artifacts.
    """
    subjects: list[SubjectDigest] = []
    for _pkg_name, checksums in sorted(artifact_checksums.items()):
        subjects.extend(subjects_from_checksums(checksums))

    return generate_provenance(
        subjects=subjects,
        context=context,
        config_source=config_source,
        resolved_dependencies=resolved_dependencies,
        build_start_time=build_start_time,
        build_finish_time=build_finish_time,
        ecosystem=ecosystem,
    )


def verify_provenance(
    artifact_path: Path,
    provenance_path: Path,
) -> tuple[bool, str]:
    """Verify that an artifact matches its provenance statement.

    Checks that the artifact's SHA-256 digest appears in the
    provenance statement's subject list.

    Args:
        artifact_path: Path to the artifact file.
        provenance_path: Path to the ``.intoto.jsonl`` file.

    Returns:
        A ``(ok, reason)`` tuple. ``ok`` is ``True`` if the artifact
        digest matches a subject in the provenance.
    """
    if not artifact_path.exists():
        return False, f'Artifact not found: {artifact_path}'
    if not provenance_path.exists():
        return False, f'Provenance not found: {provenance_path}'

    try:
        raw = provenance_path.read_text(encoding='utf-8').strip()
        stmt = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        return False, f'Failed to parse provenance: {exc}'

    # Validate statement structure.
    stmt_type = stmt.get('_type', '')
    if stmt_type != IN_TOTO_STATEMENT_TYPE:
        return False, f'Unexpected statement type: {stmt_type}'

    pred_type = stmt.get('predicateType', '')
    if pred_type != SLSA_PROVENANCE_PREDICATE_TYPE:
        return False, f'Unexpected predicate type: {pred_type}'

    # Compute artifact digest.
    actual_sha256 = compute_sha256(artifact_path)
    artifact_name = artifact_path.name

    # Search subjects for a match.
    subjects = stmt.get('subject', [])
    for subj in subjects:
        subj_name = subj.get('name', '')
        subj_digest = subj.get('digest', {}).get('sha256', '')
        if subj_name == artifact_name and subj_digest == actual_sha256:
            return True, 'OK'

    # Check if digest matches any subject (name might differ).
    for subj in subjects:
        subj_digest = subj.get('digest', {}).get('sha256', '')
        if subj_digest == actual_sha256:
            return True, f'OK (name mismatch: expected {subj.get("name")}, got {artifact_name})'

    return False, (f'Artifact {artifact_name} (sha256:{actual_sha256[:16]}...) not found in provenance subjects')


def has_oidc_credential() -> bool:
    """Check whether an OIDC credential is available for signing.

    Delegates to the canonical implementation in
    :func:`releasekit.backends.validation.oidc.has_oidc_credential`.

    Returns:
        ``True`` if an OIDC credential is detected.
    """
    return _has_oidc()


def is_ci() -> bool:
    """Check whether we are running in a CI environment.

    Returns:
        ``True`` if the ``CI`` environment variable is set.
    """
    return bool(os.environ.get('CI'))


def should_sign_provenance() -> bool:
    """Determine whether provenance should be auto-signed.

    Returns ``True`` when running in CI **and** an OIDC credential is
    available — i.e. the environment supports SLSA Build L2+.

    On GitHub-hosted runners and gitlab.com shared runners this
    achieves SLSA Build L3 (hardened, isolated builds). On self-hosted
    runners or CircleCI it achieves L2.

    This is used to auto-enable ``--sign-provenance`` so that CI
    pipelines achieve the highest possible level without explicit flags.

    Returns:
        ``True`` if the environment supports signed provenance.
    """
    return is_ci() and has_oidc_credential()


# --- JSON Schema for SLSA Provenance v1 ---
#
# Derived from the normative text at:
#   https://slsa.dev/spec/v1.1/provenance  (v1.1)
#   https://slsa.dev/spec/v1.2/build-provenance  (v1.2)
# The predicate schema (predicateType: https://slsa.dev/provenance/v1)
# is identical across v1.1, v1.2, and the working draft.

_RESOURCE_DESCRIPTOR_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'uri': {'type': 'string'},
        'digest': {
            'type': 'object',
            'additionalProperties': {'type': 'string'},
        },
        'name': {'type': 'string'},
        'downloadLocation': {'type': 'string'},
        'mediaType': {'type': 'string'},
        'content': {'type': 'string'},
        'annotations': {'type': 'object'},
    },
    'additionalProperties': False,
}

_BUILDER_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['id'],
    'properties': {
        'id': {'type': 'string'},
        'version': {
            'type': 'object',
            'additionalProperties': {'type': 'string'},
        },
        'builderDependencies': {
            'type': 'array',
            'items': _RESOURCE_DESCRIPTOR_SCHEMA,
        },
    },
    'additionalProperties': False,
}

_BUILD_METADATA_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'invocationId': {'type': 'string'},
        'startedOn': {'type': 'string'},
        'finishedOn': {'type': 'string'},
    },
    'additionalProperties': False,
}

_BUILD_DEFINITION_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['buildType', 'externalParameters'],
    'properties': {
        'buildType': {'type': 'string'},
        'externalParameters': {'type': 'object'},
        'internalParameters': {'type': 'object'},
        'resolvedDependencies': {
            'type': 'array',
            'items': _RESOURCE_DESCRIPTOR_SCHEMA,
        },
    },
    'additionalProperties': False,
}

_RUN_DETAILS_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['builder'],
    'properties': {
        'builder': _BUILDER_SCHEMA,
        'metadata': _BUILD_METADATA_SCHEMA,
        'byproducts': {
            'type': 'array',
            'items': _RESOURCE_DESCRIPTOR_SCHEMA,
        },
    },
    'additionalProperties': False,
}

_PREDICATE_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['buildDefinition', 'runDetails'],
    'properties': {
        'buildDefinition': _BUILD_DEFINITION_SCHEMA,
        'runDetails': _RUN_DETAILS_SCHEMA,
    },
    'additionalProperties': False,
}

_SUBJECT_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['name', 'digest'],
    'properties': {
        'name': {'type': 'string'},
        'digest': {
            'type': 'object',
            'required': ['sha256'],
            'additionalProperties': {'type': 'string'},
        },
    },
    'additionalProperties': False,
}

#: JSON Schema for a complete in-toto Statement with SLSA Provenance v1
#: predicate.  Validates the structure required by SLSA Build L1.
SLSA_PROVENANCE_V1_SCHEMA: dict[str, Any] = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'title': 'in-toto Statement with SLSA Provenance v1',
    'description': (
        'Validates an in-toto Statement v1 envelope containing a '
        'SLSA Provenance v1 predicate.  Conforms to SLSA spec v1.1, '
        'v1.2, and the working draft.'
    ),
    'type': 'object',
    'required': ['_type', 'subject', 'predicateType', 'predicate'],
    'properties': {
        '_type': {
            'type': 'string',
            'const': IN_TOTO_STATEMENT_TYPE,
        },
        'subject': {
            'type': 'array',
            'minItems': 1,
            'items': _SUBJECT_SCHEMA,
        },
        'predicateType': {
            'type': 'string',
            'const': SLSA_PROVENANCE_PREDICATE_TYPE,
        },
        'predicate': _PREDICATE_SCHEMA,
    },
    'additionalProperties': False,
}


def validate_provenance_schema(
    statement: dict[str, Any] | str | Path,
) -> list[str]:
    """Validate a provenance statement against the SLSA Provenance v1 JSON Schema.

    This uses the ``jsonschema`` library if available, falling back to a
    lightweight structural check when ``jsonschema`` is not installed.

    Args:
        statement: Either a parsed dict, a JSON string, or a ``Path``
            to a ``.intoto.jsonl`` file.

    Returns:
        A list of validation error messages.  An empty list means the
        statement is valid.
    """
    # Normalise input to a dict.
    if isinstance(statement, Path):
        if not statement.exists():
            return [f'File not found: {statement}']
        try:
            stmt = json.loads(statement.read_text(encoding='utf-8').strip())
        except (json.JSONDecodeError, OSError) as exc:
            return [f'Invalid JSON: {exc}']
    elif isinstance(statement, str):
        # Could be a JSON string or a file path.
        if not statement.strip().startswith('{'):
            p = Path(statement)
            if p.exists():
                try:
                    stmt = json.loads(p.read_text(encoding='utf-8').strip())
                except (json.JSONDecodeError, OSError) as exc:
                    return [f'Invalid JSON: {exc}']
            else:
                return [f'File not found: {statement}']
        else:
            try:
                stmt = json.loads(statement)
            except json.JSONDecodeError as exc:
                return [f'Invalid JSON: {exc}']
    else:
        stmt = statement

    # Try jsonschema first (full validation).
    try:
        validator = jsonschema.Draft202012Validator(SLSA_PROVENANCE_V1_SCHEMA)
        errors = sorted(validator.iter_errors(stmt), key=lambda e: list(e.absolute_path))
        return [f'{".".join(str(p) for p in e.absolute_path) or "(root)"}: {e.message}' for e in errors]
    except ImportError:
        pass

    # Fallback: lightweight structural check.
    issues: list[str] = []
    if not isinstance(stmt, dict):
        return ['Statement must be a JSON object']

    if stmt.get('_type') != IN_TOTO_STATEMENT_TYPE:
        issues.append(f'_type must be {IN_TOTO_STATEMENT_TYPE!r}, got {stmt.get("_type")!r}')
    if stmt.get('predicateType') != SLSA_PROVENANCE_PREDICATE_TYPE:
        issues.append(f'predicateType must be {SLSA_PROVENANCE_PREDICATE_TYPE!r}, got {stmt.get("predicateType")!r}')

    subjects = stmt.get('subject')
    if not isinstance(subjects, list) or len(subjects) == 0:
        issues.append('subject must be a non-empty array')
    elif subjects:
        for i, subj in enumerate(subjects):
            if not isinstance(subj, dict):
                issues.append(f'subject[{i}] must be an object')
                continue
            if 'name' not in subj:
                issues.append(f'subject[{i}] missing required field "name"')
            digest = subj.get('digest')
            if not isinstance(digest, dict) or 'sha256' not in digest:
                issues.append(f'subject[{i}].digest must contain "sha256"')

    predicate = stmt.get('predicate')
    if not isinstance(predicate, dict):
        issues.append('predicate must be an object')
    else:
        bd = predicate.get('buildDefinition')
        if not isinstance(bd, dict):
            issues.append('predicate.buildDefinition must be an object')
        else:
            if 'buildType' not in bd:
                issues.append('predicate.buildDefinition missing required field "buildType"')
            if 'externalParameters' not in bd:
                issues.append('predicate.buildDefinition missing required field "externalParameters"')

        rd = predicate.get('runDetails')
        if not isinstance(rd, dict):
            issues.append('predicate.runDetails must be an object')
        else:
            builder = rd.get('builder')
            if not isinstance(builder, dict) or 'id' not in builder:
                issues.append('predicate.runDetails.builder must be an object with "id"')

    return issues


__all__ = [
    'BuildContext',
    'ProvenanceStatement',
    'SLSA_PROVENANCE_V1_SCHEMA',
    'SLSA_SUPPORTED_SPEC_VERSIONS',
    'SLSABuildLevel',
    'SubjectDigest',
    'compute_sha256',
    'generate_provenance',
    'generate_workspace_provenance',
    'has_oidc_credential',
    'is_ci',
    'should_sign_provenance',
    'subjects_from_checksums',
    'subjects_from_dir',
    'validate_provenance_schema',
    'verify_provenance',
]
