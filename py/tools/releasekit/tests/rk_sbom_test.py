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

"""Tests for releasekit.sbom — SBOM generation (CycloneDX + SPDX)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import referencing
from releasekit.sbom import (
    SBOMComponent,
    SBOMFormat,
    _build_components,
    _make_purl,
    _render_cyclonedx,
    _render_spdx,
    generate_sbom,
    write_sbom,
)
from releasekit.versions import PackageVersion, ReleaseManifest


def _manifest(*names_versions: tuple[str, str]) -> ReleaseManifest:
    """Build a minimal manifest from (name, version) pairs."""
    return ReleaseManifest(
        git_sha='abc123',
        packages=[
            PackageVersion(
                name=n,
                old_version='0.0.0',
                new_version=v,
                bump='minor',
            )
            for n, v in names_versions
        ],
    )


class TestSBOMFormat:
    """Tests for SBOMFormat enum."""

    def test_cyclonedx_extension(self) -> None:
        """CycloneDX extension is .cdx.json."""
        assert SBOMFormat.CYCLONEDX.extension == '.cdx.json'

    def test_spdx_extension(self) -> None:
        """SPDX extension is .spdx.json."""
        assert SBOMFormat.SPDX.extension == '.spdx.json'

    def test_values(self) -> None:
        """Enum values are correct strings."""
        assert SBOMFormat.CYCLONEDX.value == 'cyclonedx'
        assert SBOMFormat.SPDX.value == 'spdx'


class TestSBOMComponent:
    """Tests for SBOMComponent dataclass."""

    def test_defaults(self) -> None:
        """Default fields are empty."""
        comp = SBOMComponent(name='foo', version='1.0.0')
        assert comp.purl == ''
        assert comp.license_id == ''
        assert comp.supplier == ''
        assert comp.description == ''
        assert comp.dependencies == []

    def test_frozen(self) -> None:
        """Component is immutable."""
        comp = SBOMComponent(name='foo', version='1.0.0')
        try:
            comp.name = 'bar'  # type: ignore[misc]
            raise AssertionError('Should be frozen')
        except AttributeError:
            pass


class TestMakePurl:
    """Tests for _make_purl helper."""

    def test_python_purl(self) -> None:
        """Python purl normalizes name."""
        assert _make_purl('my-package', '1.2.3') == 'pkg:pypi/my_package@1.2.3'

    def test_python_purl_explicit(self) -> None:
        """Explicit python ecosystem."""
        assert _make_purl('Foo', '0.1.0', 'python') == 'pkg:pypi/foo@0.1.0'

    def test_npm_purl(self) -> None:
        """Npm purl for unscoped package."""
        assert _make_purl('react', '18.0.0', 'js') == 'pkg:npm/react@18.0.0'

    def test_npm_scoped_purl(self) -> None:
        """Npm purl for scoped package."""
        assert _make_purl('@genkit/core', '0.5.0', 'npm') == 'pkg:npm/@genkit/core@0.5.0'

    def test_pnpm_ecosystem(self) -> None:
        """Pnpm maps to npm purl."""
        assert _make_purl('pkg', '1.0.0', 'pnpm') == 'pkg:npm/pkg@1.0.0'

    def test_javascript_ecosystem(self) -> None:
        """Javascript maps to npm purl."""
        assert _make_purl('pkg', '1.0.0', 'javascript') == 'pkg:npm/pkg@1.0.0'


class TestBuildComponents:
    """Tests for _build_components."""

    def test_basic(self) -> None:
        """Builds components from manifest."""
        m = _manifest(('genkit', '0.5.0'), ('plugin-a', '0.3.0'))
        comps = _build_components(m, supplier='Google LLC')
        assert len(comps) == 2
        assert comps[0].name == 'genkit'
        assert comps[0].version == '0.5.0'
        assert comps[0].supplier == 'Google LLC'
        assert comps[0].license_id == 'Apache-2.0'
        assert 'pkg:pypi/genkit@0.5.0' == comps[0].purl

    def test_uses_old_version_when_no_new(self) -> None:
        """Falls back to old_version when new_version is empty."""
        m = ReleaseManifest(
            git_sha='abc',
            packages=[
                PackageVersion(
                    name='foo',
                    old_version='1.0.0',
                    new_version='',
                    bump='',
                ),
            ],
        )
        comps = _build_components(m)
        assert comps[0].version == '1.0.0'

    def test_js_ecosystem(self) -> None:
        """JS ecosystem generates npm purls."""
        m = _manifest(('react', '18.0.0'))
        comps = _build_components(m, ecosystem='js')
        assert comps[0].purl == 'pkg:npm/react@18.0.0'


class TestRenderCycloneDX:
    """Tests for CycloneDX rendering."""

    def test_basic_structure(self) -> None:
        """CycloneDX document has correct top-level keys."""
        comps = [SBOMComponent(name='foo', version='1.0.0', purl='pkg:pypi/foo@1.0.0')]
        doc = _render_cyclonedx(
            comps,
            serial_number='urn:uuid:test-123',
            timestamp='2026-01-01T00:00:00Z',
        )
        assert doc['bomFormat'] == 'CycloneDX'
        assert doc['specVersion'] == '1.5'
        assert doc['serialNumber'] == 'urn:uuid:test-123'
        assert doc['metadata']['timestamp'] == '2026-01-01T00:00:00Z'
        assert len(doc['components']) == 1

    def test_component_fields(self) -> None:
        """Component entry includes purl, license, supplier, description."""
        comps = [
            SBOMComponent(
                name='bar',
                version='2.0.0',
                purl='pkg:pypi/bar@2.0.0',
                license_id='MIT',
                supplier='Acme',
                description='A bar library',
            )
        ]
        doc = _render_cyclonedx(comps, serial_number='urn:uuid:x', timestamp='t')
        entry = doc['components'][0]
        assert entry['name'] == 'bar'
        assert entry['version'] == '2.0.0'
        assert entry['purl'] == 'pkg:pypi/bar@2.0.0'
        assert entry['bom-ref'] == 'pkg:pypi/bar@2.0.0'
        assert entry['licenses'] == [{'license': {'id': 'MIT'}}]
        assert entry['supplier'] == {'name': 'Acme'}
        assert entry['description'] == 'A bar library'

    def test_minimal_component(self) -> None:
        """Component without optional fields omits them."""
        comps = [SBOMComponent(name='x', version='0.1.0')]
        doc = _render_cyclonedx(comps, serial_number='urn:uuid:y', timestamp='t')
        entry = doc['components'][0]
        assert 'purl' not in entry
        assert 'licenses' not in entry
        assert 'supplier' not in entry
        assert 'description' not in entry

    def test_auto_serial_and_timestamp(self) -> None:
        """Auto-generates serial number and timestamp when not provided."""
        comps = [SBOMComponent(name='x', version='0.1.0')]
        doc = _render_cyclonedx(comps)
        assert doc['serialNumber'].startswith('urn:uuid:')
        assert doc['metadata']['timestamp'] != ''


class TestRenderSPDX:
    """Tests for SPDX rendering."""

    def test_basic_structure(self) -> None:
        """SPDX document has correct top-level keys."""
        comps = [SBOMComponent(name='foo', version='1.0.0', purl='pkg:pypi/foo@1.0.0')]
        doc = _render_spdx(
            comps,
            document_namespace='https://example.com/test',
            timestamp='2026-01-01T00:00:00Z',
        )
        assert doc['spdxVersion'] == 'SPDX-2.3'
        assert doc['dataLicense'] == 'CC0-1.0'
        assert doc['SPDXID'] == 'SPDXRef-DOCUMENT'
        assert doc['documentNamespace'] == 'https://example.com/test'
        assert len(doc['packages']) == 1

    def test_package_with_license(self) -> None:
        """Package with license_id sets licenseConcluded/Declared."""
        comps = [SBOMComponent(name='bar', version='2.0.0', license_id='MIT')]
        doc = _render_spdx(comps, document_namespace='ns', timestamp='t')
        pkg = doc['packages'][0]
        assert pkg['licenseConcluded'] == 'MIT'
        assert pkg['licenseDeclared'] == 'MIT'

    def test_package_without_license(self) -> None:
        """Package without license_id uses NOASSERTION."""
        comps = [SBOMComponent(name='bar', version='2.0.0')]
        doc = _render_spdx(comps, document_namespace='ns', timestamp='t')
        pkg = doc['packages'][0]
        assert pkg['licenseConcluded'] == 'NOASSERTION'
        assert pkg['licenseDeclared'] == 'NOASSERTION'

    def test_package_with_supplier(self) -> None:
        """Package with supplier includes Organization prefix."""
        comps = [SBOMComponent(name='x', version='1.0.0', supplier='Google')]
        doc = _render_spdx(comps, document_namespace='ns', timestamp='t')
        assert doc['packages'][0]['supplier'] == 'Organization: Google'

    def test_package_with_purl(self) -> None:
        """Package with purl includes externalRefs."""
        comps = [SBOMComponent(name='x', version='1.0.0', purl='pkg:pypi/x@1.0.0')]
        doc = _render_spdx(comps, document_namespace='ns', timestamp='t')
        refs = doc['packages'][0]['externalRefs']
        assert len(refs) == 1
        assert refs[0]['referenceType'] == 'purl'
        assert refs[0]['referenceLocator'] == 'pkg:pypi/x@1.0.0'

    def test_spdx_id_sanitization(self) -> None:
        """SPDX ID sanitizes special characters."""
        comps = [SBOMComponent(name='@scope/pkg.name', version='1.0.0')]
        doc = _render_spdx(comps, document_namespace='ns', timestamp='t')
        spdx_id = doc['packages'][0]['SPDXID']
        assert '/' not in spdx_id
        assert '@' not in spdx_id

    def test_auto_namespace_and_timestamp(self) -> None:
        """Auto-generates namespace and timestamp when not provided."""
        comps = [SBOMComponent(name='x', version='0.1.0')]
        doc = _render_spdx(comps)
        assert 'spdx.org' in doc['documentNamespace']
        assert doc['creationInfo']['created'] != ''


class TestGenerateSBOM:
    """Tests for generate_sbom."""

    def test_cyclonedx_json(self) -> None:
        """Generates valid CycloneDX JSON."""
        m = _manifest(('genkit', '0.5.0'))
        result = generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, supplier='Google')
        doc = json.loads(result)
        assert doc['bomFormat'] == 'CycloneDX'
        assert len(doc['components']) == 1

    def test_spdx_json(self) -> None:
        """Generates valid SPDX JSON."""
        m = _manifest(('genkit', '0.5.0'))
        result = generate_sbom(m, fmt=SBOMFormat.SPDX, supplier='Google')
        doc = json.loads(result)
        assert doc['spdxVersion'] == 'SPDX-2.3'
        assert len(doc['packages']) == 1

    def test_default_format_is_cyclonedx(self) -> None:
        """Default format is CycloneDX."""
        m = _manifest(('foo', '1.0.0'))
        result = generate_sbom(m)
        doc = json.loads(result)
        assert doc['bomFormat'] == 'CycloneDX'

    def test_multiple_packages(self) -> None:
        """Multiple packages appear in SBOM."""
        m = _manifest(('a', '1.0.0'), ('b', '2.0.0'), ('c', '3.0.0'))
        result = generate_sbom(m, fmt=SBOMFormat.CYCLONEDX)
        doc = json.loads(result)
        assert len(doc['components']) == 3

    def test_js_ecosystem(self) -> None:
        """JS ecosystem generates npm purls."""
        m = _manifest(('react', '18.0.0'))
        result = generate_sbom(m, ecosystem='js')
        json.loads(result)
        assert 'pkg:npm/react@18.0.0' in result


class TestWriteSBOM:
    """Tests for write_sbom."""

    def test_writes_cyclonedx_file(self, tmp_path: Path) -> None:
        """Writes CycloneDX SBOM to disk."""
        m = _manifest(('genkit', '0.5.0'))
        out = write_sbom(m, tmp_path, fmt=SBOMFormat.CYCLONEDX)
        assert out.exists()
        assert out.name == 'sbom.cdx.json'
        doc = json.loads(out.read_text())
        assert doc['bomFormat'] == 'CycloneDX'

    def test_writes_spdx_file(self, tmp_path: Path) -> None:
        """Writes SPDX SBOM to disk."""
        m = _manifest(('genkit', '0.5.0'))
        out = write_sbom(m, tmp_path, fmt=SBOMFormat.SPDX)
        assert out.exists()
        assert out.name == 'sbom.spdx.json'
        doc = json.loads(out.read_text())
        assert doc['spdxVersion'] == 'SPDX-2.3'

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        """Creates output directory if it doesn't exist."""
        m = _manifest(('foo', '1.0.0'))
        nested = tmp_path / 'a' / 'b' / 'c'
        out = write_sbom(m, nested)
        assert out.exists()
        assert nested.is_dir()

    def test_supplier_propagates(self, tmp_path: Path) -> None:
        """Supplier is included in the SBOM."""
        m = _manifest(('foo', '1.0.0'))
        out = write_sbom(m, tmp_path, supplier='Acme Corp')
        doc = json.loads(out.read_text())
        comp = doc['components'][0]
        assert comp['supplier'] == {'name': 'Acme Corp'}


