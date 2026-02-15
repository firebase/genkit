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

"""Software Bill of Materials (SBOM) generation for releasekit.

Generates CycloneDX and SPDX SBOMs from workspace package metadata.
SBOMs list every component (package) in a release with its version,
license, supplier, and dependency relationships — required for supply
chain compliance (Executive Order 14028, NIST SP 800-218).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ SBOM                │ An ingredient list for software — every       │
    │                     │ library, its version, and its license.        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ CycloneDX           │ An OWASP standard for SBOMs (JSON/XML).      │
    │                     │ Widely adopted in security scanning.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ SPDX                │ A Linux Foundation standard for SBOMs.        │
    │                     │ Required by some government procurement.      │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Component           │ One entry in the SBOM: name, version,        │
    │                     │ license, purl, and dependencies.             │
    └─────────────────────┴────────────────────────────────────────────────┘

Supported formats::

    ┌──────────────┬──────────────────────────────────────────────────────┐
    │ Format       │ Output                                               │
    ├──────────────┼──────────────────────────────────────────────────────┤
    │ CycloneDX    │ ``sbom.cdx.json`` (CycloneDX 1.5 JSON)             │
    ├──────────────┼──────────────────────────────────────────────────────┤
    │ SPDX         │ ``sbom.spdx.json`` (SPDX 2.3 JSON)                 │
    └──────────────┴──────────────────────────────────────────────────────┘

Usage::

    from releasekit.sbom import generate_sbom, SBOMFormat

    # From a release manifest:
    sbom = generate_sbom(
        manifest=manifest,
        packages=packages,
        format=SBOMFormat.CYCLONEDX,
        supplier='Google LLC',
    )

    # Write to file:
    Path('sbom.cdx.json').write_text(sbom)

    # Or generate both formats:
    for fmt in SBOMFormat:
        content = generate_sbom(manifest=manifest, packages=packages, format=fmt)
        Path(f'sbom{fmt.extension}').write_text(content)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from releasekit.logging import get_logger
from releasekit.utils.date import utc_iso
from releasekit.versions import ReleaseManifest

logger = get_logger(__name__)


class SBOMFormat(str, Enum):
    """Supported SBOM output formats."""

    CYCLONEDX = 'cyclonedx'
    SPDX = 'spdx'

    @property
    def extension(self) -> str:
        """File extension for this format."""
        if self == SBOMFormat.CYCLONEDX:
            return '.cdx.json'
        return '.spdx.json'


@dataclass(frozen=True)
class SBOMComponent:
    """A single component (package) in the SBOM.

    Attributes:
        name: Package name.
        version: Package version.
        purl: Package URL (https://github.com/package-url/purl-spec).
        license_id: SPDX license identifier (e.g. ``"Apache-2.0"``).
        supplier: Supplier / author organization.
        description: Short package description.
        dependencies: Names of direct dependencies.
    """

    name: str
    version: str
    purl: str = ''
    license_id: str = ''
    supplier: str = ''
    description: str = ''
    dependencies: list[str] = field(default_factory=list)


def _make_purl(name: str, version: str, ecosystem: str = 'python') -> str:
    """Build a Package URL (purl) for a component.

    Args:
        name: Package name.
        version: Package version.
        ecosystem: Package ecosystem (``"python"`` or ``"js"``).

    Returns:
        A purl string like ``pkg:pypi/genkit@0.5.0``.
    """
    if ecosystem in ('js', 'javascript', 'npm', 'pnpm'):
        # npm purl: pkg:npm/@scope/name@version or pkg:npm/name@version
        if name.startswith('@'):
            # Scoped: @scope/name → %40scope/name
            return f'pkg:npm/{name}@{version}'
        return f'pkg:npm/{name}@{version}'
    # Default to PyPI.
    normalized = name.replace('-', '_').lower()
    return f'pkg:pypi/{normalized}@{version}'


def _build_components(
    manifest: ReleaseManifest,
    *,
    ecosystem: str = 'python',
    license_id: str = 'Apache-2.0',
    supplier: str = '',
) -> list[SBOMComponent]:
    """Build SBOM components from a release manifest.

    Args:
        manifest: Release manifest with package versions.
        ecosystem: Package ecosystem for purl generation.
        license_id: Default SPDX license ID for all components.
        supplier: Supplier organization name.

    Returns:
        List of SBOM components.
    """
    components: list[SBOMComponent] = []
    for pkg in manifest.packages:
        version = pkg.new_version if pkg.new_version else pkg.old_version
        components.append(
            SBOMComponent(
                name=pkg.name,
                version=version,
                purl=_make_purl(pkg.name, version, ecosystem),
                license_id=license_id,
                supplier=supplier,
            )
        )
    return components


def _render_cyclonedx(
    components: list[SBOMComponent],
    *,
    serial_number: str = '',
    timestamp: str = '',
    tool_name: str = 'releasekit',
    tool_version: str = '0.1.0',
) -> dict[str, Any]:
    """Render a CycloneDX 1.5 BOM document.

    Args:
        components: SBOM components.
        serial_number: Unique BOM serial number (auto-generated if empty).
        timestamp: ISO 8601 timestamp (auto-generated if empty).
        tool_name: Name of the generating tool.
        tool_version: Version of the generating tool.

    Returns:
        A dict suitable for ``json.dumps``.
    """
    if not serial_number:
        serial_number = f'urn:uuid:{uuid.uuid4()}'
    if not timestamp:
        timestamp = utc_iso()

    cdx_components: list[dict[str, Any]] = []
    for comp in components:
        entry: dict[str, Any] = {
            'type': 'library',
            'name': comp.name,
            'version': comp.version,
        }
        if comp.purl:
            entry['purl'] = comp.purl
            entry['bom-ref'] = comp.purl
        if comp.license_id:
            entry['licenses'] = [{'license': {'id': comp.license_id}}]
        if comp.supplier:
            entry['supplier'] = {'name': comp.supplier}
        if comp.description:
            entry['description'] = comp.description
        cdx_components.append(entry)

    return {
        'bomFormat': 'CycloneDX',
        'specVersion': '1.5',
        'serialNumber': serial_number,
        'version': 1,
        'metadata': {
            'timestamp': timestamp,
            'tools': {
                'components': [
                    {
                        'type': 'application',
                        'name': tool_name,
                        'version': tool_version,
                    }
                ],
            },
        },
        'components': cdx_components,
    }


def _render_spdx(
    components: list[SBOMComponent],
    *,
    document_name: str = 'releasekit-sbom',
    document_namespace: str = '',
    timestamp: str = '',
    tool_name: str = 'releasekit',
    tool_version: str = '0.1.0',
) -> dict[str, Any]:
    """Render an SPDX 2.3 document.

    Args:
        components: SBOM components.
        document_name: SPDX document name.
        document_namespace: Unique document namespace URI (auto-generated if empty).
        timestamp: ISO 8601 timestamp (auto-generated if empty).
        tool_name: Name of the generating tool.
        tool_version: Version of the generating tool.

    Returns:
        A dict suitable for ``json.dumps``.
    """
    if not document_namespace:
        document_namespace = f'https://spdx.org/spdxdocs/{document_name}-{uuid.uuid4()}'
    if not timestamp:
        timestamp = utc_iso()

    spdx_packages: list[dict[str, Any]] = []
    for comp in components:
        spdx_id = f'SPDXRef-{comp.name.replace("/", "-").replace("@", "").replace(".", "-")}'
        pkg: dict[str, Any] = {
            'SPDXID': spdx_id,
            'name': comp.name,
            'versionInfo': comp.version,
            'downloadLocation': 'NOASSERTION',
            'filesAnalyzed': False,
        }
        if comp.license_id:
            pkg['licenseConcluded'] = comp.license_id
            pkg['licenseDeclared'] = comp.license_id
        else:
            pkg['licenseConcluded'] = 'NOASSERTION'
            pkg['licenseDeclared'] = 'NOASSERTION'
        if comp.supplier:
            pkg['supplier'] = f'Organization: {comp.supplier}'
        if comp.purl:
            pkg['externalRefs'] = [
                {
                    'referenceCategory': 'PACKAGE-MANAGER',
                    'referenceType': 'purl',
                    'referenceLocator': comp.purl,
                }
            ]
        spdx_packages.append(pkg)

    return {
        'spdxVersion': 'SPDX-2.3',
        'dataLicense': 'CC0-1.0',
        'SPDXID': 'SPDXRef-DOCUMENT',
        'name': document_name,
        'documentNamespace': document_namespace,
        'creationInfo': {
            'created': timestamp,
            'creators': [f'Tool: {tool_name}-{tool_version}'],
        },
        'packages': spdx_packages,
    }


def generate_sbom(
    manifest: ReleaseManifest,
    *,
    fmt: SBOMFormat = SBOMFormat.CYCLONEDX,
    ecosystem: str = 'python',
    license_id: str = 'Apache-2.0',
    supplier: str = '',
    indent: int = 2,
) -> str:
    """Generate an SBOM from a release manifest.

    Args:
        manifest: Release manifest with package versions.
        fmt: Output format (CycloneDX or SPDX).
        ecosystem: Package ecosystem for purl generation.
        license_id: Default SPDX license ID for all components.
        supplier: Supplier organization name.
        indent: JSON indentation level.

    Returns:
        JSON string of the SBOM document.
    """
    components = _build_components(
        manifest,
        ecosystem=ecosystem,
        license_id=license_id,
        supplier=supplier,
    )

    if fmt == SBOMFormat.CYCLONEDX:
        doc = _render_cyclonedx(components)
    else:
        doc = _render_spdx(components)

    logger.info(
        'sbom_generated',
        format=fmt.value,
        components=len(components),
    )
    return json.dumps(doc, indent=indent)


def write_sbom(
    manifest: ReleaseManifest,
    output_dir: Path,
    *,
    fmt: SBOMFormat = SBOMFormat.CYCLONEDX,
    ecosystem: str = 'python',
    license_id: str = 'Apache-2.0',
    supplier: str = '',
) -> Path:
    """Generate and write an SBOM file.

    Args:
        manifest: Release manifest with package versions.
        output_dir: Directory to write the SBOM file to.
        fmt: Output format (CycloneDX or SPDX).
        ecosystem: Package ecosystem for purl generation.
        license_id: Default SPDX license ID for all components.
        supplier: Supplier organization name.

    Returns:
        Path to the written SBOM file.
    """
    content = generate_sbom(
        manifest,
        fmt=fmt,
        ecosystem=ecosystem,
        license_id=license_id,
        supplier=supplier,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f'sbom{fmt.extension}'
    output_path = output_dir / filename
    output_path.write_text(content, encoding='utf-8')

    logger.info('sbom_written', path=str(output_path), format=fmt.value)
    return output_path


__all__ = [
    'SBOMComponent',
    'SBOMFormat',
    'generate_sbom',
    'write_sbom',
]
