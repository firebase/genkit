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

"""Tests for SLSA Build Level compliance.

Covers:
- SLSABuildLevel enum
- BuildContext.slsa_build_level property (L1/L2/L3 detection)
- SLSALevelValidator (context validation + provenance validation)
- Provenance generation with L3 fields (builder.version, byproducts, slsaBuildLevel)
- Protocol conformance
"""

from __future__ import annotations

import os
from unittest import mock

from releasekit.backends.validation import Validator, all_passed, run_validators
from releasekit.backends.validation.slsa import SLSALevelValidator
from releasekit.provenance import (
    _HOSTED_BUILD_PLATFORMS,
    BuildContext,
    SLSABuildLevel,
    SubjectDigest,
    generate_provenance,
)


def _github_l3_context() -> BuildContext:
    """BuildContext simulating a GitHub Actions github-hosted runner."""
    return BuildContext(
        builder_id='https://github.com/actions/runner',
        source_repo='https://github.com/firebase/genkit',
        source_digest='abc123def456',
        source_ref='refs/heads/main',
        source_entry_point='.github/workflows/release.yml',
        run_id='12345',
        run_url='https://github.com/firebase/genkit/actions/runs/12345',
        is_ci=True,
        ci_platform='github-actions',
        invocation_id='https://github.com/firebase/genkit/actions/runs/12345/attempts/1',
        runner_environment='github-hosted',
        runner_os='Linux',
        runner_arch='X64',
    )


def _github_self_hosted_context() -> BuildContext:
    """BuildContext simulating a GitHub Actions self-hosted runner."""
    return BuildContext(
        builder_id='https://github.com/actions/runner/self-hosted',
        source_repo='https://github.com/firebase/genkit',
        source_digest='abc123def456',
        source_ref='refs/heads/main',
        source_entry_point='.github/workflows/release.yml',
        run_id='12345',
        run_url='https://github.com/firebase/genkit/actions/runs/12345',
        is_ci=True,
        ci_platform='github-actions',
        invocation_id='https://github.com/firebase/genkit/actions/runs/12345/attempts/1',
        runner_environment='self-hosted',
        runner_os='Linux',
        runner_arch='X64',
    )


def _gitlab_context() -> BuildContext:
    """BuildContext simulating a GitLab CI shared runner."""
    return BuildContext(
        builder_id='https://gitlab.com/gitlab-runner',
        source_repo='https://gitlab.com/myorg/myrepo',
        source_digest='abc123',
        source_ref='main',
        source_entry_point='.gitlab-ci.yml',
        run_id='999',
        run_url='https://gitlab.com/myorg/myrepo/-/pipelines/999',
        is_ci=True,
        ci_platform='gitlab-ci',
        invocation_id='https://gitlab.com/myorg/myrepo/-/pipelines/999',
        runner_environment='shared-runner',
        runner_os='Linux',
        runner_arch='x86_64',
    )


def _local_context() -> BuildContext:
    """BuildContext for a local build."""
    return BuildContext(
        builder_id='local://myhost',
        is_ci=False,
        ci_platform='local',
    )


def _l3_provenance_dict() -> dict:
    """A provenance dict that should pass L3 validation."""
    return {
        '_type': 'https://in-toto.io/Statement/v1',
        'subject': [
            {'name': 'foo-1.0.tar.gz', 'digest': {'sha256': 'abc123'}},
        ],
        'predicateType': 'https://slsa.dev/provenance/v1',
        'predicate': {
            'buildDefinition': {
                'buildType': 'https://firebase.google.com/releasekit/v1',
                'externalParameters': {
                    'repository': 'https://github.com/firebase/genkit',
                    'ref': 'refs/heads/main',
                    'configSource': 'releasekit.toml',
                },
                'internalParameters': {
                    'generator': {'name': 'releasekit', 'version': '0.1.0'},
                    'slsaBuildLevel': 3,
                },
                'resolvedDependencies': [
                    {
                        'uri': 'git+https://github.com/firebase/genkit@refs/heads/main',
                        'digest': {'gitCommit': 'abc123def456'},
                    },
                ],
            },
            'runDetails': {
                'builder': {
                    'id': 'https://github.com/actions/runner',
                    'version': {
                        'github-actions': 'latest',
                        'runnerOs': 'Linux',
                        'runnerArch': 'X64',
                        'runnerEnvironment': 'github-hosted',
                        'python': '3.12.0',
                    },
                },
                'metadata': {
                    'invocationId': 'https://github.com/firebase/genkit/actions/runs/12345/attempts/1',
                    'startedOn': '2026-01-01T00:00:00Z',
                    'finishedOn': '2026-01-01T00:01:00Z',
                },
            },
        },
    }


