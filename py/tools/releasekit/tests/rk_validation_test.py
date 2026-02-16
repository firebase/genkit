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

"""Tests for the extensible validation framework.

Covers:
- ValidationResult dataclass and factory methods
- Validator protocol conformance
- run_validators / all_passed / errors_only / warnings_only helpers
- OIDC token validators (GitHub, GitLab, CircleCI)
- JWT claim validation (structure, expiry, issuer)
- Schema validators (provenance, generic)
- Provenance digest validator
- Auto-detection of OIDC platform
- Deduplication: provenance.has_oidc_credential delegates to validation.oidc
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from unittest import mock

import pytest
from releasekit.backends.validation import (
    ValidationResult,
    Validator,
    all_passed,
    errors_only,
    run_validators,
    warnings_only,
)
from releasekit.backends.validation.oidc import (
    CIRCLECI_OIDC_ISSUER,
    GITHUB_OIDC_ISSUER,
    GITLAB_OIDC_ISSUER,
    CircleCIOIDCValidator,
    GitHubOIDCValidator,
    GitLabOIDCValidator,
    _check_expiry,
    _check_issuer,
    _decode_jwt_claims,
    detect_oidc_validator,
    has_oidc_credential,
    validate_oidc_environment,
)
from releasekit.backends.validation.provenance import ProvenanceDigestValidator
from releasekit.backends.validation.schema import (
    JsonSchemaValidator,
    ProvenanceSchemaValidator,
)
from releasekit.provenance import has_oidc_credential as prov_has_oidc

# ── Helpers ──


def _make_jwt(claims: dict, header: dict | None = None) -> str:
    """Create a minimal unsigned JWT for testing."""
    hdr = header or {'alg': 'none', 'typ': 'JWT'}
    hdr_b64 = base64.urlsafe_b64encode(json.dumps(hdr).encode()).rstrip(b'=').decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b'=').decode()
    sig_b64 = base64.urlsafe_b64encode(b'fake-signature').rstrip(b'=').decode()
    return f'{hdr_b64}.{payload_b64}.{sig_b64}'


def _make_valid_github_jwt() -> str:
    """Create a valid GitHub Actions OIDC JWT."""
    return _make_jwt({
        'iss': GITHUB_OIDC_ISSUER,
        'aud': 'sigstore',
        'sub': 'repo:firebase/genkit:ref:refs/heads/main',
        'exp': int(time.time()) + 600,
    })


def _make_expired_jwt(issuer: str = GITHUB_OIDC_ISSUER) -> str:
    """Create an expired JWT."""
    return _make_jwt({
        'iss': issuer,
        'exp': int(time.time()) - 60,
    })


def _make_wrong_issuer_jwt() -> str:
    """Create a JWT with wrong issuer."""
    return _make_jwt({
        'iss': 'https://evil.example.com',
        'exp': int(time.time()) + 600,
    })


# ── ValidationResult ──


class TestValidationResult:
    """Tests for ValidationResult dataclass and factory methods."""

    def test_passed_factory(self) -> None:
        r = ValidationResult.passed('test.validator', 'All good')
        assert r.ok is True
        assert r.validator_name == 'test.validator'
        assert r.message == 'All good'
        assert r.severity == 'info'

    def test_failed_factory(self) -> None:
        r = ValidationResult.failed('test.validator', 'Bad', hint='Fix it')
        assert r.ok is False
        assert r.message == 'Bad'
        assert r.hint == 'Fix it'
        assert r.severity == 'error'

    def test_warning_factory(self) -> None:
        r = ValidationResult.warning('test.validator', 'Hmm', hint='Consider')
        assert r.ok is True
        assert r.severity == 'warning'
        assert r.hint == 'Consider'

    def test_details_default_empty(self) -> None:
        r = ValidationResult.passed('x')
        assert r.details == {}

    def test_details_preserved(self) -> None:
        r = ValidationResult.failed('x', 'err', details={'key': 'val'})
        assert r.details == {'key': 'val'}

    def test_frozen(self) -> None:
        r = ValidationResult.passed('x')
        with pytest.raises(AttributeError):
            r.ok = False  # type: ignore[misc]


# ── Validator protocol ──


class TestValidatorProtocol:
    """Tests for Validator protocol conformance."""

    def test_github_oidc_is_validator(self) -> None:
        assert isinstance(GitHubOIDCValidator(), Validator)

    def test_gitlab_oidc_is_validator(self) -> None:
        assert isinstance(GitLabOIDCValidator(), Validator)

    def test_circleci_oidc_is_validator(self) -> None:
        assert isinstance(CircleCIOIDCValidator(), Validator)

    def test_provenance_schema_is_validator(self) -> None:
        assert isinstance(ProvenanceSchemaValidator(), Validator)

    def test_json_schema_is_validator(self) -> None:
        assert isinstance(JsonSchemaValidator(schema={}), Validator)

    def test_provenance_digest_is_validator(self) -> None:
        assert isinstance(ProvenanceDigestValidator(), Validator)


# ── run_validators / helpers ──


class TestRunValidators:
    """Tests for run_validators and helper functions."""

    def test_run_validators_collects_results(self) -> None:
        v1 = ProvenanceSchemaValidator()
        # Pass a valid minimal statement.
        stmt = {
            '_type': 'https://in-toto.io/Statement/v1',
            'subject': [{'name': 'a.tar.gz', 'digest': {'sha256': 'abc'}}],
            'predicateType': 'https://slsa.dev/provenance/v1',
            'predicate': {
                'buildDefinition': {
                    'buildType': 'https://firebase.google.com/releasekit/v1',
                    'externalParameters': {},
                    'internalParameters': {},
                },
                'runDetails': {'builder': {'id': 'local://test'}},
            },
        }
        results = run_validators([v1], stmt)
        assert len(results) == 1
        assert results[0].ok is True

    def test_all_passed_true(self) -> None:
        results = [
            ValidationResult.passed('a'),
            ValidationResult.warning('b', 'warn'),
        ]
        assert all_passed(results) is True

    def test_all_passed_false(self) -> None:
        results = [
            ValidationResult.passed('a'),
            ValidationResult.failed('b', 'err'),
        ]
        assert all_passed(results) is False

    def test_errors_only(self) -> None:
        results = [
            ValidationResult.passed('a'),
            ValidationResult.failed('b', 'err'),
            ValidationResult.warning('c', 'warn'),
        ]
        errs = errors_only(results)
        assert len(errs) == 1
        assert errs[0].validator_name == 'b'

    def test_warnings_only(self) -> None:
        results = [
            ValidationResult.passed('a'),
            ValidationResult.failed('b', 'err'),
            ValidationResult.warning('c', 'warn'),
        ]
        warns = warnings_only(results)
        assert len(warns) == 1
        assert warns[0].validator_name == 'c'


# ── JWT helpers ──


class TestJWTHelpers:
    """Tests for JWT decoding and claim validation helpers."""

    def test_decode_valid_jwt(self) -> None:
        token = _make_jwt({'iss': 'test', 'sub': 'user'})
        claims = _decode_jwt_claims(token)
        assert claims is not None
        assert claims['iss'] == 'test'
        assert claims['sub'] == 'user'

    def test_decode_malformed_jwt(self) -> None:
        assert _decode_jwt_claims('not-a-jwt') is None
        assert _decode_jwt_claims('a.b') is None
        assert _decode_jwt_claims('') is None

    def test_decode_invalid_base64(self) -> None:
        assert _decode_jwt_claims('a.!!!invalid!!!.c') is None

    def test_check_expiry_valid(self) -> None:
        claims = {'exp': int(time.time()) + 600}
        ok, msg = _check_expiry(claims)
        assert ok is True
        assert 'valid for' in msg

    def test_check_expiry_expired(self) -> None:
        claims = {'exp': int(time.time()) - 60}
        ok, msg = _check_expiry(claims)
        assert ok is False
        assert 'expired' in msg

    def test_check_expiry_no_exp(self) -> None:
        ok, msg = _check_expiry({})
        assert ok is True
        assert 'does not expire' in msg

    def test_check_expiry_invalid_exp(self) -> None:
        ok, msg = _check_expiry({'exp': 'not-a-number'})
        assert ok is False
        assert 'Invalid exp' in msg

    def test_check_issuer_match(self) -> None:
        ok, msg = _check_issuer({'iss': GITHUB_OIDC_ISSUER}, GITHUB_OIDC_ISSUER)
        assert ok is True

    def test_check_issuer_prefix_match(self) -> None:
        ok, msg = _check_issuer(
            {'iss': 'https://oidc.circleci.com/org/abc123'},
            CIRCLECI_OIDC_ISSUER,
        )
        assert ok is True

    def test_check_issuer_mismatch(self) -> None:
        ok, msg = _check_issuer({'iss': 'https://evil.com'}, GITHUB_OIDC_ISSUER)
        assert ok is False
        assert 'Unexpected issuer' in msg

    def test_check_issuer_missing(self) -> None:
        ok, msg = _check_issuer({}, GITHUB_OIDC_ISSUER)
        assert ok is False
        assert 'Missing iss' in msg


# ── GitHub OIDC Validator ──


class TestGitHubOIDCValidator:
    """Tests for GitHubOIDCValidator."""

    def test_name(self) -> None:
        assert GitHubOIDCValidator().name == 'oidc.github'

    def test_no_env_var_fails(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            r = GitHubOIDCValidator().validate()
        assert r.ok is False
        assert 'ACTIONS_ID_TOKEN_REQUEST_URL' in r.message
        assert 'id-token: write' in r.hint

    def test_env_var_set_passes(self) -> None:
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com/token'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitHubOIDCValidator().validate()
        assert r.ok is True
        assert 'available' in r.message

    def test_valid_token_passes(self) -> None:
        token = _make_valid_github_jwt()
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com/token'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitHubOIDCValidator().validate(token)
        assert r.ok is True
        assert 'valid' in r.message

    def test_expired_token_fails(self) -> None:
        token = _make_expired_jwt(GITHUB_OIDC_ISSUER)
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com/token'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitHubOIDCValidator().validate(token)
        assert r.ok is False
        assert 'expired' in r.message

    def test_wrong_issuer_fails(self) -> None:
        token = _make_wrong_issuer_jwt()
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com/token'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitHubOIDCValidator().validate(token)
        assert r.ok is False
        assert 'issuer mismatch' in r.message

    def test_malformed_token_fails(self) -> None:
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com/token'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitHubOIDCValidator().validate('not-a-jwt')
        assert r.ok is False
        assert 'Malformed JWT' in r.message


# ── GitLab OIDC Validator ──


class TestGitLabOIDCValidator:
    """Tests for GitLabOIDCValidator."""

    def test_name(self) -> None:
        assert GitLabOIDCValidator().name == 'oidc.gitlab'

    def test_no_env_var_fails(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            r = GitLabOIDCValidator().validate()
        assert r.ok is False
        assert 'CI_JOB_JWT' in r.message

    def test_jwt_v2_env_var(self) -> None:
        token = _make_jwt({
            'iss': GITLAB_OIDC_ISSUER,
            'exp': int(time.time()) + 600,
        })
        env = {'CI_JOB_JWT_V2': token}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitLabOIDCValidator().validate()
        assert r.ok is True

    def test_jwt_v1_fallback(self) -> None:
        token = _make_jwt({
            'iss': GITLAB_OIDC_ISSUER,
            'exp': int(time.time()) + 600,
        })
        env = {'CI_JOB_JWT': token}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitLabOIDCValidator().validate()
        assert r.ok is True

    def test_expired_token_fails(self) -> None:
        token = _make_expired_jwt(GITLAB_OIDC_ISSUER)
        with mock.patch.dict(os.environ, {}, clear=True):
            r = GitLabOIDCValidator().validate(token)
        assert r.ok is False
        assert 'expired' in r.message

    def test_self_hosted_issuer(self) -> None:
        """Self-hosted GitLab uses CI_SERVER_URL as issuer."""
        token = _make_jwt({
            'iss': 'https://gitlab.mycompany.com',
            'exp': int(time.time()) + 600,
        })
        env = {'CI_SERVER_URL': 'https://gitlab.mycompany.com'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = GitLabOIDCValidator().validate(token)
        assert r.ok is True


# ── CircleCI OIDC Validator ──


class TestCircleCIOIDCValidator:
    """Tests for CircleCIOIDCValidator."""

    def test_name(self) -> None:
        assert CircleCIOIDCValidator().name == 'oidc.circleci'

    def test_no_env_var_fails(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            r = CircleCIOIDCValidator().validate()
        assert r.ok is False
        assert 'CIRCLE_OIDC_TOKEN_V2' in r.message

    def test_valid_token_passes(self) -> None:
        token = _make_jwt({
            'iss': 'https://oidc.circleci.com/org/abc123',
            'exp': int(time.time()) + 600,
        })
        env = {'CIRCLE_OIDC_TOKEN_V2': token}
        with mock.patch.dict(os.environ, env, clear=True):
            r = CircleCIOIDCValidator().validate()
        assert r.ok is True

    def test_expired_token_fails(self) -> None:
        token = _make_expired_jwt('https://oidc.circleci.com/org/abc123')
        with mock.patch.dict(os.environ, {}, clear=True):
            r = CircleCIOIDCValidator().validate(token)
        assert r.ok is False
        assert 'expired' in r.message


# ── Auto-detection ──


class TestDetectOIDCValidator:
    """Tests for detect_oidc_validator()."""

    def test_github(self) -> None:
        env = {'GITHUB_ACTIONS': 'true'}
        with mock.patch.dict(os.environ, env, clear=True):
            v = detect_oidc_validator()
        assert isinstance(v, GitHubOIDCValidator)

    def test_gitlab(self) -> None:
        env = {'GITLAB_CI': 'true'}
        with mock.patch.dict(os.environ, env, clear=True):
            v = detect_oidc_validator()
        assert isinstance(v, GitLabOIDCValidator)

    def test_circleci(self) -> None:
        env = {'CIRCLECI': 'true'}
        with mock.patch.dict(os.environ, env, clear=True):
            v = detect_oidc_validator()
        assert isinstance(v, CircleCIOIDCValidator)

    def test_no_ci(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            v = detect_oidc_validator()
        assert v is None


class TestValidateOIDCEnvironment:
    """Tests for validate_oidc_environment()."""

    def test_local_passes(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            r = validate_oidc_environment()
        assert r.ok is True
        assert 'local' in r.message.lower() or 'Not in CI' in r.message

    def test_ci_no_oidc_warns(self) -> None:
        env = {'CI': 'true'}
        with mock.patch.dict(os.environ, env, clear=True):
            r = validate_oidc_environment()
        assert r.severity == 'warning'
        assert 'OIDC' in r.message

    def test_github_with_oidc_passes(self) -> None:
        env = {
            'CI': 'true',
            'GITHUB_ACTIONS': 'true',
            'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com/token',
        }
        with mock.patch.dict(os.environ, env, clear=True):
            r = validate_oidc_environment()
        assert r.ok is True


class TestHasOIDCCredential:
    """Tests for the canonical has_oidc_credential()."""

    def test_no_credential(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            assert has_oidc_credential() is False

    def test_github_credential(self) -> None:
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert has_oidc_credential() is True

    def test_gitlab_v2_credential(self) -> None:
        env = {'CI_JOB_JWT_V2': 'some-token'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert has_oidc_credential() is True

    def test_gitlab_v1_credential(self) -> None:
        env = {'CI_JOB_JWT': 'some-token'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert has_oidc_credential() is True

    def test_circleci_credential(self) -> None:
        env = {'CIRCLE_OIDC_TOKEN_V2': 'some-token'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert has_oidc_credential() is True


class TestProvenanceHasOIDCDelegates:
    """Verify provenance.has_oidc_credential delegates to validation.oidc."""

    def test_delegates(self) -> None:
        env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.com'}
        with mock.patch.dict(os.environ, env, clear=True):
            assert prov_has_oidc() is True
        with mock.patch.dict(os.environ, {}, clear=True):
            assert prov_has_oidc() is False


# ── Schema validators ──


class TestProvenanceSchemaValidator:
    """Tests for ProvenanceSchemaValidator."""

    def test_name(self) -> None:
        assert ProvenanceSchemaValidator().name == 'schema.provenance'

    def test_valid_statement_passes(self) -> None:
        stmt = {
            '_type': 'https://in-toto.io/Statement/v1',
            'subject': [{'name': 'a.tar.gz', 'digest': {'sha256': 'abc'}}],
            'predicateType': 'https://slsa.dev/provenance/v1',
            'predicate': {
                'buildDefinition': {
                    'buildType': 'https://firebase.google.com/releasekit/v1',
                    'externalParameters': {},
                    'internalParameters': {},
                },
                'runDetails': {'builder': {'id': 'local://test'}},
            },
        }
        r = ProvenanceSchemaValidator().validate(stmt)
        assert r.ok is True

    def test_invalid_statement_fails(self) -> None:
        r = ProvenanceSchemaValidator().validate({'bad': 'data'})
        assert r.ok is False
        assert 'schema violation' in r.message


class TestJsonSchemaValidator:
    """Tests for JsonSchemaValidator."""

    def test_name(self) -> None:
        assert JsonSchemaValidator(schema={}, validator_id='schema.test').name == 'schema.test'

    def test_no_schema_fails(self) -> None:
        r = JsonSchemaValidator().validate({'any': 'data'})
        assert r.ok is False
        assert 'No schema' in r.message

    def test_valid_data_passes(self) -> None:
        schema = {
            'type': 'object',
            'required': ['name'],
            'properties': {'name': {'type': 'string'}},
        }
        r = JsonSchemaValidator(schema=schema, validator_id='test').validate({'name': 'hello'})
        assert r.ok is True

    def test_invalid_data_fails(self) -> None:
        schema = {
            'type': 'object',
            'required': ['name'],
            'properties': {'name': {'type': 'string'}},
        }
        r = JsonSchemaValidator(schema=schema, validator_id='test').validate({})
        assert r.ok is False

    def test_json_string_input(self) -> None:
        schema = {
            'type': 'object',
            'required': ['name'],
            'properties': {'name': {'type': 'string'}},
        }
        r = JsonSchemaValidator(schema=schema, validator_id='test').validate('{"name": "hello"}')
        assert r.ok is True

    def test_file_input(self, tmp_path: Path) -> None:
        schema = {
            'type': 'object',
            'required': ['name'],
            'properties': {'name': {'type': 'string'}},
        }
        p = tmp_path / 'data.json'
        p.write_text('{"name": "hello"}', encoding='utf-8')
        r = JsonSchemaValidator(schema=schema, validator_id='test').validate(p)
        assert r.ok is True

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        schema = {'type': 'object'}
        r = JsonSchemaValidator(schema=schema, validator_id='test').validate(tmp_path / 'missing.json')
        assert r.ok is False
        assert 'File not found' in r.message

    def test_invalid_json_fails(self) -> None:
        schema = {'type': 'object'}
        r = JsonSchemaValidator(schema=schema, validator_id='test').validate('{bad')
        assert r.ok is False
        assert 'Invalid JSON' in r.message


# ── Provenance digest validator ──


class TestProvenanceDigestValidator:
    """Tests for ProvenanceDigestValidator."""

    def test_name(self) -> None:
        assert ProvenanceDigestValidator().name == 'provenance.digest'

    def test_non_dict_subject_fails(self) -> None:
        r = ProvenanceDigestValidator().validate('not a dict')
        assert r.ok is False
        assert 'must be a dict' in r.message

    def test_missing_artifact_path_fails(self) -> None:
        r = ProvenanceDigestValidator().validate({'provenance_path': Path('/tmp/x')})
        assert r.ok is False
        assert 'artifact_path' in r.message

    def test_missing_provenance_path_fails(self) -> None:
        r = ProvenanceDigestValidator().validate({'artifact_path': Path('/tmp/x')})
        assert r.ok is False
        assert 'provenance_path' in r.message

    def test_valid_digest_passes(self, tmp_path: Path) -> None:
        """Create an artifact and provenance, verify they match."""
        artifact = tmp_path / 'pkg-0.1.0.tar.gz'
        artifact.write_bytes(b'artifact content')
        sha = hashlib.sha256(b'artifact content').hexdigest()

        stmt = {
            '_type': 'https://in-toto.io/Statement/v1',
            'subject': [{'name': 'pkg-0.1.0.tar.gz', 'digest': {'sha256': sha}}],
            'predicateType': 'https://slsa.dev/provenance/v1',
            'predicate': {
                'buildDefinition': {
                    'buildType': 'test',
                    'externalParameters': {},
                },
                'runDetails': {'builder': {'id': 'test'}},
            },
        }
        prov = tmp_path / 'provenance.intoto.jsonl'
        prov.write_text(json.dumps(stmt), encoding='utf-8')

        r = ProvenanceDigestValidator().validate({
            'artifact_path': artifact,
            'provenance_path': prov,
        })
        assert r.ok is True
        assert 'verified' in r.message

    def test_tampered_artifact_fails(self, tmp_path: Path) -> None:
        """Tampered artifact should fail digest verification."""
        artifact = tmp_path / 'pkg-0.1.0.tar.gz'
        artifact.write_bytes(b'original content')
        sha = hashlib.sha256(b'original content').hexdigest()

        stmt = {
            '_type': 'https://in-toto.io/Statement/v1',
            'subject': [{'name': 'pkg-0.1.0.tar.gz', 'digest': {'sha256': sha}}],
            'predicateType': 'https://slsa.dev/provenance/v1',
            'predicate': {
                'buildDefinition': {
                    'buildType': 'test',
                    'externalParameters': {},
                },
                'runDetails': {'builder': {'id': 'test'}},
            },
        }
        prov = tmp_path / 'provenance.intoto.jsonl'
        prov.write_text(json.dumps(stmt), encoding='utf-8')

        # Tamper with the artifact.
        artifact.write_bytes(b'tampered content')

        r = ProvenanceDigestValidator().validate({
            'artifact_path': artifact,
            'provenance_path': prov,
        })
        assert r.ok is False
        assert 'mismatch' in r.message.lower() or 'not found' in r.details.get('reason', '')
