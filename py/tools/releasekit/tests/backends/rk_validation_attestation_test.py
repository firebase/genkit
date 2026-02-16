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

"""Tests for PEP 740 attestation and Security Insights validators."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from releasekit.backends.validation import Validator, run_validators
from releasekit.backends.validation.attestation import (
    PEP740AttestationValidator,
    SecurityInsightsValidator,
)
from releasekit.security_insights import (
    Contact,
    SecurityInsightsConfig,
    default_security_tools,
    generate_security_insights,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_attestation() -> dict:
    """Return a minimal valid PEP 740 attestation dict."""
    return {
        'version': 1,
        'verification_material': {
            'certificate': 'base64-cert-data',
            'transparency_entries': [
                {'logIndex': 12345, 'logId': 'abc'},
            ],
        },
        'envelope': {
            'statement': 'base64-statement',
            'signature': 'base64-signature',
        },
    }


def _valid_security_insights() -> dict:
    """Return a minimal valid Security Insights v2 dict."""
    return {
        'header': {
            'schema-version': '2.0.0',
            'last-updated': '2025-01-01',
            'last-reviewed': '2025-01-01',
        },
        'project': {
            'name': 'TestProject',
            'administrators': [
                {'name': 'Admin', 'primary': True},
            ],
            'repositories': [
                {'name': 'main', 'url': 'https://github.com/test/test', 'comment': 'Main repo.'},
            ],
            'vulnerability-reporting': {
                'reports-accepted': True,
                'bug-bounty-available': False,
            },
        },
        'repository': {
            'url': 'https://github.com/test/test',
            'status': 'active',
            'accepts-change-request': True,
            'accepts-automated-change-request': True,
            'core-team': [
                {'name': 'Dev', 'primary': True},
            ],
            'license': {
                'url': 'https://github.com/test/test/blob/main/LICENSE',
                'expression': 'Apache-2.0',
            },
            'security': {
                'assessments': {
                    'self': {'comment': 'Self assessment.'},
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# PEP740AttestationValidator
# ---------------------------------------------------------------------------


class TestPEP740AttestationValidator:
    """Tests for the PEP 740 attestation validator."""

    def test_name(self) -> None:
        """Default name is schema.pep740-attestation."""
        v = PEP740AttestationValidator()
        assert v.name == 'schema.pep740-attestation'

    def test_custom_name(self) -> None:
        """Custom validator_id overrides name."""
        v = PEP740AttestationValidator(validator_id='custom.attest')
        assert v.name == 'custom.attest'

    def test_valid_attestation_dict(self) -> None:
        """Valid attestation dict passes."""
        v = PEP740AttestationValidator()
        result = v.validate(_valid_attestation())
        assert result.ok
        assert 'valid' in result.message.lower()

    def test_valid_attestation_json_string(self) -> None:
        """Valid attestation JSON string passes."""
        v = PEP740AttestationValidator()
        result = v.validate(json.dumps(_valid_attestation()))
        assert result.ok

    def test_valid_attestation_file(self, tmp_path: Path) -> None:
        """Valid attestation file passes."""
        f = tmp_path / 'test.publish.attestation'
        f.write_text(json.dumps(_valid_attestation()), encoding='utf-8')
        v = PEP740AttestationValidator()
        result = v.validate(f)
        assert result.ok

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns failure."""
        v = PEP740AttestationValidator()
        result = v.validate(tmp_path / 'nonexistent.attestation')
        assert not result.ok
        assert 'not found' in result.message.lower()

    def test_wrong_version(self) -> None:
        """Wrong version number fails."""
        data = _valid_attestation()
        data['version'] = 2
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert 'version must be 1' in result.details['errors'][0]

    def test_missing_version(self) -> None:
        """Missing version fails."""
        data = _valid_attestation()
        del data['version']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_verification_material(self) -> None:
        """Missing verification_material fails."""
        data = _valid_attestation()
        del data['verification_material']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('verification_material' in e for e in result.details['errors'])

    def test_missing_certificate(self) -> None:
        """Missing certificate fails."""
        data = _valid_attestation()
        del data['verification_material']['certificate']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('certificate' in e for e in result.details['errors'])

    def test_empty_transparency_entries(self) -> None:
        """Empty transparency_entries fails."""
        data = _valid_attestation()
        data['verification_material']['transparency_entries'] = []
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('transparency_entries' in e for e in result.details['errors'])

    def test_missing_transparency_entries(self) -> None:
        """Missing transparency_entries fails."""
        data = _valid_attestation()
        del data['verification_material']['transparency_entries']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_envelope(self) -> None:
        """Missing envelope fails."""
        data = _valid_attestation()
        del data['envelope']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('envelope' in e for e in result.details['errors'])

    def test_missing_statement(self) -> None:
        """Missing statement in envelope fails."""
        data = _valid_attestation()
        del data['envelope']['statement']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('statement' in e for e in result.details['errors'])

    def test_missing_signature(self) -> None:
        """Missing signature in envelope fails."""
        data = _valid_attestation()
        del data['envelope']['signature']
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('signature' in e for e in result.details['errors'])

    def test_unsupported_subject_type(self) -> None:
        """Unsupported subject type fails."""
        v = PEP740AttestationValidator()
        result = v.validate(42)
        assert not result.ok
        assert 'Unsupported subject type' in result.message

    def test_invalid_json_string(self) -> None:
        """Invalid JSON string fails."""
        v = PEP740AttestationValidator()
        result = v.validate('not valid json {{{')
        assert not result.ok

    def test_multiple_issues(self) -> None:
        """Multiple structural issues are all reported."""
        data = {'version': 99}
        v = PEP740AttestationValidator()
        result = v.validate(data)
        assert not result.ok
        assert len(result.details['errors']) >= 3

    def test_conforms_to_validator_protocol(self) -> None:
        """PEP740AttestationValidator conforms to Validator protocol."""
        v = PEP740AttestationValidator()
        assert isinstance(v, Validator)


