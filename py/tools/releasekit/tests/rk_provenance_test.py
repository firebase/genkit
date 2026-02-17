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

"""Tests for releasekit.provenance — SLSA Provenance v1 generation.

Covers:
- SubjectDigest dataclass and serialization
- BuildContext from environment detection (GitHub Actions, GitLab CI, CircleCI, local)
- ProvenanceStatement serialization and file writing
- compute_sha256 and subjects_from_dir helpers
- subjects_from_checksums helper
- generate_provenance single-package provenance
- generate_workspace_provenance multi-package provenance
- verify_provenance artifact-to-provenance matching
- Constants (URIs, types)
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from unittest import mock

from releasekit.provenance import (
    IN_TOTO_STATEMENT_TYPE,
    RELEASEKIT_BUILD_TYPE,
    SLSA_PROVENANCE_PREDICATE_TYPE,
    SLSA_PROVENANCE_V1_SCHEMA,
    SLSA_SUPPORTED_SPEC_VERSIONS,
    BuildContext,
    ProvenanceStatement,
    SubjectDigest,
    compute_sha256,
    generate_provenance,
    generate_workspace_provenance,
    has_oidc_credential,
    is_ci,
    should_sign_provenance,
    subjects_from_checksums,
    subjects_from_dir,
    validate_provenance_schema,
    verify_provenance,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_in_toto_statement_type(self) -> None:
        """Test in toto statement type."""
        assert IN_TOTO_STATEMENT_TYPE == 'https://in-toto.io/Statement/v1'

    def test_slsa_predicate_type(self) -> None:
        """Test slsa predicate type."""
        assert SLSA_PROVENANCE_PREDICATE_TYPE == 'https://slsa.dev/provenance/v1'

    def test_releasekit_build_type(self) -> None:
        """Test releasekit build type."""
        assert RELEASEKIT_BUILD_TYPE == 'https://firebase.google.com/releasekit/v1'


class TestSubjectDigest:
    """Tests for SubjectDigest dataclass."""

    def test_to_dict(self) -> None:
        """Serializes to in-toto subject format."""
        s = SubjectDigest(name='pkg-1.0.tar.gz', sha256='abc123')
        d = s.to_dict()
        assert d == {
            'name': 'pkg-1.0.tar.gz',
            'digest': {'sha256': 'abc123'},
        }

    def test_frozen(self) -> None:
        """SubjectDigest is immutable."""
        s = SubjectDigest(name='pkg.tar.gz', sha256='abc')
        try:
            s.name = 'other'  # type: ignore[misc]
            raise AssertionError('Should be frozen')
        except AttributeError:
            pass


class TestBuildContext:
    """Tests for BuildContext and environment detection."""

    def test_defaults(self) -> None:
        """Default context has empty fields."""
        ctx = BuildContext()
        assert ctx.builder_id == ''
        assert ctx.source_repo == ''
        assert ctx.is_ci is False
        assert ctx.ci_platform == ''

    def test_from_github_actions(self) -> None:
        """Detects GitHub Actions environment."""
        env = {
            'GITHUB_ACTIONS': 'true',
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_REPOSITORY': 'firebase/genkit',
            'GITHUB_SHA': 'abc123def456',
            'GITHUB_REF': 'refs/tags/v0.5.0',
            'GITHUB_RUN_ID': '12345',
            'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_WORKFLOW_REF': 'firebase/genkit/.github/workflows/release.yml@refs/heads/main',
            'RUNNER_ENVIRONMENT': 'github-hosted',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            ctx = BuildContext.from_env()

        assert ctx.is_ci is True
        assert ctx.ci_platform == 'github-actions'
        assert ctx.builder_id == 'https://github.com/actions/runner'
        assert ctx.source_repo == 'https://github.com/firebase/genkit'
        assert ctx.source_digest == 'abc123def456'
        assert ctx.source_ref == 'refs/tags/v0.5.0'
        assert ctx.run_id == '12345'
        assert 'actions/runs/12345' in ctx.run_url
        assert 'attempts/1' in ctx.invocation_id

    def test_from_github_actions_self_hosted(self) -> None:
        """Self-hosted runner gets different builder_id."""
        env = {
            'GITHUB_ACTIONS': 'true',
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_REPOSITORY': 'firebase/genkit',
            'GITHUB_SHA': 'abc123',
            'GITHUB_RUN_ID': '99',
            'GITHUB_RUN_ATTEMPT': '1',
            'RUNNER_ENVIRONMENT': 'self-hosted',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            ctx = BuildContext.from_env()

        assert 'self-hosted' in ctx.builder_id

    def test_from_gitlab_ci(self) -> None:
        """Detects GitLab CI environment."""
        env = {
            'GITLAB_CI': 'true',
            'CI_SERVER_URL': 'https://gitlab.com',
            'CI_PROJECT_URL': 'https://gitlab.com/org/repo',
            'CI_COMMIT_SHA': 'deadbeef',
            'CI_COMMIT_REF_NAME': 'main',
            'CI_JOB_ID': '42',
            'CI_PIPELINE_URL': 'https://gitlab.com/org/repo/-/pipelines/100',
            'CI_CONFIG_PATH': '.gitlab-ci.yml',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            ctx = BuildContext.from_env()

        assert ctx.is_ci is True
        assert ctx.ci_platform == 'gitlab-ci'
        assert ctx.source_digest == 'deadbeef'
        assert 'gitlab' in ctx.builder_id

    def test_from_circleci(self) -> None:
        """Detects CircleCI environment."""
        env = {
            'CIRCLECI': 'true',
            'CIRCLE_REPOSITORY_URL': 'https://github.com/org/repo',
            'CIRCLE_SHA1': 'cafe0123',
            'CIRCLE_BRANCH': 'main',
            'CIRCLE_BUILD_URL': 'https://circleci.com/gh/org/repo/123',
            'CIRCLE_BUILD_NUM': '123',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            ctx = BuildContext.from_env()

        assert ctx.is_ci is True
        assert ctx.ci_platform == 'circleci'
        assert ctx.source_digest == 'cafe0123'
        assert ctx.source_ref == 'refs/heads/main'

    def test_from_local(self) -> None:
        """Falls back to local context when no CI detected."""
        with mock.patch.dict(os.environ, {}, clear=True):
            ctx = BuildContext.from_env()

        assert ctx.is_ci is False
        assert ctx.ci_platform == 'local'
        assert ctx.builder_id.startswith('local://')


class TestProvenanceStatement:
    """Tests for ProvenanceStatement serialization."""

    def test_to_dict_structure(self) -> None:
        """Statement dict has correct top-level keys."""
        stmt = ProvenanceStatement(
            subjects=[SubjectDigest(name='a.tar.gz', sha256='aaa')],
            predicate={'buildDefinition': {}, 'runDetails': {}},
        )
        d = stmt.to_dict()
        assert d['_type'] == IN_TOTO_STATEMENT_TYPE
        assert d['predicateType'] == SLSA_PROVENANCE_PREDICATE_TYPE
        assert len(d['subject']) == 1
        assert d['subject'][0]['name'] == 'a.tar.gz'
        assert 'predicate' in d

    def test_to_json_compact(self) -> None:
        """Compact JSON has no indentation (JSONL convention)."""
        stmt = ProvenanceStatement(
            subjects=[SubjectDigest(name='a.tar.gz', sha256='aaa')],
            predicate={},
        )
        j = stmt.to_json()
        assert '\n' not in j
        parsed = json.loads(j)
        assert parsed['_type'] == IN_TOTO_STATEMENT_TYPE

    def test_to_json_indented(self) -> None:
        """Indented JSON is human-readable."""
        stmt = ProvenanceStatement(
            subjects=[SubjectDigest(name='a.tar.gz', sha256='aaa')],
            predicate={},
        )
        j = stmt.to_json(indent=2)
        assert '\n' in j

    def test_write(self, tmp_path: Path) -> None:
        """Write creates the file with correct content."""
        stmt = ProvenanceStatement(
            subjects=[SubjectDigest(name='a.tar.gz', sha256='aaa')],
            predicate={'key': 'value'},
        )
        out = tmp_path / 'provenance.intoto.jsonl'
        result = stmt.write(out)
        assert result == out
        assert out.exists()
        content = out.read_text(encoding='utf-8')
        parsed = json.loads(content.strip())
        assert parsed['_type'] == IN_TOTO_STATEMENT_TYPE

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Write creates parent directories if needed."""
        stmt = ProvenanceStatement(subjects=[], predicate={})
        out = tmp_path / 'deep' / 'nested' / 'provenance.intoto.jsonl'
        stmt.write(out)
        assert out.exists()

    def test_empty_subjects(self) -> None:
        """Statement with no subjects is valid."""
        stmt = ProvenanceStatement(subjects=[], predicate={})
        d = stmt.to_dict()
        assert d['subject'] == []