class TestSLSABuildLevel:
    """Tests for the SLSABuildLevel enum."""

    def test_values(self) -> None:
        """Test values."""
        assert SLSABuildLevel.L0 == 0
        assert SLSABuildLevel.L1 == 1
        assert SLSABuildLevel.L2 == 2
        assert SLSABuildLevel.L3 == 3

    def test_ordering(self) -> None:
        """Test ordering."""
        assert SLSABuildLevel.L0 < SLSABuildLevel.L1
        assert SLSABuildLevel.L1 < SLSABuildLevel.L2
        assert SLSABuildLevel.L2 < SLSABuildLevel.L3

    def test_int_conversion(self) -> None:
        """Test int conversion."""
        assert int(SLSABuildLevel.L3) == 3


class TestBuildContextSLSALevel:
    """Tests for BuildContext.slsa_build_level property."""

    def test_local_build_is_l1(self) -> None:
        """Test local build is l1."""
        ctx = _local_context()
        assert ctx.slsa_build_level == SLSABuildLevel.L1

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_github_hosted_is_l3(self) -> None:
        """Test github hosted is l3."""
        ctx = _github_l3_context()
        assert ctx.slsa_build_level == SLSABuildLevel.L3

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_github_self_hosted_is_l2(self) -> None:
        """Test github self hosted is l2."""
        ctx = _github_self_hosted_context()
        assert ctx.slsa_build_level == SLSABuildLevel.L2

    @mock.patch.dict(
        os.environ,
        {
            'CI_JOB_JWT_V2': 'fake.jwt.token',
            'CI_SERVER_URL': 'https://gitlab.com',
        },
    )
    def test_gitlab_shared_is_l3(self) -> None:
        """Test gitlab shared is l3."""
        ctx = _gitlab_context()
        assert ctx.slsa_build_level == SLSABuildLevel.L3

    @mock.patch.dict(
        os.environ,
        {
            'CI_JOB_JWT_V2': 'fake.jwt.token',
            'CI_SERVER_URL': 'https://gitlab.mycompany.com',
        },
    )
    def test_gitlab_self_managed_is_l2(self) -> None:
        """Test gitlab self managed is l2."""
        ctx = _gitlab_context()
        assert ctx.slsa_build_level == SLSABuildLevel.L2

    def test_no_oidc_is_l1(self) -> None:
        """CI without OIDC can only reach L1."""
        env = {
            k: ''
            for k in [
                'ACTIONS_ID_TOKEN_REQUEST_URL',
                'CI_JOB_JWT_V2',
                'CI_JOB_JWT',
                'CIRCLE_OIDC_TOKEN_V2',
            ]
        }
        with mock.patch.dict(os.environ, env, clear=False):
            ctx = _github_l3_context()
            assert ctx.slsa_build_level == SLSABuildLevel.L1

    def test_unknown_platform_is_l1(self) -> None:
        """Test unknown platform is l1."""
        ctx = BuildContext(
            builder_id='https://example.com/builder',
            is_ci=True,
            ci_platform='unknown-ci',
        )
        assert ctx.slsa_build_level == SLSABuildLevel.L1


