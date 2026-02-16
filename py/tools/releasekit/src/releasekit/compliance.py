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

r"""OSPS Baseline and NIST SSDF compliance tracker.

Maps releasekit capabilities to `OpenSSF OSPS Baseline`_ levels
(L1/L2/L3) and NIST SSDF tasks.  The ``releasekit compliance``
subcommand uses this module to output a compliance matrix.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ OSPS Baseline       │ An OpenSSF umbrella framework that maps to   │
    │                     │ NIST CSF, EU CRA, SSDF, and SLSA.           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Compliance control  │ A specific security practice (e.g. "generate │
    │                     │ SBOM", "sign artifacts").                     │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Met / Partial / Gap │ Whether releasekit fully meets, partially    │
    │                     │ meets, or does not meet a control.           │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.compliance import (
        evaluate_compliance,
        ComplianceStatus,
    )

    results = evaluate_compliance(repo_root=Path('.'))
    for r in results:
        print(f'{r.control}: {r.status.value} — {r.module}')

.. _OpenSSF OSPS Baseline: https://best.openssf.org/Concise-Guide-for-Evaluating-Open-Source-Software
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass
from pathlib import Path

from releasekit.logging import get_logger

logger = get_logger(__name__)


class ComplianceStatus(str, enum.Enum):
    """Status of a compliance control."""

    MET = 'met'
    PARTIAL = 'partial'
    GAP = 'gap'


class OSPSLevel(int, enum.Enum):
    """OSPS Baseline maturity levels."""

    L1 = 1
    L2 = 2
    L3 = 3


@dataclass(frozen=True)
class ComplianceControl:
    """A single compliance control and its evaluation.

    Attributes:
        id: Control identifier (e.g. ``'OSPS-SCA-01'``).
        control: Human-readable control name.
        osps_level: The OSPS Baseline level this control belongs to.
        status: Whether the control is met, partial, or a gap.
        module: The releasekit module that implements this control.
        nist_ssdf: Corresponding NIST SSDF task ID (if any).
        notes: Additional context about the evaluation.
    """

    id: str
    control: str
    osps_level: OSPSLevel
    status: ComplianceStatus
    module: str = ''
    nist_ssdf: str = ''
    notes: str = ''


def _check_file_exists(repo_root: Path, *candidates: str) -> bool:
    """Check if any of the candidate files exist under repo_root."""
    return any((repo_root / c).is_file() for c in candidates)


def _detect_ecosystems(repo_root: Path) -> frozenset[str]:
    """Auto-detect which ecosystems are present in the repo.

    Looks for canonical manifest files to determine which language
    ecosystems are active.
    """
    ecosystems: set[str] = set()
    markers = {
        'python': ('pyproject.toml', 'setup.py', 'setup.cfg', 'uv.lock', 'Pipfile'),
        'go': ('go.mod', 'go.sum'),
        'js': ('package.json', 'pnpm-lock.yaml', 'package-lock.json', 'yarn.lock'),
        'java': ('pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle'),
        'rust': ('Cargo.toml', 'Cargo.lock'),
        'dart': ('pubspec.yaml', 'pubspec.lock'),
    }
    for eco, files in markers.items():
        for f in files:
            if (repo_root / f).exists() or list(repo_root.glob(f'**/{f}'))[:1]:
                ecosystems.add(eco)
                break
    return frozenset(ecosystems)


def _ecosystem_controls(
    repo_root: Path,
    detected: frozenset[str],
) -> list[ComplianceControl]:
    """Generate ecosystem-specific security and compliance controls.

    Each ecosystem has its own security requirements around type safety,
    manifest hygiene, registry attestation, and vulnerability tooling.
    Controls are only emitted for ecosystems detected in the repo.
    """
    controls: list[ComplianceControl] = []

    # Python-specific controls.
    if 'python' in detected:
        has_py_typed = bool(list(repo_root.glob('**/py.typed'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-PY-01',
                control='PEP 561 type markers (py.typed)',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_py_typed else ComplianceStatus.GAP,
                module='checks/_python.py',
                notes='Type-safe packages improve downstream security analysis.',
            )
        )

        has_pep740 = bool(list(repo_root.glob('dist/*.publish.attestation'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-PY-02',
                control='PEP 740 publish attestations',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_pep740 else ComplianceStatus.GAP,
                module='attestations.py',
                notes='PyPI Trusted Publisher attestations (PEP 740).',
            )
        )

        has_requires_python = _check_file_exists(repo_root, 'pyproject.toml')
        controls.append(
            ComplianceControl(
                id='ECO-PY-03',
                control='requires-python declared',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_requires_python else ComplianceStatus.GAP,
                module='checks/_python.py',
                notes='Prevents install on incompatible Python versions.',
            )
        )

    # Go-specific controls.
    if 'go' in detected:
        has_go_mod = bool(list(repo_root.glob('**/go.mod'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-GO-01',
                control='go.mod present',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_go_mod else ComplianceStatus.GAP,
                module='checks/_go.py',
                notes='Module dependency management.',
            )
        )

        has_go_sum = bool(list(repo_root.glob('**/go.sum'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-GO-02',
                control='go.sum integrity verification',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_go_sum else ComplianceStatus.GAP,
                module='checks/_go.py',
                notes='Cryptographic hash verification of dependencies.',
            )
        )

        has_govulncheck_ci = _check_file_exists(
            repo_root,
            '.github/workflows/govulncheck.yml',
            '.github/workflows/govulncheck.yaml',
        )
        controls.append(
            ComplianceControl(
                id='ECO-GO-03',
                control='govulncheck in CI',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_govulncheck_ci else ComplianceStatus.PARTIAL,
                module='osv.py',
                notes='Go vulnerability database scanning.' if has_govulncheck_ci else 'OSV fallback only.',
            )
        )

    # JS/Node-specific controls.
    if 'js' in detected:
        has_pkg_json = bool(list(repo_root.glob('**/package.json'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-JS-01',
                control='package.json present',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_pkg_json else ComplianceStatus.GAP,
                module='checks/_js.py',
                notes='npm/pnpm manifest.',
            )
        )

        has_npm_provenance = _check_file_exists(
            repo_root,
            '.github/workflows/publish.yml',
            '.github/workflows/release.yml',
        )
        controls.append(
            ComplianceControl(
                id='ECO-JS-02',
                control='npm provenance (--provenance)',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.PARTIAL if has_npm_provenance else ComplianceStatus.GAP,
                module='publisher.py',
                notes='npm publish --provenance for Sigstore-backed attestations.',
            )
        )

        has_npmrc = _check_file_exists(repo_root, '.npmrc')
        controls.append(
            ComplianceControl(
                id='ECO-JS-03',
                control='.npmrc registry config',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_npmrc else ComplianceStatus.PARTIAL,
                module='',
                notes='Explicit registry pinning prevents substitution attacks.',
            )
        )

    # Java-specific controls.
    if 'java' in detected:
        has_gradle = _check_file_exists(
            repo_root,
            'build.gradle',
            'build.gradle.kts',
            'settings.gradle',
        ) or bool(list(repo_root.glob('**/build.gradle*'))[:1])
        has_maven = _check_file_exists(repo_root, 'pom.xml') or bool(
            list(repo_root.glob('**/pom.xml'))[:1],
        )
        controls.append(
            ComplianceControl(
                id='ECO-JV-01',
                control='Build system manifest',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if (has_gradle or has_maven) else ComplianceStatus.GAP,
                module='checks/_java.py',
                notes='Gradle' if has_gradle else ('Maven' if has_maven else ''),
            )
        )

        has_dep_verification = _check_file_exists(
            repo_root,
            'gradle/verification-metadata.xml',
        ) or bool(list(repo_root.glob('**/verification-metadata.xml'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-JV-02',
                control='Gradle dependency verification',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_dep_verification else ComplianceStatus.GAP,
                module='checks/_java.py',
                notes='Checksum/signature verification of dependencies.',
            )
        )

        has_signing_key = _check_file_exists(
            repo_root,
            'gradle.properties',
        )
        controls.append(
            ComplianceControl(
                id='ECO-JV-03',
                control='Maven Central signing (GPG)',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.PARTIAL if has_signing_key else ComplianceStatus.GAP,
                module='signing.py',
                notes='Maven Central requires GPG-signed artifacts.',
            )
        )

    # Rust-specific controls.
    if 'rust' in detected:
        has_cargo_toml = bool(list(repo_root.glob('**/Cargo.toml'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-RS-01',
                control='Cargo.toml present',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_cargo_toml else ComplianceStatus.GAP,
                module='checks/_rust.py',
                notes='Rust package manifest.',
            )
        )

        has_cargo_lock = _check_file_exists(repo_root, 'Cargo.lock')
        controls.append(
            ComplianceControl(
                id='ECO-RS-02',
                control='Cargo.lock committed',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_cargo_lock else ComplianceStatus.GAP,
                module='checks/_rust.py',
                notes='Reproducible builds require committed lockfile.',
            )
        )

        has_cargo_audit_ci = _check_file_exists(
            repo_root,
            '.github/workflows/audit.yml',
            '.github/workflows/audit.yaml',
            '.github/workflows/security.yml',
        )
        controls.append(
            ComplianceControl(
                id='ECO-RS-03',
                control='cargo-audit in CI',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_cargo_audit_ci else ComplianceStatus.PARTIAL,
                module='osv.py',
                notes='RustSec advisory database scanning.' if has_cargo_audit_ci else 'OSV fallback only.',
            )
        )

        has_deny_toml = _check_file_exists(repo_root, 'deny.toml')
        controls.append(
            ComplianceControl(
                id='ECO-RS-04',
                control='cargo-deny license/advisory policy',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_deny_toml else ComplianceStatus.GAP,
                module='',
                notes='Enforces license allowlist and advisory bans.',
            )
        )

    # Dart-specific controls.
    if 'dart' in detected:
        has_pubspec = bool(list(repo_root.glob('**/pubspec.yaml'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-DT-01',
                control='pubspec.yaml present',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_pubspec else ComplianceStatus.GAP,
                module='checks/_dart.py',
                notes='Dart/Flutter package manifest.',
            )
        )

        has_pubspec_lock = bool(list(repo_root.glob('**/pubspec.lock'))[:1])
        controls.append(
            ComplianceControl(
                id='ECO-DT-02',
                control='pubspec.lock committed',
                osps_level=OSPSLevel.L2,
                status=ComplianceStatus.MET if has_pubspec_lock else ComplianceStatus.GAP,
                module='checks/_dart.py',
                notes='Reproducible builds require committed lockfile.',
            )
        )

        has_analysis_options = _check_file_exists(repo_root, 'analysis_options.yaml')
        controls.append(
            ComplianceControl(
                id='ECO-DT-03',
                control='analysis_options.yaml (strict mode)',
                osps_level=OSPSLevel.L1,
                status=ComplianceStatus.MET if has_analysis_options else ComplianceStatus.GAP,
                module='',
                notes='Static analysis rules for type safety and security.',
            )
        )

    return controls


def evaluate_compliance(
    repo_root: Path,
    *,
    has_signing: bool = True,
    has_provenance: bool = True,
    has_sbom: bool = True,
    has_vuln_scanning: bool = False,
    has_slsa_l3: bool = False,
    ecosystems: frozenset[str] | None = None,
) -> list[ComplianceControl]:
    """Evaluate compliance against OSPS Baseline controls.

    Checks a combination of releasekit capabilities (passed as flags)
    and repository file existence (checked on disk).  When *ecosystems*
    is ``None``, auto-detects which ecosystems are present.

    Args:
        repo_root: Path to the repository root.
        has_signing: Whether Sigstore signing is enabled.
        has_provenance: Whether SLSA provenance generation is enabled.
        has_sbom: Whether SBOM generation is enabled.
        has_vuln_scanning: Whether vulnerability scanning is configured.
        has_slsa_l3: Whether SLSA Build L3 is achievable.
        ecosystems: Explicit set of ecosystem names (e.g.
            ``{'python', 'go', 'js'}``).  Auto-detected if ``None``.

    Returns:
        List of :class:`ComplianceControl` evaluations.
    """
    controls: list[ComplianceControl] = []
    detected = ecosystems if ecosystems is not None else _detect_ecosystems(repo_root)

    # L1: SBOM generation.
    controls.append(
        ComplianceControl(
            id='OSPS-SCA-01',
            control='SBOM generation',
            osps_level=OSPSLevel.L1,
            status=ComplianceStatus.MET if has_sbom else ComplianceStatus.GAP,
            module='sbom.py',
            nist_ssdf='PS.3.2',
            notes='CycloneDX 1.5 + SPDX 2.3' if has_sbom else '',
        )
    )

    # L1: SECURITY.md present.
    has_security_md = _check_file_exists(
        repo_root,
        'SECURITY.md',
        '.github/SECURITY.md',
        'docs/SECURITY.md',
    )
    controls.append(
        ComplianceControl(
            id='OSPS-GOV-01',
            control='Security policy (SECURITY.md)',
            osps_level=OSPSLevel.L1,
            status=ComplianceStatus.MET if has_security_md else ComplianceStatus.GAP,
            module='scorecard.py',
            nist_ssdf='PO.1.1',
        )
    )

    # L1: License declared.
    has_license = _check_file_exists(
        repo_root,
        'LICENSE',
        'LICENSE.md',
        'LICENSE.txt',
        'COPYING',
    )
    controls.append(
        ComplianceControl(
            id='OSPS-LEG-01',
            control='License declared',
            osps_level=OSPSLevel.L1,
            status=ComplianceStatus.MET if has_license else ComplianceStatus.GAP,
            module='',
            nist_ssdf='PO.1.3',
        )
    )

    # L2: Signed artifacts.
    controls.append(
        ComplianceControl(
            id='OSPS-SCA-02',
            control='Signed release artifacts',
            osps_level=OSPSLevel.L2,
            status=ComplianceStatus.MET if has_signing else ComplianceStatus.GAP,
            module='signing.py',
            nist_ssdf='PS.2.1',
            notes='Sigstore keyless signing' if has_signing else '',
        )
    )

    # L2: Provenance attestation.
    controls.append(
        ComplianceControl(
            id='OSPS-SCA-03',
            control='Provenance attestation',
            osps_level=OSPSLevel.L2,
            status=ComplianceStatus.MET if has_provenance else ComplianceStatus.GAP,
            module='provenance.py',
            nist_ssdf='PS.3.1',
            notes='in-toto SLSA Provenance v1' if has_provenance else '',
        )
    )

    # L2: Vulnerability scanning.
    vuln_tools: list[str] = []
    if 'python' in detected:
        vuln_tools.append('pip-audit')
    if 'go' in detected:
        vuln_tools.append('govulncheck')
    if 'js' in detected:
        vuln_tools.append('npm audit')
    if 'rust' in detected:
        vuln_tools.append('cargo-audit')
    if 'java' in detected:
        vuln_tools.append('OWASP dep-check')
    if 'dart' in detected:
        vuln_tools.append('dart pub outdated')
    vuln_tools.append('OSV')
    vuln_notes = ' + '.join(vuln_tools) if has_vuln_scanning else f'{" + ".join(vuln_tools)} (partial)'
    controls.append(
        ComplianceControl(
            id='OSPS-SCA-04',
            control='Vulnerability scanning',
            osps_level=OSPSLevel.L2,
            status=(ComplianceStatus.MET if has_vuln_scanning else ComplianceStatus.PARTIAL),
            module='preflight.py / osv.py',
            nist_ssdf='RV.1.1',
            notes=vuln_notes,
        )
    )

    # L2: Dependency pinning.
    lockfile_map = {
        'python': ('uv.lock', 'Pipfile.lock', 'poetry.lock'),
        'js': ('pnpm-lock.yaml', 'package-lock.json', 'yarn.lock', 'bun.lockb'),
        'go': ('go.sum',),
        'rust': ('Cargo.lock',),
        'java': ('gradle.lockfile', 'buildscript-gradle.lockfile'),
        'dart': ('pubspec.lock',),
    }
    found_lockfiles: list[str] = []
    search_ecos = sorted(detected) if detected else sorted(lockfile_map)
    for eco in search_ecos:
        for lf in lockfile_map.get(eco, ()):
            if _check_file_exists(repo_root, lf) or list(repo_root.glob(f'**/{lf}'))[:1]:
                found_lockfiles.append(lf)
                break
    has_lockfile = bool(found_lockfiles)
    controls.append(
        ComplianceControl(
            id='OSPS-SCA-05',
            control='Dependency pinning (lockfile)',
            osps_level=OSPSLevel.L2,
            status=ComplianceStatus.MET if has_lockfile else ComplianceStatus.GAP,
            module='preflight.py',
            nist_ssdf='PS.1.1',
            notes=', '.join(found_lockfiles) if found_lockfiles else '',
        )
    )

    # L2: Dependency update tool.
    has_dep_tool = _check_file_exists(
        repo_root,
        '.github/dependabot.yml',
        '.github/dependabot.yaml',
        'renovate.json',
        'renovate.json5',
        '.renovaterc',
        '.renovaterc.json',
    )
    controls.append(
        ComplianceControl(
            id='OSPS-SCA-06',
            control='Automated dependency updates',
            osps_level=OSPSLevel.L2,
            status=ComplianceStatus.MET if has_dep_tool else ComplianceStatus.GAP,
            module='scorecard.py',
            nist_ssdf='PS.1.1',
        )
    )

    # L3: Build isolation (SLSA L3).
    controls.append(
        ComplianceControl(
            id='OSPS-BLD-01',
            control='Build isolation (SLSA Build L3)',
            osps_level=OSPSLevel.L3,
            status=ComplianceStatus.MET if has_slsa_l3 else ComplianceStatus.PARTIAL,
            module='provenance.py',
            nist_ssdf='PW.6.1',
            notes='GitHub-hosted runners' if has_slsa_l3 else 'L2 achieved, L3 requires hosted runners',
        )
    )

    # L3: Signed provenance.
    controls.append(
        ComplianceControl(
            id='OSPS-BLD-02',
            control='Signed provenance',
            osps_level=OSPSLevel.L3,
            status=ComplianceStatus.MET if (has_signing and has_provenance) else ComplianceStatus.GAP,
            module='signing.py + provenance.py',
            nist_ssdf='PS.2.1',
        )
    )

    # Ecosystem-specific controls.
    controls.extend(_ecosystem_controls(repo_root, detected))

    met = sum(1 for c in controls if c.status == ComplianceStatus.MET)
    partial = sum(1 for c in controls if c.status == ComplianceStatus.PARTIAL)
    gap = sum(1 for c in controls if c.status == ComplianceStatus.GAP)
    logger.info(
        'compliance_evaluated',
        met=met,
        partial=partial,
        gap=gap,
        total=len(controls),
        ecosystems=sorted(detected),
    )

    return controls


def format_compliance_table(controls: list[ComplianceControl]) -> str:
    """Format compliance results as a human-readable table.

    Args:
        controls: List of evaluated compliance controls.

    Returns:
        Multi-line table string.
    """
    status_icons = {
        ComplianceStatus.MET: '\u2705',
        ComplianceStatus.PARTIAL: '\u26a0\ufe0f',
        ComplianceStatus.GAP: '\u274c',
    }
    lines: list[str] = []
    lines.append(
        f'{"ID":<14} {"Control":<35} {"Level":<5} {"Status":<9} {"Module":<30} {"Notes"}',
    )
    lines.append('-' * 110)
    for c in controls:
        icon = status_icons.get(c.status, '?')
        level = f'L{c.osps_level.value}'
        lines.append(
            f'{c.id:<14} {c.control:<35} {level:<5} {icon} {c.status.value:<7} {c.module:<30} {c.notes}',
        )

    met = sum(1 for c in controls if c.status == ComplianceStatus.MET)
    lines.append(f'\n{met}/{len(controls)} controls met.')
    return '\n'.join(lines)


def compliance_to_json(controls: list[ComplianceControl], *, indent: int = 2) -> str:
    """Serialize compliance results to JSON.

    Args:
        controls: List of evaluated compliance controls.
        indent: JSON indentation level.

    Returns:
        JSON string.
    """
    records = [
        {
            'id': c.id,
            'control': c.control,
            'osps_level': f'L{c.osps_level.value}',
            'status': c.status.value,
            'module': c.module,
            'nist_ssdf': c.nist_ssdf,
            'notes': c.notes,
        }
        for c in controls
    ]
    return json.dumps(records, indent=indent)


__all__ = [
    'ComplianceControl',
    'ComplianceStatus',
    'OSPSLevel',
    'compliance_to_json',
    'evaluate_compliance',
    'format_compliance_table',
]