class TestComputeSha256:
    """Tests for compute_sha256."""

    def test_correct_digest(self, tmp_path: Path) -> None:
        """Computes correct SHA-256 for known content."""
        f = tmp_path / 'test.txt'
        content = b'hello world'
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_sha256(f) == expected

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file has the known SHA-256 of empty bytes."""
        f = tmp_path / 'empty.txt'
        f.write_bytes(b'')
        expected = hashlib.sha256(b'').hexdigest()
        assert compute_sha256(f) == expected


class TestSubjectsFromDir:
    """Tests for subjects_from_dir."""

    def test_finds_tar_gz_and_whl(self, tmp_path: Path) -> None:
        """Finds .tar.gz and .whl files."""
        (tmp_path / 'pkg-1.0.tar.gz').write_bytes(b'tarball')
        (tmp_path / 'pkg-1.0-py3-none-any.whl').write_bytes(b'wheel')
        (tmp_path / 'README.md').write_bytes(b'readme')

        subjects = subjects_from_dir(tmp_path)
        names = [s.name for s in subjects]
        assert 'pkg-1.0.tar.gz' in names
        assert 'pkg-1.0-py3-none-any.whl' in names
        assert 'README.md' not in names

    def test_finds_tgz(self, tmp_path: Path) -> None:
        """Finds .tgz files (npm tarballs)."""
        (tmp_path / 'core-1.0.0.tgz').write_bytes(b'npm tarball')
        subjects = subjects_from_dir(tmp_path)
        assert len(subjects) == 1
        assert subjects[0].name == 'core-1.0.0.tgz'

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        assert subjects_from_dir(tmp_path) == []

    def test_digests_are_correct(self, tmp_path: Path) -> None:
        """Digests match actual file content."""
        content = b'test content'
        (tmp_path / 'pkg-1.0.tar.gz').write_bytes(content)
        subjects = subjects_from_dir(tmp_path)
        expected = hashlib.sha256(content).hexdigest()
        assert subjects[0].sha256 == expected

    def test_sorted_output(self, tmp_path: Path) -> None:
        """Subjects are sorted by filename."""
        (tmp_path / 'z-pkg.whl').write_bytes(b'z')
        (tmp_path / 'a-pkg.whl').write_bytes(b'a')
        subjects = subjects_from_dir(tmp_path)
        assert subjects[0].name == 'a-pkg.whl'
        assert subjects[1].name == 'z-pkg.whl'


class TestSubjectsFromChecksums:
    """Tests for subjects_from_checksums."""

    def test_converts_checksum_map(self) -> None:
        """Converts {filename: sha256} to SubjectDigest list."""
        checksums = {
            'pkg-1.0.tar.gz': 'abc123',
            'pkg-1.0.whl': 'def456',
        }
        subjects = subjects_from_checksums(checksums)
        assert len(subjects) == 2
        assert subjects[0].name == 'pkg-1.0.tar.gz'
        assert subjects[0].sha256 == 'abc123'

    def test_sorted_by_name(self) -> None:
        """Output is sorted by filename."""
        checksums = {'z.whl': 'z', 'a.tar.gz': 'a'}
        subjects = subjects_from_checksums(checksums)
        assert subjects[0].name == 'a.tar.gz'

    def test_empty(self) -> None:
        """Empty input returns empty list."""
        assert subjects_from_checksums({}) == []


class TestGenerateProvenance:
    """Tests for generate_provenance."""

    def test_basic_statement(self) -> None:
        """Generates a valid in-toto statement."""
        ctx = BuildContext(
            builder_id='https://github.com/actions/runner',
            source_repo='https://github.com/firebase/genkit',
            source_digest='abc123',
            is_ci=True,
            ci_platform='github-actions',
        )
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='deadbeef')],
            context=ctx,
            package_name='genkit',
            package_version='0.5.0',
            ecosystem='python',
        )
        d = stmt.to_dict()
        assert d['_type'] == IN_TOTO_STATEMENT_TYPE
        assert d['predicateType'] == SLSA_PROVENANCE_PREDICATE_TYPE
        assert len(d['subject']) == 1
        assert d['subject'][0]['digest']['sha256'] == 'deadbeef'

    def test_predicate_structure(self) -> None:
        """Predicate has buildDefinition and runDetails."""
        ctx = BuildContext(
            builder_id='https://github.com/actions/runner',
            source_repo='https://github.com/firebase/genkit',
            source_digest='abc123',
            is_ci=True,
            ci_platform='github-actions',
            invocation_id='https://github.com/firebase/genkit/actions/runs/1/attempts/1',
        )
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='aaa')],
            context=ctx,
            package_name='genkit',
            package_version='0.5.0',
        )
        pred = stmt.predicate
        assert 'buildDefinition' in pred
        assert 'runDetails' in pred

        build_def = pred['buildDefinition']
        assert build_def['buildType'] == RELEASEKIT_BUILD_TYPE
        assert build_def['externalParameters']['packageName'] == 'genkit'
        assert build_def['externalParameters']['packageVersion'] == '0.5.0'

        run_details = pred['runDetails']
        assert run_details['builder']['id'] == 'https://github.com/actions/runner'
        assert run_details['metadata']['invocationId'] == ctx.invocation_id

    def test_resolved_dependencies_includes_source(self) -> None:
        """Source repo appears in resolvedDependencies."""
        ctx = BuildContext(
            builder_id='local://test',
            source_repo='https://github.com/firebase/genkit',
            source_digest='abc123',
        )
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='aaa')],
            context=ctx,
        )
        deps = stmt.predicate['buildDefinition'].get('resolvedDependencies', [])
        assert len(deps) >= 1
        assert deps[0]['uri'] == 'git+https://github.com/firebase/genkit'
        assert deps[0]['digest']['gitCommit'] == 'abc123'

    def test_extra_resolved_dependencies(self) -> None:
        """Additional resolved dependencies are included."""
        ctx = BuildContext(builder_id='local://test')
        extra = [{'uri': 'pkg:pypi/requests@2.31.0', 'digest': {'sha256': 'fff'}}]
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='aaa')],
            context=ctx,
            resolved_dependencies=extra,
        )
        deps = stmt.predicate['buildDefinition'].get('resolvedDependencies', [])
        assert any(d['uri'] == 'pkg:pypi/requests@2.31.0' for d in deps)

    def test_build_times(self) -> None:
        """Build start/finish times appear in metadata."""
        ctx = BuildContext(
            builder_id='local://test',
            invocation_id='test-invocation',
        )
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='aaa')],
            context=ctx,
            build_start_time='2026-01-01T00:00:00Z',
            build_finish_time='2026-01-01T00:05:00Z',
        )
        meta = stmt.predicate['runDetails']['metadata']
        assert meta['startedOn'] == '2026-01-01T00:00:00Z'
        assert meta['finishedOn'] == '2026-01-01T00:05:00Z'

    def test_auto_finish_time(self) -> None:
        """Finish time is auto-populated if not provided."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='aaa')],
            context=ctx,
        )
        # The finish time should be set (non-empty) even without explicit input.
        meta = stmt.predicate['runDetails'].get('metadata', {})
        assert meta.get('finishedOn', '') != ''

    def test_local_context_no_source_deps(self) -> None:
        """Local context without source_repo has no resolvedDependencies."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='pkg.tar.gz', sha256='aaa')],
            context=ctx,
        )
        build_def = stmt.predicate['buildDefinition']
        assert 'resolvedDependencies' not in build_def


class TestGenerateWorkspaceProvenance:
    """Tests for generate_workspace_provenance."""

    def test_collects_all_subjects(self) -> None:
        """All artifacts from all packages are collected."""
        checksums = {
            'pkg-a': {'pkg-a-1.0.tar.gz': 'aaa', 'pkg-a-1.0.whl': 'bbb'},
            'pkg-b': {'pkg-b-2.0.tar.gz': 'ccc'},
        }
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_workspace_provenance(
            artifact_checksums=checksums,
            context=ctx,
        )
        subjects = stmt.to_dict()['subject']
        assert len(subjects) == 3
        names = {s['name'] for s in subjects}
        assert names == {'pkg-a-1.0.tar.gz', 'pkg-a-1.0.whl', 'pkg-b-2.0.tar.gz'}

    def test_empty_checksums(self) -> None:
        """Empty checksums produce empty subjects."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_workspace_provenance(
            artifact_checksums={},
            context=ctx,
        )
        assert stmt.to_dict()['subject'] == []

    def test_ecosystem_in_predicate(self) -> None:
        """Ecosystem is recorded in externalParameters."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_workspace_provenance(
            artifact_checksums={'pkg': {'pkg.tar.gz': 'aaa'}},
            context=ctx,
            ecosystem='python',
        )
        params = stmt.predicate['buildDefinition']['externalParameters']
        assert params['ecosystem'] == 'python'


class TestVerifyProvenance:
    """Tests for verify_provenance."""

    def _write_provenance(self, tmp_path: Path, subjects: list[dict]) -> Path:
        """Helper to write a provenance file."""
        stmt = {
            '_type': IN_TOTO_STATEMENT_TYPE,
            'predicateType': SLSA_PROVENANCE_PREDICATE_TYPE,
            'subject': subjects,
            'predicate': {},
        }
        prov = tmp_path / 'provenance.intoto.jsonl'
        prov.write_text(json.dumps(stmt), encoding='utf-8')
        return prov

    def test_matching_artifact(self, tmp_path: Path) -> None:
        """Artifact matching a subject returns ok."""
        content = b'test artifact content'
        artifact = tmp_path / 'pkg-1.0.tar.gz'
        artifact.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()

        prov = self._write_provenance(
            tmp_path,
            [
                {'name': 'pkg-1.0.tar.gz', 'digest': {'sha256': sha}},
            ],
        )

        ok, reason = verify_provenance(artifact, prov)
        assert ok is True
        assert reason == 'OK'

    def test_mismatched_digest(self, tmp_path: Path) -> None:
        """Artifact with wrong digest fails."""
        artifact = tmp_path / 'pkg-1.0.tar.gz'
        artifact.write_bytes(b'real content')

        prov = self._write_provenance(
            tmp_path,
            [
                {'name': 'pkg-1.0.tar.gz', 'digest': {'sha256': 'wrong_digest'}},
            ],
        )

        ok, reason = verify_provenance(artifact, prov)
        assert ok is False
        assert 'not found in provenance' in reason

    def test_missing_artifact(self, tmp_path: Path) -> None:
        """Missing artifact file returns error."""
        prov = self._write_provenance(tmp_path, [])
        ok, reason = verify_provenance(tmp_path / 'nonexistent.tar.gz', prov)
        assert ok is False
        assert 'not found' in reason.lower()

    def test_missing_provenance(self, tmp_path: Path) -> None:
        """Missing provenance file returns error."""
        artifact = tmp_path / 'pkg.tar.gz'
        artifact.write_bytes(b'content')
        ok, reason = verify_provenance(artifact, tmp_path / 'missing.intoto.jsonl')
        assert ok is False
        assert 'not found' in reason.lower()

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Invalid JSON in provenance returns error."""
        artifact = tmp_path / 'pkg.tar.gz'
        artifact.write_bytes(b'content')
        prov = tmp_path / 'bad.intoto.jsonl'
        prov.write_text('not json', encoding='utf-8')

        ok, reason = verify_provenance(artifact, prov)
        assert ok is False
        assert 'parse' in reason.lower()

    def test_wrong_statement_type(self, tmp_path: Path) -> None:
        """Wrong _type field returns error."""
        artifact = tmp_path / 'pkg.tar.gz'
        artifact.write_bytes(b'content')
        prov = tmp_path / 'wrong.intoto.jsonl'
        prov.write_text(
            json.dumps({
                '_type': 'https://wrong.type/v1',
                'predicateType': SLSA_PROVENANCE_PREDICATE_TYPE,
                'subject': [],
                'predicate': {},
            }),
            encoding='utf-8',
        )

        ok, reason = verify_provenance(artifact, prov)
        assert ok is False
        assert 'statement type' in reason.lower()

    def test_wrong_predicate_type(self, tmp_path: Path) -> None:
        """Wrong predicateType returns error."""
        artifact = tmp_path / 'pkg.tar.gz'
        artifact.write_bytes(b'content')
        prov = tmp_path / 'wrong.intoto.jsonl'
        prov.write_text(
            json.dumps({
                '_type': IN_TOTO_STATEMENT_TYPE,
                'predicateType': 'https://wrong.predicate/v1',
                'subject': [],
                'predicate': {},
            }),
            encoding='utf-8',
        )

        ok, reason = verify_provenance(artifact, prov)
        assert ok is False
        assert 'predicate type' in reason.lower()

    def test_digest_match_name_mismatch(self, tmp_path: Path) -> None:
        """Digest match with different name still passes (with note)."""
        content = b'test content'
        artifact = tmp_path / 'renamed.tar.gz'
        artifact.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()

        prov = self._write_provenance(
            tmp_path,
            [
                {'name': 'original.tar.gz', 'digest': {'sha256': sha}},
            ],
        )

        ok, reason = verify_provenance(artifact, prov)
        assert ok is True
        assert 'name mismatch' in reason.lower()

    def test_multiple_subjects(self, tmp_path: Path) -> None:
        """Finds the correct subject among multiple."""
        content_a = b'artifact a'
        content_b = b'artifact b'
        artifact = tmp_path / 'b.tar.gz'
        artifact.write_bytes(content_b)

        prov = self._write_provenance(
            tmp_path,
            [
                {'name': 'a.tar.gz', 'digest': {'sha256': hashlib.sha256(content_a).hexdigest()}},
                {'name': 'b.tar.gz', 'digest': {'sha256': hashlib.sha256(content_b).hexdigest()}},
            ],
        )

        ok, reason = verify_provenance(artifact, prov)
        assert ok is True
        assert reason == 'OK'