# ---------------------------------------------------------------------------
# SecurityInsightsValidator
# ---------------------------------------------------------------------------


class TestSecurityInsightsValidator:
    """Tests for the Security Insights v2 validator."""

    def test_name(self) -> None:
        """Default name is schema.security-insights."""
        v = SecurityInsightsValidator()
        assert v.name == 'schema.security-insights'

    def test_custom_name(self) -> None:
        """Custom validator_id overrides name."""
        v = SecurityInsightsValidator(validator_id='custom.si')
        assert v.name == 'custom.si'

    def test_valid_dict(self) -> None:
        """Valid Security Insights dict passes."""
        v = SecurityInsightsValidator()
        result = v.validate(_valid_security_insights())
        assert result.ok
        assert 'valid' in result.message.lower()

    def test_valid_json_string(self) -> None:
        """Valid JSON string passes."""
        v = SecurityInsightsValidator()
        result = v.validate(json.dumps(_valid_security_insights()))
        assert result.ok

    def test_valid_yaml_file(self, tmp_path: Path) -> None:
        """Valid YAML file passes."""
        f = tmp_path / 'SECURITY-INSIGHTS.yml'
        f.write_text(
            yaml.dump(_valid_security_insights(), default_flow_style=False),
            encoding='utf-8',
        )
        v = SecurityInsightsValidator()
        result = v.validate(f)
        assert result.ok

    def test_valid_json_file(self, tmp_path: Path) -> None:
        """Valid JSON file passes."""
        f = tmp_path / 'si.json'
        f.write_text(json.dumps(_valid_security_insights()), encoding='utf-8')
        v = SecurityInsightsValidator()
        result = v.validate(f)
        assert result.ok

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns failure."""
        v = SecurityInsightsValidator()
        result = v.validate(tmp_path / 'nonexistent.yml')
        assert not result.ok
        assert 'not found' in result.message.lower()

    def test_missing_header(self) -> None:
        """Missing header section fails."""
        data = _valid_security_insights()
        del data['header']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok
        assert any('header' in e for e in result.details['errors'])

    def test_missing_schema_version(self) -> None:
        """Missing schema-version fails."""
        data = _valid_security_insights()
        del data['header']['schema-version']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_last_updated(self) -> None:
        """Missing last-updated fails."""
        data = _valid_security_insights()
        del data['header']['last-updated']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_last_reviewed(self) -> None:
        """Missing last-reviewed fails."""
        data = _valid_security_insights()
        del data['header']['last-reviewed']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_project(self) -> None:
        """Missing project section fails."""
        data = _valid_security_insights()
        del data['project']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_project_name(self) -> None:
        """Missing project name fails."""
        data = _valid_security_insights()
        del data['project']['name']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_empty_administrators(self) -> None:
        """Empty administrators list fails."""
        data = _valid_security_insights()
        data['project']['administrators'] = []
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_empty_repositories(self) -> None:
        """Empty repositories list fails."""
        data = _valid_security_insights()
        data['project']['repositories'] = []
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_repository_missing_name(self) -> None:
        """Repository entry missing name fails."""
        data = _valid_security_insights()
        del data['project']['repositories'][0]['name']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_repository_missing_url(self) -> None:
        """Repository entry missing URL fails."""
        data = _valid_security_insights()
        del data['project']['repositories'][0]['url']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_invalid_repository_entry(self) -> None:
        """Non-dict repository entry fails."""
        data = _valid_security_insights()
        data['project']['repositories'] = ['not-a-dict']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_vulnerability_reporting(self) -> None:
        """Missing vulnerability-reporting fails."""
        data = _valid_security_insights()
        del data['project']['vulnerability-reporting']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_reports_accepted(self) -> None:
        """Missing reports-accepted fails."""
        data = _valid_security_insights()
        del data['project']['vulnerability-reporting']['reports-accepted']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_bug_bounty_available(self) -> None:
        """Missing bug-bounty-available fails."""
        data = _valid_security_insights()
        del data['project']['vulnerability-reporting']['bug-bounty-available']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_repository_section(self) -> None:
        """Missing repository section fails."""
        data = _valid_security_insights()
        del data['repository']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_repo_url(self) -> None:
        """Missing repository URL fails."""
        data = _valid_security_insights()
        del data['repository']['url']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_repo_status(self) -> None:
        """Missing repository status fails."""
        data = _valid_security_insights()
        del data['repository']['status']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_accepts_change_request(self) -> None:
        """Missing accepts-change-request fails."""
        data = _valid_security_insights()
        del data['repository']['accepts-change-request']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_accepts_automated_change_request(self) -> None:
        """Missing accepts-automated-change-request fails."""
        data = _valid_security_insights()
        del data['repository']['accepts-automated-change-request']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_empty_core_team(self) -> None:
        """Empty core-team list fails."""
        data = _valid_security_insights()
        data['repository']['core-team'] = []
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_license(self) -> None:
        """Missing license fails."""
        data = _valid_security_insights()
        del data['repository']['license']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_license_expression(self) -> None:
        """Missing license expression fails."""
        data = _valid_security_insights()
        data['repository']['license'] = {'url': 'https://example.com/LICENSE'}
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_security(self) -> None:
        """Missing security section fails."""
        data = _valid_security_insights()
        del data['repository']['security']
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_missing_assessments(self) -> None:
        """Missing assessments fails."""
        data = _valid_security_insights()
        data['repository']['security'] = {}
        v = SecurityInsightsValidator()
        result = v.validate(data)
        assert not result.ok

    def test_unsupported_subject_type(self) -> None:
        """Unsupported subject type fails."""
        v = SecurityInsightsValidator()
        result = v.validate(42)
        assert not result.ok
        assert 'Unsupported subject type' in result.message

    def test_conforms_to_validator_protocol(self) -> None:
        """SecurityInsightsValidator conforms to Validator protocol."""
        v = SecurityInsightsValidator()
        assert isinstance(v, Validator)


# ---------------------------------------------------------------------------
# Integration: run_validators
# ---------------------------------------------------------------------------


class TestRunValidators:
    """Test that both validators work with run_validators."""

    def test_both_pass(self) -> None:
        """Attestation passes, SI fails with wrong subject."""
        results = run_validators(
            [PEP740AttestationValidator(), SecurityInsightsValidator()],
            _valid_attestation(),
        )
        # Attestation passes, SI fails (wrong subject).
        assert results[0].ok
        assert not results[1].ok

    def test_si_with_correct_subject(self) -> None:
        """SI validator passes with correct subject."""
        results = run_validators(
            [SecurityInsightsValidator()],
            _valid_security_insights(),
        )
        assert results[0].ok


# ---------------------------------------------------------------------------
# Integration: generate + validate round-trip
# ---------------------------------------------------------------------------


class TestGenerateAndValidateRoundTrip:
    """Test that generated Security Insights passes validation."""

    def test_generated_output_passes_validation(self, tmp_path: Path) -> None:
        """Generated Security Insights passes validation."""
        cfg = SecurityInsightsConfig(
            project_name='GenKit',
            repo_url='https://github.com/firebase/genkit',
            license_expression='Apache-2.0',
            administrators=[
                Contact(name='Maintainer', email='m@example.com', primary=True),
            ],
            core_team=[
                Contact(name='Dev', email='d@example.com', primary=True),
            ],
            security_tools=default_security_tools(),
        )
        result = generate_security_insights(
            cfg,
            output_path=tmp_path / 'si.yml',
        )
        assert result.generated

        # Validate the generated data.
        v = SecurityInsightsValidator()
        vr = v.validate(result.data)
        assert vr.ok, f'Validation failed: {vr.details}'

    def test_dry_run_output_passes_validation(self) -> None:
        """Dry-run output also passes validation."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            repo_url='https://github.com/test/test',
            administrators=[
                Contact(name='Admin', primary=True),
            ],
            core_team=[
                Contact(name='Dev', primary=True),
            ],
        )
        result = generate_security_insights(cfg, dry_run=True)

        v = SecurityInsightsValidator()
        vr = v.validate(result.data)
        assert vr.ok, f'Validation failed: {vr.details}'