_SCHEMA_DIR = Path(__file__).parent / 'schemas'


def _build_schema_registry() -> referencing.Registry:
    """Build a referencing.Registry from all .schema.json files in the schemas dir.

    This allows jsonschema to resolve $ref links between sibling schema files
    (e.g., bom-1.5.schema.json references spdx.schema.json).
    """
    registry = referencing.Registry()
    for path in _SCHEMA_DIR.glob('*.schema.json'):
        contents = json.loads(path.read_text(encoding='utf-8'))
        resource = referencing.Resource.from_contents(contents)
        # Register under the filename so that relative $ref resolves.
        registry = registry.with_resource(path.name, resource)
        # Also register under the $id if present, for absolute $ref.
        if '$id' in contents:
            registry = registry.with_resource(contents['$id'], resource)
    return registry


_SCHEMA_REGISTRY = _build_schema_registry()


def _load_schema(name: str) -> dict:
    """Load a JSON schema from the schemas directory."""
    path = _SCHEMA_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


class TestCycloneDXSchemaValidation:
    """Validate generated CycloneDX output against the official 1.5 schema."""

    def test_single_package(self) -> None:
        """Single-package SBOM validates against CycloneDX 1.5 schema."""
        schema = _load_schema('bom-1.5.schema.json')
        if not schema:
            return  # Schema file not available; skip gracefully.
        m = _manifest(('genkit', '0.5.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, supplier='Google LLC'))
        jsonschema.validate(doc, schema, registry=_SCHEMA_REGISTRY)

    def test_multiple_packages(self) -> None:
        """Multi-package SBOM validates against CycloneDX 1.5 schema."""
        schema = _load_schema('bom-1.5.schema.json')
        if not schema:
            return
        m = _manifest(
            ('genkit', '0.5.0'),
            ('genkit-plugin-google-genai', '0.5.0'),
            ('genkit-plugin-vertex-ai', '0.5.0'),
        )
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, supplier='Google LLC'))
        jsonschema.validate(doc, schema, registry=_SCHEMA_REGISTRY)

    def test_minimal_no_supplier(self) -> None:
        """Minimal SBOM without supplier validates."""
        schema = _load_schema('bom-1.5.schema.json')
        if not schema:
            return
        m = _manifest(('foo', '1.0.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX))
        jsonschema.validate(doc, schema, registry=_SCHEMA_REGISTRY)

    def test_js_ecosystem(self) -> None:
        """JS ecosystem SBOM validates against CycloneDX 1.5 schema."""
        schema = _load_schema('bom-1.5.schema.json')
        if not schema:
            return
        m = _manifest(('react', '18.0.0'), ('@genkit/core', '0.5.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.CYCLONEDX, ecosystem='js'))
        jsonschema.validate(doc, schema, registry=_SCHEMA_REGISTRY)


class TestSPDXSchemaValidation:
    """Validate generated SPDX output against the official 2.3 schema."""

    def test_single_package(self) -> None:
        """Single-package SBOM validates against SPDX 2.3 schema."""
        schema = _load_schema('spdx-2.3.schema.json')
        if not schema:
            return
        m = _manifest(('genkit', '0.5.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX, supplier='Google LLC'))
        jsonschema.validate(doc, schema)

    def test_multiple_packages(self) -> None:
        """Multi-package SBOM validates against SPDX 2.3 schema."""
        schema = _load_schema('spdx-2.3.schema.json')
        if not schema:
            return
        m = _manifest(
            ('genkit', '0.5.0'),
            ('genkit-plugin-google-genai', '0.5.0'),
            ('genkit-plugin-vertex-ai', '0.5.0'),
        )
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX, supplier='Google LLC'))
        jsonschema.validate(doc, schema)

    def test_minimal_no_supplier(self) -> None:
        """Minimal SBOM without supplier validates."""
        schema = _load_schema('spdx-2.3.schema.json')
        if not schema:
            return
        m = _manifest(('foo', '1.0.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX))
        jsonschema.validate(doc, schema)

    def test_no_license(self) -> None:
        """SBOM with NOASSERTION license validates."""
        schema = _load_schema('spdx-2.3.schema.json')
        if not schema:
            return
        m = _manifest(('bar', '2.0.0'))
        doc = json.loads(generate_sbom(m, fmt=SBOMFormat.SPDX, license_id=''))
        jsonschema.validate(doc, schema)