class TestHostedBuildPlatforms:
    """Tests for the _HOSTED_BUILD_PLATFORMS constant."""

    def test_github_actions_is_l3(self) -> None:
        """Test github actions is l3."""
        assert _HOSTED_BUILD_PLATFORMS['github-actions'] == SLSABuildLevel.L3

    def test_gitlab_ci_is_l3(self) -> None:
        """Test gitlab ci is l3."""
        assert _HOSTED_BUILD_PLATFORMS['gitlab-ci'] == SLSABuildLevel.L3

    def test_circleci_is_l2(self) -> None:
        """Test circleci is l2."""
        assert _HOSTED_BUILD_PLATFORMS['circleci'] == SLSABuildLevel.L2

    def test_gcb_is_l3(self) -> None:
        """Test gcb is l3."""
        assert _HOSTED_BUILD_PLATFORMS['google-cloud-build'] == SLSABuildLevel.L3


class TestSLSAValidatorProtocol:
    """SLSALevelValidator implements the Validator protocol."""

    def test_is_validator(self) -> None:
        """Test is validator."""
        assert isinstance(SLSALevelValidator(), Validator)

    def test_name(self) -> None:
        """Test name."""
        assert SLSALevelValidator().name == 'slsa.build-level'

    def test_custom_name(self) -> None:
        """Test custom name."""
        v = SLSALevelValidator(validator_id='custom.slsa')
        assert v.name == 'custom.slsa'

    def test_unsupported_type(self) -> None:
        """Test unsupported type."""
        r = SLSALevelValidator().validate(42)
        assert r.ok is False
        assert 'Unsupported subject type' in r.message


class TestSLSAContextValidation:
    """SLSALevelValidator with BuildContext subjects."""

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_l3_github_hosted_passes(self) -> None:
        """Test l3 github hosted passes."""
        v = SLSALevelValidator(target_level=3)
        r = v.validate(_github_l3_context())
        assert r.ok is True
        assert r.details['achieved_level'] == 3

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_l3_self_hosted_fails(self) -> None:
        """Test l3 self hosted fails."""
        v = SLSALevelValidator(target_level=3)
        r = v.validate(_github_self_hosted_context())
        assert r.ok is False
        assert r.details['achieved_level'] == 2
        assert any('github-hosted' in i for i in r.details['issues'])

    def test_l1_local_passes(self) -> None:
        """Test l1 local passes."""
        v = SLSALevelValidator(target_level=1)
        r = v.validate(_local_context())
        assert r.ok is True

    def test_l2_local_fails(self) -> None:
        """Test l2 local fails."""
        v = SLSALevelValidator(target_level=2)
        r = v.validate(_local_context())
        assert r.ok is False
        assert 'hosted build platform' in str(r.details.get('issues', []))

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_l2_github_hosted_passes(self) -> None:
        """Test l2 github hosted passes."""
        v = SLSALevelValidator(target_level=2)
        r = v.validate(_github_l3_context())
        assert r.ok is True

    def test_l3_missing_entry_point_fails(self) -> None:
        """Test l3 missing entry point fails."""
        ctx = BuildContext(
            builder_id='https://github.com/actions/runner',
            source_repo='https://github.com/firebase/genkit',
            source_digest='abc123',
            source_ref='refs/heads/main',
            source_entry_point='',
            run_id='12345',
            is_ci=True,
            ci_platform='github-actions',
            invocation_id='https://github.com/firebase/genkit/actions/runs/12345/attempts/1',
            runner_environment='github-hosted',
        )
        with mock.patch.dict(
            os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'}
        ):
            v = SLSALevelValidator(target_level=3)
            r = v.validate(ctx)
            assert r.ok is False
            assert any('source_entry_point' in i for i in r.details['issues'])

    def test_l3_missing_invocation_id_fails(self) -> None:
        """Test l3 missing invocation id fails."""
        ctx = BuildContext(
            builder_id='https://github.com/actions/runner',
            source_repo='https://github.com/firebase/genkit',
            source_digest='abc123',
            source_ref='refs/heads/main',
            source_entry_point='.github/workflows/release.yml',
            run_id='12345',
            is_ci=True,
            ci_platform='github-actions',
            invocation_id='',
            runner_environment='github-hosted',
        )
        with mock.patch.dict(
            os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'}
        ):
            v = SLSALevelValidator(target_level=3)
            r = v.validate(ctx)
            assert r.ok is False
            assert any('invocation_id' in i for i in r.details['issues'])