class TestIsCi:
    """Tests for is_ci()."""

    def test_true_when_ci_set(self) -> None:
        """Test true when ci set."""
        with mock.patch.dict(os.environ, {'CI': 'true'}, clear=True):
            assert is_ci() is True

    def test_false_when_ci_not_set(self) -> None:
        """Test false when ci not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert is_ci() is False


class TestHasOidcCredential:
    """Tests for has_oidc_credential()."""

    def test_github_actions_oidc(self) -> None:
        """Test github actions oidc."""
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert has_oidc_credential() is True

    def test_gitlab_ci_jwt_v2(self) -> None:
        """Test gitlab ci jwt v2."""
        with mock.patch.dict(os.environ, {'CI_JOB_JWT_V2': 'eyJ...'}, clear=True):
            assert has_oidc_credential() is True

    def test_gitlab_ci_jwt(self) -> None:
        """Test gitlab ci jwt."""
        with mock.patch.dict(os.environ, {'CI_JOB_JWT': 'eyJ...'}, clear=True):
            assert has_oidc_credential() is True

    def test_circleci_oidc(self) -> None:
        """Test circleci oidc."""
        with mock.patch.dict(os.environ, {'CIRCLE_OIDC_TOKEN_V2': 'eyJ...'}, clear=True):
            assert has_oidc_credential() is True

    def test_no_oidc(self) -> None:
        """Test no oidc."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert has_oidc_credential() is False

    def test_ci_without_oidc(self) -> None:
        """Test ci without oidc."""
        with mock.patch.dict(os.environ, {'CI': 'true'}, clear=True):
            assert has_oidc_credential() is False


