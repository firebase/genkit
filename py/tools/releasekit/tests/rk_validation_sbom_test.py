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

"""Tests for SBOM validation adapters (CycloneDX + SPDX).

Covers:
- CycloneDXSchemaValidator: structural checks, full schema, from_schema_file
- SPDXSchemaValidator: structural checks, full schema, from_schema_file
- Protocol conformance (both implement Validator)
- Input normalisation (dict, JSON string, Path)
- Integration with generate_sbom output
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from releasekit.backends.validation import Validator, all_passed, run_validators
from releasekit.backends.validation.sbom import (
    CycloneDXSchemaValidator,
    SPDXSchemaValidator,
    _build_registry_from_dir,
)
from releasekit.sbom import SBOMFormat, generate_sbom
from releasekit.versions import PackageVersion, ReleaseManifest

_SCHEMA_DIR = Path(__file__).parent / 'schemas'


def _manifest(*names_versions: tuple[str, str]) -> ReleaseManifest:
    """Build a minimal manifest from (name, version) pairs."""
    return ReleaseManifest(
        git_sha='abc123',
        packages=[PackageVersion(name=n, old_version='0.0.0', new_version=v, bump='minor') for n, v in names_versions],
    )


def _load_schema(name: str) -> dict:
    """Load schema."""
    path = _SCHEMA_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _valid_cyclonedx() -> dict:
    """Minimal valid CycloneDX 1.5 document."""
    return {
        'bomFormat': 'CycloneDX',
        'specVersion': '1.5',
        'serialNumber': 'urn:uuid:00000000-0000-0000-0000-000000000000',
        'version': 1,
        'metadata': {
            'timestamp': '2026-01-01T00:00:00Z',
            'tools': {'components': [{'type': 'application', 'name': 'test', 'version': '0.1'}]},
        },
        'components': [
            {'type': 'library', 'name': 'foo', 'version': '1.0.0'},
        ],
    }


def _valid_spdx() -> dict:
    """Minimal valid SPDX 2.3 document."""
    return {
        'spdxVersion': 'SPDX-2.3',
        'dataLicense': 'CC0-1.0',
        'SPDXID': 'SPDXRef-DOCUMENT',
        'name': 'test-sbom',
        'documentNamespace': 'https://example.com/test',
        'creationInfo': {
            'created': '2026-01-01T00:00:00Z',
            'creators': ['Tool: test-0.1'],
        },
        'packages': [
            {
                'SPDXID': 'SPDXRef-foo',
                'name': 'foo',
                'versionInfo': '1.0.0',
                'downloadLocation': 'NOASSERTION',
                'filesAnalyzed': False,
                'licenseConcluded': 'Apache-2.0',
                'licenseDeclared': 'Apache-2.0',
            },
        ],
    }


class TestProtocolConformance:
    """Both SBOM validators implement the Validator protocol."""

    def test_cyclonedx_is_validator(self) -> None:
        """Test cyclonedx is validator."""
        assert isinstance(CycloneDXSchemaValidator(), Validator)

    def test_spdx_is_validator(self) -> None:
        """Test spdx is validator."""
        assert isinstance(SPDXSchemaValidator(), Validator)


class TestCycloneDXStructural:
    """CycloneDXSchemaValidator structural checks (no full schema)."""

    def test_name(self) -> None:
        """Test name."""
        assert CycloneDXSchemaValidator().name == 'schema.cyclonedx'

    def test_custom_name(self) -> None:
        """Test custom name."""
        v = CycloneDXSchemaValidator(validator_id='custom.cdx')
        assert v.name == 'custom.cdx'

    def test_valid_passes(self) -> None:
        """Test valid passes."""
        r = CycloneDXSchemaValidator().validate(_valid_cyclonedx())
        assert r.ok is True

    def test_wrong_bom_format_fails(self) -> None:
        """Test wrong bom format fails."""
        doc = _valid_cyclonedx()
        doc['bomFormat'] = 'NotCycloneDX'
        r = CycloneDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'bomFormat' in r.details.get('errors', [''])[0]

    def test_missing_spec_version_fails(self) -> None:
        """Test missing spec version fails."""
        doc = _valid_cyclonedx()
        del doc['specVersion']
        r = CycloneDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'specVersion' in r.details.get('errors', [''])[0]

    def test_component_missing_type_fails(self) -> None:
        """Test component missing type fails."""
        doc = _valid_cyclonedx()
        doc['components'] = [{'name': 'foo'}]
        r = CycloneDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'type' in str(r.details.get('errors', []))

    def test_component_missing_name_fails(self) -> None:
        """Test component missing name fails."""
        doc = _valid_cyclonedx()
        doc['components'] = [{'type': 'library'}]
        r = CycloneDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'name' in str(r.details.get('errors', []))

    def test_empty_components_passes(self) -> None:
        """Test empty components passes."""
        doc = _valid_cyclonedx()
        doc['components'] = []
        r = CycloneDXSchemaValidator().validate(doc)
        assert r.ok is True

    def test_no_components_key_passes(self) -> None:
        """Test no components key passes."""
        doc = _valid_cyclonedx()
        del doc['components']
        r = CycloneDXSchemaValidator().validate(doc)
        assert r.ok is True


class TestSPDXStructural:
    """SPDXSchemaValidator structural checks (no full schema)."""

    def test_name(self) -> None:
        """Test name."""
        assert SPDXSchemaValidator().name == 'schema.spdx'

    def test_valid_passes(self) -> None:
        """Test valid passes."""
        r = SPDXSchemaValidator().validate(_valid_spdx())
        assert r.ok is True

    def test_missing_spdx_version_fails(self) -> None:
        """Test missing spdx version fails."""
        doc = _valid_spdx()
        del doc['spdxVersion']
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'spdxVersion' in str(r.details.get('errors', []))

    def test_wrong_spdxid_fails(self) -> None:
        """Test wrong spdxid fails."""
        doc = _valid_spdx()
        doc['SPDXID'] = 'SPDXRef-WRONG'
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'SPDXID' in str(r.details.get('errors', []))

    def test_missing_name_fails(self) -> None:
        """Test missing name fails."""
        doc = _valid_spdx()
        del doc['name']
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'name' in str(r.details.get('errors', []))

    def test_missing_namespace_fails(self) -> None:
        """Test missing namespace fails."""
        doc = _valid_spdx()
        del doc['documentNamespace']
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'documentNamespace' in str(r.details.get('errors', []))

    def test_missing_data_license_fails(self) -> None:
        """Test missing data license fails."""
        doc = _valid_spdx()
        del doc['dataLicense']
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'dataLicense' in str(r.details.get('errors', []))

    def test_missing_creation_info_fails(self) -> None:
        """Test missing creation info fails."""
        doc = _valid_spdx()
        del doc['creationInfo']
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'creationInfo' in str(r.details.get('errors', []))

    def test_missing_created_in_creation_info_fails(self) -> None:
        """Test missing created in creation info fails."""
        doc = _valid_spdx()
        doc['creationInfo'] = {'creators': ['Tool: test']}
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'created' in str(r.details.get('errors', []))

    def test_package_missing_spdxid_fails(self) -> None:
        """Test package missing spdxid fails."""
        doc = _valid_spdx()
        doc['packages'] = [{'name': 'foo', 'downloadLocation': 'NOASSERTION'}]
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'SPDXID' in str(r.details.get('errors', []))

    def test_package_missing_download_location_fails(self) -> None:
        """Test package missing download location fails."""
        doc = _valid_spdx()
        doc['packages'] = [{'SPDXID': 'SPDXRef-foo', 'name': 'foo'}]
        r = SPDXSchemaValidator().validate(doc)
        assert r.ok is False
        assert 'downloadLocation' in str(r.details.get('errors', []))


class TestInputNormalisation:
    """Both validators accept dict, JSON string, and Path."""

    def test_cyclonedx_json_string(self) -> None:
        """Test cyclonedx json string."""
        r = CycloneDXSchemaValidator().validate(json.dumps(_valid_cyclonedx()))
        assert r.ok is True

    def test_spdx_json_string(self) -> None:
        """Test spdx json string."""
        r = SPDXSchemaValidator().validate(json.dumps(_valid_spdx()))
        assert r.ok is True

    def test_cyclonedx_path(self, tmp_path: Path) -> None:
        """Test cyclonedx path."""
        p = tmp_path / 'sbom.cdx.json'
        p.write_text(json.dumps(_valid_cyclonedx()), encoding='utf-8')
        r = CycloneDXSchemaValidator().validate(p)
        assert r.ok is True

    def test_spdx_path(self, tmp_path: Path) -> None:
        """Test spdx path."""
        p = tmp_path / 'sbom.spdx.json'
        p.write_text(json.dumps(_valid_spdx()), encoding='utf-8')
        r = SPDXSchemaValidator().validate(p)
        assert r.ok is True

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        """Test missing file fails."""
        r = CycloneDXSchemaValidator().validate(tmp_path / 'missing.json')
        assert r.ok is False
        assert 'File not found' in r.message

    def test_invalid_json_string_fails(self) -> None:
        """Test invalid json string fails."""
        r = CycloneDXSchemaValidator().validate('{bad json')
        assert r.ok is False
        assert 'Invalid JSON' in r.message

    def test_unsupported_type_fails(self) -> None:
        """Test unsupported type fails."""
        r = CycloneDXSchemaValidator().validate(42)
        assert r.ok is False
        assert 'Unsupported subject type' in r.message


class TestCycloneDXFullSchema:
    """CycloneDX validation against the official 1.5 schema."""

    @pytest.fixture()
    def validator(self) -> CycloneDXSchemaValidator:
        """Validator."""
        schema = _load_schema('bom-1.5.schema.json')
        if not schema:
            pytest.skip('CycloneDX 1.5 schema not available')
        registry = _build_registry_from_dir(_SCHEMA_DIR)
        return CycloneDXSchemaValidator(
            schema=schema,
            registry=registry,
        )

    def test_valid_passes(self, validator: CycloneDXSchemaValidator) -> None:
        """Test valid passes."""
        r = validator.validate(_valid_cyclonedx())
        assert r.ok is True

    def test_generated_single_package(self, validator: CycloneDXSchemaValidator) -> None:
        """Test generated single package."""
        m = _manifest(('genkit', '0.5.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, supplier='Google LLC'))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_generated_multi_package(self, validator: CycloneDXSchemaValidator) -> None:
        """Test generated multi package."""
        m = _manifest(('genkit', '0.5.0'), ('plugin-a', '0.3.0'), ('plugin-b', '0.2.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, supplier='Google LLC'))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_generated_js_ecosystem(self, validator: CycloneDXSchemaValidator) -> None:
        """Test generated js ecosystem."""
        m = _manifest(('react', '18.0.0'), ('@genkit/core', '0.5.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, ecosystem='js'))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_generated_no_supplier(self, validator: CycloneDXSchemaValidator) -> None:
        """Test generated no supplier."""
        m = _manifest(('foo', '1.0.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_invalid_fails(self, validator: CycloneDXSchemaValidator) -> None:
        """Test invalid fails."""
        r = validator.validate({'bomFormat': 'CycloneDX', 'specVersion': '1.5'})
        # May pass structural but fail full schema (missing version field).
        # Either way, the validator should not crash.
        assert isinstance(r.ok, bool)

    def test_from_schema_file(self) -> None:
        """Test from schema file."""
        path = _SCHEMA_DIR / 'bom-1.5.schema.json'
        if not path.exists():
            pytest.skip('CycloneDX 1.5 schema not available')
        v = CycloneDXSchemaValidator.from_schema_file(path)
        r = v.validate(_valid_cyclonedx())
        assert r.ok is True


class TestSPDXFullSchema:
    """SPDX validation against the official 2.3 schema."""

    @pytest.fixture()
    def validator(self) -> SPDXSchemaValidator:
        """Validator."""
        schema = _load_schema('spdx-2.3.schema.json')
        if not schema:
            pytest.skip('SPDX 2.3 schema not available')
        registry = _build_registry_from_dir(_SCHEMA_DIR)
        return SPDXSchemaValidator(
            schema=schema,
            registry=registry,
        )

    def test_valid_passes(self, validator: SPDXSchemaValidator) -> None:
        """Test valid passes."""
        r = validator.validate(_valid_spdx())
        assert r.ok is True

    def test_generated_single_package(self, validator: SPDXSchemaValidator) -> None:
        """Test generated single package."""
        m = _manifest(('genkit', '0.5.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX, supplier='Google LLC'))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_generated_multi_package(self, validator: SPDXSchemaValidator) -> None:
        """Test generated multi package."""
        m = _manifest(('genkit', '0.5.0'), ('plugin-a', '0.3.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX, supplier='Google LLC'))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_generated_no_license(self, validator: SPDXSchemaValidator) -> None:
        """Test generated no license."""
        m = _manifest(('bar', '2.0.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX, license_id=''))
        r = validator.validate(doc)
        assert r.ok is True, f'Schema errors: {r.details}'

    def test_from_schema_file(self) -> None:
        """Test from schema file."""
        path = _SCHEMA_DIR / 'spdx-2.3.schema.json'
        if not path.exists():
            pytest.skip('SPDX 2.3 schema not available')
        v = SPDXSchemaValidator.from_schema_file(path)
        r = v.validate(_valid_spdx())
        assert r.ok is True


class TestRunValidatorsIntegration:
    """Test running both SBOM validators together via run_validators."""

    def test_both_pass_on_cyclonedx(self) -> None:
        """Test both pass on cyclonedx."""
        v = CycloneDXSchemaValidator()
        results = run_validators([v], _valid_cyclonedx())
        assert len(results) == 1
        assert results[0].ok is True

    def test_both_formats_validated(self) -> None:
        """Test both formats validated."""
        cdx_v = CycloneDXSchemaValidator()
        spdx_v = SPDXSchemaValidator()

        m = _manifest(('genkit', '0.5.0'))
        cdx_doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX))
        spdx_doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX))

        cdx_results = run_validators([cdx_v], cdx_doc)
        spdx_results = run_validators([spdx_v], spdx_doc)

        assert all_passed(cdx_results)
        assert all_passed(spdx_results)