class TestSLSAProvenanceValidation:
    """SLSALevelValidator with provenance dict subjects."""

    def test_l3_valid_passes(self) -> None:
        """Test l3 valid passes."""
        v = SLSALevelValidator(target_level=3)
        r = v.validate(_l3_provenance_dict())
        assert r.ok is True
        assert r.details['achieved_level'] == 3

    def test_l1_minimal_passes(self) -> None:
        """Test l1 minimal passes."""
        stmt = {
            'subject': [{'name': 'foo.tar.gz', 'digest': {'sha256': 'abc'}}],
            'predicate': {
                'buildDefinition': {
                    'buildType': 'https://example.com/build/v1',
                    'externalParameters': {},
                },
                'runDetails': {
                    'builder': {'id': 'https://example.com/builder'},
                },
            },
        }
        v = SLSALevelValidator(target_level=1)
        r = v.validate(stmt)
        assert r.ok is True

    def test_l1_missing_build_type_fails(self) -> None:
        """Test l1 missing build type fails."""
        stmt = {
            'subject': [{'name': 'foo.tar.gz', 'digest': {'sha256': 'abc'}}],
            'predicate': {
                'buildDefinition': {'externalParameters': {}},
                'runDetails': {'builder': {'id': 'https://example.com'}},
            },
        }
        v = SLSALevelValidator(target_level=1)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('buildType' in i for i in r.details['issues'])

    def test_l1_empty_subjects_fails(self) -> None:
        """Test l1 empty subjects fails."""
        stmt = {
            'subject': [],
            'predicate': {
                'buildDefinition': {
                    'buildType': 'https://example.com/build/v1',
                    'externalParameters': {},
                },
                'runDetails': {'builder': {'id': 'https://example.com'}},
            },
        }
        v = SLSALevelValidator(target_level=1)
        r = v.validate(stmt)
        assert r.ok is False

    def test_l2_missing_builder_version_fails(self) -> None:
        """Test l2 missing builder version fails."""
        stmt = _l3_provenance_dict()
        del stmt['predicate']['runDetails']['builder']['version']
        v = SLSALevelValidator(target_level=2)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('version' in i for i in r.details['issues'])

    def test_l3_missing_repository_fails(self) -> None:
        """Test l3 missing repository fails."""
        stmt = _l3_provenance_dict()
        del stmt['predicate']['buildDefinition']['externalParameters']['repository']
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('repository' in i for i in r.details['issues'])

    def test_l3_missing_ref_fails(self) -> None:
        """Test l3 missing ref fails."""
        stmt = _l3_provenance_dict()
        del stmt['predicate']['buildDefinition']['externalParameters']['ref']
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('ref' in i for i in r.details['issues'])

    def test_l3_missing_source_dep_fails(self) -> None:
        """Test l3 missing source dep fails."""
        stmt = _l3_provenance_dict()
        stmt['predicate']['buildDefinition']['resolvedDependencies'] = []
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('resolvedDependencies' in i for i in r.details['issues'])

    def test_l3_missing_runner_env_fails(self) -> None:
        """Test l3 missing runner env fails."""
        stmt = _l3_provenance_dict()
        del stmt['predicate']['runDetails']['builder']['version']['runnerEnvironment']
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('runnerEnvironment' in i for i in r.details['issues'])

    def test_l3_low_recorded_level_fails(self) -> None:
        """Test l3 low recorded level fails."""
        stmt = _l3_provenance_dict()
        stmt['predicate']['buildDefinition']['internalParameters']['slsaBuildLevel'] = 2
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('slsaBuildLevel' in i for i in r.details['issues'])

    def test_l3_missing_invocation_id_fails(self) -> None:
        """Test l3 missing invocation id fails."""
        stmt = _l3_provenance_dict()
        del stmt['predicate']['runDetails']['metadata']['invocationId']
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt)
        assert r.ok is False
        assert any('invocationId' in i for i in r.details['issues'])

    def test_invalid_predicate_fails(self) -> None:
        """Test invalid predicate fails."""
        v = SLSALevelValidator(target_level=1)
        r = v.validate({'predicate': 'not a dict'})
        assert r.ok is False
        assert 'predicate' in r.message