class TestShouldSignProvenance:
    """Tests for should_sign_provenance()."""

    def test_ci_with_oidc(self) -> None:
        """CI + OIDC → True (SLSA L2 capable)."""
        env = {'CI': 'true', 'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert should_sign_provenance() is True

    def test_ci_without_oidc(self) -> None:
        """CI without OIDC → False (only L1)."""
        with mock.patch.dict(os.environ, {'CI': 'true'}, clear=True):
            assert should_sign_provenance() is False

    def test_local_with_oidc(self) -> None:
        """Local with OIDC env var → False (not CI)."""
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert should_sign_provenance() is False

    def test_local_no_oidc(self) -> None:
        """Local without OIDC → False."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert should_sign_provenance() is False


class TestRoundTrip:
    """End-to-end: generate provenance, write it, verify artifacts against it."""

    def test_generate_write_verify(self, tmp_path: Path) -> None:
        """Full round-trip: generate → write → verify."""
        # Create fake artifacts.
        content_a = b'artifact-a-content'
        content_b = b'artifact-b-content'
        (tmp_path / 'a-1.0.tar.gz').write_bytes(content_a)
        (tmp_path / 'b-2.0.tar.gz').write_bytes(content_b)

        # Generate provenance from directory.
        subjects = subjects_from_dir(tmp_path)
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_provenance(subjects=subjects, context=ctx)

        # Write provenance.
        prov_path = tmp_path / 'provenance.intoto.jsonl'
        stmt.write(prov_path)

        # Verify each artifact.
        for artifact_name in ['a-1.0.tar.gz', 'b-2.0.tar.gz']:
            ok, reason = verify_provenance(tmp_path / artifact_name, prov_path)
            assert ok is True, f'{artifact_name}: {reason}'

    def test_workspace_round_trip(self, tmp_path: Path) -> None:
        """Workspace provenance round-trip with checksums."""
        content = b'workspace artifact'
        artifact = tmp_path / 'pkg-1.0.tar.gz'
        artifact.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()

        checksums = {'my-pkg': {'pkg-1.0.tar.gz': sha}}
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_workspace_provenance(
            artifact_checksums=checksums,
            context=ctx,
            ecosystem='python',
        )

        prov_path = tmp_path / 'provenance.intoto.jsonl'
        stmt.write(prov_path)

        ok, reason = verify_provenance(artifact, prov_path)
        assert ok is True, reason

    def test_tampered_artifact_fails(self, tmp_path: Path) -> None:
        """Tampered artifact fails verification."""
        original = b'original content'
        artifact = tmp_path / 'pkg.tar.gz'
        artifact.write_bytes(original)

        subjects = subjects_from_dir(tmp_path)
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_provenance(subjects=subjects, context=ctx)
        prov_path = tmp_path / 'provenance.intoto.jsonl'
        stmt.write(prov_path)

        # Tamper with the artifact.
        artifact.write_bytes(b'tampered content')

        ok, reason = verify_provenance(artifact, prov_path)
        assert ok is False
        assert 'not found in provenance' in reason


class TestSupportedVersions:
    """Tests for SLSA_SUPPORTED_SPEC_VERSIONS constant."""

    def test_includes_v1_1(self) -> None:
        """Test includes v1 1."""
        assert '1.1' in SLSA_SUPPORTED_SPEC_VERSIONS

    def test_includes_v1_2(self) -> None:
        """Test includes v1 2."""
        assert '1.2' in SLSA_SUPPORTED_SPEC_VERSIONS

    def test_includes_draft(self) -> None:
        """Test includes draft."""
        assert 'draft' in SLSA_SUPPORTED_SPEC_VERSIONS

    def test_is_tuple(self) -> None:
        """Test is tuple."""
        assert isinstance(SLSA_SUPPORTED_SPEC_VERSIONS, tuple)


class TestSchemaExport:
    """Tests for the exported JSON schema constant."""

    def test_schema_has_required_fields(self) -> None:
        """Test schema has required fields."""
        assert '$schema' in SLSA_PROVENANCE_V1_SCHEMA
        assert 'required' in SLSA_PROVENANCE_V1_SCHEMA
        required = SLSA_PROVENANCE_V1_SCHEMA['required']
        assert '_type' in required
        assert 'subject' in required
        assert 'predicateType' in required
        assert 'predicate' in required

    def test_schema_enforces_statement_type(self) -> None:
        """Test schema enforces statement type."""
        props = SLSA_PROVENANCE_V1_SCHEMA['properties']
        assert props['_type']['const'] == IN_TOTO_STATEMENT_TYPE

    def test_schema_enforces_predicate_type(self) -> None:
        """Test schema enforces predicate type."""
        props = SLSA_PROVENANCE_V1_SCHEMA['properties']
        assert props['predicateType']['const'] == SLSA_PROVENANCE_PREDICATE_TYPE


class TestValidateProvenanceSchema:
    """Tests for validate_provenance_schema()."""

    def _make_valid_statement(self) -> dict:
        """Create a minimal valid provenance statement."""
        return {
            '_type': IN_TOTO_STATEMENT_TYPE,
            'subject': [{'name': 'a.tar.gz', 'digest': {'sha256': 'abc123'}}],
            'predicateType': SLSA_PROVENANCE_PREDICATE_TYPE,
            'predicate': {
                'buildDefinition': {
                    'buildType': RELEASEKIT_BUILD_TYPE,
                    'externalParameters': {},
                    'internalParameters': {},
                },
                'runDetails': {
                    'builder': {'id': 'local://test'},
                },
            },
        }

    def test_valid_statement_passes(self) -> None:
        """Test valid statement passes."""
        stmt = self._make_valid_statement()
        errors = validate_provenance_schema(stmt)
        assert errors == []

    def test_valid_json_string_passes(self) -> None:
        """Test valid json string passes."""
        stmt = self._make_valid_statement()
        errors = validate_provenance_schema(json.dumps(stmt))
        assert errors == []

    def test_valid_file_passes(self, tmp_path: Path) -> None:
        """Test valid file passes."""
        stmt = self._make_valid_statement()
        p = tmp_path / 'prov.intoto.jsonl'
        p.write_text(json.dumps(stmt), encoding='utf-8')
        errors = validate_provenance_schema(p)
        assert errors == []

    def test_missing_type_fails(self) -> None:
        """Test missing type fails."""
        stmt = self._make_valid_statement()
        del stmt['_type']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_wrong_type_fails(self) -> None:
        """Test wrong type fails."""
        stmt = self._make_valid_statement()
        stmt['_type'] = 'wrong'
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_subject_fails(self) -> None:
        """Test missing subject fails."""
        stmt = self._make_valid_statement()
        del stmt['subject']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_empty_subject_fails(self) -> None:
        """Test empty subject fails."""
        stmt = self._make_valid_statement()
        stmt['subject'] = []
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_predicate_fails(self) -> None:
        """Test missing predicate fails."""
        stmt = self._make_valid_statement()
        del stmt['predicate']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_build_definition_fails(self) -> None:
        """Test missing build definition fails."""
        stmt = self._make_valid_statement()
        del stmt['predicate']['buildDefinition']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_run_details_fails(self) -> None:
        """Test missing run details fails."""
        stmt = self._make_valid_statement()
        del stmt['predicate']['runDetails']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_builder_id_fails(self) -> None:
        """Test missing builder id fails."""
        stmt = self._make_valid_statement()
        del stmt['predicate']['runDetails']['builder']['id']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_build_type_fails(self) -> None:
        """Test missing build type fails."""
        stmt = self._make_valid_statement()
        del stmt['predicate']['buildDefinition']['buildType']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_missing_external_parameters_fails(self) -> None:
        """Test missing external parameters fails."""
        stmt = self._make_valid_statement()
        del stmt['predicate']['buildDefinition']['externalParameters']
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_invalid_json_string_fails(self) -> None:
        """Test invalid json string fails."""
        errors = validate_provenance_schema('{bad json')
        assert len(errors) > 0
        assert 'Invalid JSON' in errors[0]

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        """Test missing file fails."""
        errors = validate_provenance_schema(tmp_path / 'nonexistent.json')
        assert len(errors) > 0
        assert 'File not found' in errors[0]

    def test_subject_missing_digest_sha256_fails(self) -> None:
        """Test subject missing digest sha256 fails."""
        stmt = self._make_valid_statement()
        stmt['subject'] = [{'name': 'a.tar.gz', 'digest': {}}]
        errors = validate_provenance_schema(stmt)
        assert len(errors) > 0

    def test_with_resolved_dependencies(self) -> None:
        """Full statement with resolvedDependencies passes."""
        stmt = self._make_valid_statement()
        stmt['predicate']['buildDefinition']['resolvedDependencies'] = [
            {
                'uri': 'git+https://github.com/firebase/genkit@refs/heads/main',
                'digest': {'gitCommit': 'abc123'},
            },
        ]
        errors = validate_provenance_schema(stmt)
        assert errors == []

    def test_with_metadata(self) -> None:
        """Full statement with metadata passes."""
        stmt = self._make_valid_statement()
        stmt['predicate']['runDetails']['metadata'] = {
            'invocationId': 'https://github.com/firebase/genkit/actions/runs/123',
            'startedOn': '2026-01-01T00:00:00Z',
            'finishedOn': '2026-01-01T00:01:00Z',
        }
        errors = validate_provenance_schema(stmt)
        assert errors == []


class TestGeneratedProvenancePassesSchema:
    """Validates that generate_provenance() output passes schema validation."""

    def test_local_build(self) -> None:
        """Local build provenance passes schema."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='a.tar.gz', sha256='abc123')],
            context=ctx,
        )
        errors = validate_provenance_schema(stmt.to_dict())
        assert errors == [], f'Schema errors: {errors}'

    def test_github_actions_build(self) -> None:
        """GitHub Actions provenance passes schema."""
        env = {
            'GITHUB_ACTIONS': 'true',
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_REPOSITORY': 'firebase/genkit',
            'GITHUB_SHA': 'abc123def456',
            'GITHUB_REF': 'refs/heads/main',
            'GITHUB_RUN_ID': '12345',
            'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_WORKFLOW_REF': 'firebase/genkit/.github/workflows/release.yml@refs/heads/main',
            'RUNNER_ENVIRONMENT': 'github-hosted',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            ctx = BuildContext.from_env()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='genkit-0.6.0.tar.gz', sha256='deadbeef')],
            context=ctx,
            config_source='py/tools/releasekit/releasekit.toml',
            ecosystem='python',
            package_name='genkit',
            package_version='0.6.0',
            build_start_time='2026-01-01T00:00:00Z',
            build_finish_time='2026-01-01T00:05:00Z',
        )
        d = stmt.to_dict()
        errors = validate_provenance_schema(d)
        assert errors == [], f'Schema errors: {errors}'

        # Verify spec-compliant source URI format.
        deps = d['predicate']['buildDefinition'].get('resolvedDependencies', [])
        assert len(deps) >= 1
        source_dep = deps[0]
        assert source_dep['uri'].startswith('git+https://')
        assert '@refs/heads/main' in source_dep['uri']
        assert source_dep['digest']['gitCommit'] == 'abc123def456'

        # Verify externalParameters includes configSource, repository, ref.
        ext = d['predicate']['buildDefinition']['externalParameters']
        assert ext['configSource'] == 'py/tools/releasekit/releasekit.toml'
        assert ext['repository'] == 'https://github.com/firebase/genkit'
        assert ext['ref'] == 'refs/heads/main'

    def test_workspace_provenance_passes_schema(self) -> None:
        """Workspace provenance passes schema."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_workspace_provenance(
            artifact_checksums={
                'pkg-a': {'a-0.1.0.tar.gz': 'aaa111'},
                'pkg-b': {'b-0.2.0.whl': 'bbb222'},
            },
            context=ctx,
            ecosystem='python',
        )
        errors = validate_provenance_schema(stmt.to_dict())
        assert errors == [], f'Schema errors: {errors}'

    def test_round_trip_json_passes_schema(self, tmp_path: Path) -> None:
        """Write to file, read back, validate schema."""
        ctx = BuildContext(builder_id='local://test')
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='x.whl', sha256='fff000')],
            context=ctx,
        )
        p = tmp_path / 'provenance.intoto.jsonl'
        stmt.write(p)
        errors = validate_provenance_schema(p)
        assert errors == [], f'Schema errors: {errors}'