class TestProvenanceL3Fields:
    """Verify generate_provenance includes L3 fields."""

    def test_builder_version_populated(self) -> None:
        """Test builder version populated."""
        ctx = _github_l3_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc')],
            context=ctx,
        )
        builder = stmt.predicate['runDetails']['builder']
        assert 'version' in builder
        v = builder['version']
        assert v['runnerOs'] == 'Linux'
        assert v['runnerArch'] == 'X64'
        assert v['runnerEnvironment'] == 'github-hosted'
        assert 'python' in v

    def test_slsa_build_level_in_internal_params(self) -> None:
        """Test slsa build level in internal params."""
        ctx = _github_l3_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc')],
            context=ctx,
        )
        internal = stmt.predicate['buildDefinition']['internalParameters']
        assert 'slsaBuildLevel' in internal
        assert isinstance(internal['slsaBuildLevel'], int)

    def test_byproducts_with_config_source(self) -> None:
        """Test byproducts with config source."""
        ctx = _github_l3_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc')],
            context=ctx,
            config_source='releasekit.toml',
        )
        byproducts = stmt.predicate['runDetails'].get('byproducts', [])
        assert len(byproducts) >= 1
        assert byproducts[0]['name'] == 'releasekit.toml'

    def test_byproducts_absent_without_config(self) -> None:
        """Test byproducts absent without config."""
        ctx = _github_l3_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc')],
            context=ctx,
        )
        assert 'byproducts' not in stmt.predicate['runDetails']

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_generated_provenance_passes_l3_validation(self) -> None:
        """End-to-end: generate provenance and validate it at L3."""
        ctx = _github_l3_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc123')],
            context=ctx,
            config_source='releasekit.toml',
        )
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt.to_dict())
        assert r.ok is True, f'L3 validation failed: {r.details}'

    def test_local_provenance_passes_l1_validation(self) -> None:
        """Test local provenance passes l1 validation."""
        ctx = _local_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc123')],
            context=ctx,
        )
        v = SLSALevelValidator(target_level=1)
        r = v.validate(stmt.to_dict())
        assert r.ok is True

    def test_local_provenance_fails_l3_validation(self) -> None:
        """Test local provenance fails l3 validation."""
        ctx = _local_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc123')],
            context=ctx,
        )
        v = SLSALevelValidator(target_level=3)
        r = v.validate(stmt.to_dict())
        assert r.ok is False


class TestRunValidatorsIntegration:
    """Test running SLSA validator via run_validators."""

    @mock.patch.dict(os.environ, {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://token.actions.githubusercontent.com'})
    def test_context_and_provenance_both_pass(self) -> None:
        """Test context and provenance both pass."""
        ctx = _github_l3_context()
        stmt = generate_provenance(
            subjects=[SubjectDigest(name='foo.tar.gz', sha256='abc')],
            context=ctx,
            config_source='releasekit.toml',
        )

        ctx_v = SLSALevelValidator(target_level=3, validator_id='slsa.context')
        prov_v = SLSALevelValidator(target_level=3, validator_id='slsa.provenance')

        ctx_results = run_validators([ctx_v], ctx)
        prov_results = run_validators([prov_v], stmt.to_dict())

        assert all_passed(ctx_results)
        assert all_passed(prov_results)
