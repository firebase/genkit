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

"""Tests for OSPS Baseline compliance tracker.

Validates the compliance evaluation and JSON serialization in
:mod:`releasekit.compliance`.

Key Concepts::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ What We Test                                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Control evaluation  │ Each control maps to met/partial/gap          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ File detection      │ SECURITY.md, LICENSE, lockfiles detected      │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ JSON serialization  │ compliance_to_json() produces valid JSON      │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    test → create temp repo → evaluate_compliance() → assert controls
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from releasekit.compliance import (
    ComplianceControl,
    ComplianceStatus,
    OSPSLevel,
    compliance_to_json,
    evaluate_compliance,
    format_compliance_table,
)


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    """Create a minimal repo structure."""
    return tmp_path


class TestEvaluateCompliance:
    """Tests for compliance evaluation."""

    def test_returns_all_controls(self, repo_root: Path) -> None:
        """All expected controls are returned."""
        controls = evaluate_compliance(repo_root)
        assert len(controls) >= 9
        ids = {c.id for c in controls}
        assert 'OSPS-SCA-01' in ids  # SBOM
        assert 'OSPS-GOV-01' in ids  # SECURITY.md
        assert 'OSPS-LEG-01' in ids  # License
        assert 'OSPS-SCA-02' in ids  # Signing
        assert 'OSPS-SCA-03' in ids  # Provenance
        assert 'OSPS-SCA-04' in ids  # Vuln scanning
        assert 'OSPS-SCA-05' in ids  # Dependency pinning
        assert 'OSPS-BLD-01' in ids  # Build isolation
        assert 'OSPS-BLD-02' in ids  # Signed provenance

    def test_sbom_met_by_default(self, repo_root: Path) -> None:
        """SBOM control is met when has_sbom=True (default)."""
        controls = evaluate_compliance(repo_root)
        sbom = next(c for c in controls if c.id == 'OSPS-SCA-01')
        assert sbom.status == ComplianceStatus.MET
        assert sbom.hint == ''

    def test_sbom_gap_when_disabled(self, repo_root: Path) -> None:
        """SBOM control is gap when has_sbom=False."""
        controls = evaluate_compliance(repo_root, has_sbom=False)
        sbom = next(c for c in controls if c.id == 'OSPS-SCA-01')
        assert sbom.status == ComplianceStatus.GAP
        assert sbom.hint  # gap controls must have a hint

    def test_security_md_detected(self, repo_root: Path) -> None:
        """SECURITY.md at repo root is detected."""
        (repo_root / 'SECURITY.md').write_text('# Security\n')
        controls = evaluate_compliance(repo_root)
        gov = next(c for c in controls if c.id == 'OSPS-GOV-01')
        assert gov.status == ComplianceStatus.MET

    def test_security_md_missing(self, repo_root: Path) -> None:
        """Missing SECURITY.md is a gap with actionable hint."""
        controls = evaluate_compliance(repo_root)
        gov = next(c for c in controls if c.id == 'OSPS-GOV-01')
        assert gov.status == ComplianceStatus.GAP
        assert 'SECURITY.md' in gov.hint

    def test_license_detected(self, repo_root: Path) -> None:
        """LICENSE file is detected."""
        (repo_root / 'LICENSE').write_text('Apache-2.0\n')
        controls = evaluate_compliance(repo_root)
        lic = next(c for c in controls if c.id == 'OSPS-LEG-01')
        assert lic.status == ComplianceStatus.MET

    def test_license_missing(self, repo_root: Path) -> None:
        """Missing LICENSE is a gap."""
        controls = evaluate_compliance(repo_root)
        lic = next(c for c in controls if c.id == 'OSPS-LEG-01')
        assert lic.status == ComplianceStatus.GAP

    def test_signing_met(self, repo_root: Path) -> None:
        """Signing control is met when has_signing=True."""
        controls = evaluate_compliance(repo_root, has_signing=True)
        sign = next(c for c in controls if c.id == 'OSPS-SCA-02')
        assert sign.status == ComplianceStatus.MET

    def test_signing_gap(self, repo_root: Path) -> None:
        """Signing control is gap when has_signing=False."""
        controls = evaluate_compliance(repo_root, has_signing=False)
        sign = next(c for c in controls if c.id == 'OSPS-SCA-02')
        assert sign.status == ComplianceStatus.GAP

    def test_vuln_scanning_partial_by_default(self, repo_root: Path) -> None:
        """Vulnerability scanning is partial by default (pip-audit only)."""
        controls = evaluate_compliance(repo_root)
        vuln = next(c for c in controls if c.id == 'OSPS-SCA-04')
        assert vuln.status == ComplianceStatus.PARTIAL

    def test_vuln_scanning_met(self, repo_root: Path) -> None:
        """Vulnerability scanning is met when has_vuln_scanning=True."""
        controls = evaluate_compliance(repo_root, has_vuln_scanning=True)
        vuln = next(c for c in controls if c.id == 'OSPS-SCA-04')
        assert vuln.status == ComplianceStatus.MET

    def test_lockfile_detected(self, repo_root: Path) -> None:
        """uv.lock is detected for dependency pinning."""
        (repo_root / 'uv.lock').write_text('# lockfile\n')
        controls = evaluate_compliance(repo_root)
        pin = next(c for c in controls if c.id == 'OSPS-SCA-05')
        assert pin.status == ComplianceStatus.MET

    def test_lockfile_missing(self, repo_root: Path) -> None:
        """Missing lockfile is a gap."""
        controls = evaluate_compliance(repo_root)
        pin = next(c for c in controls if c.id == 'OSPS-SCA-05')
        assert pin.status == ComplianceStatus.GAP

    def test_slsa_l3_met(self, repo_root: Path) -> None:
        """Build isolation is met when has_slsa_l3=True."""
        controls = evaluate_compliance(repo_root, has_slsa_l3=True)
        bld = next(c for c in controls if c.id == 'OSPS-BLD-01')
        assert bld.status == ComplianceStatus.MET

    def test_slsa_l3_partial(self, repo_root: Path) -> None:
        """Build isolation is partial when has_slsa_l3=False."""
        controls = evaluate_compliance(repo_root, has_slsa_l3=False)
        bld = next(c for c in controls if c.id == 'OSPS-BLD-01')
        assert bld.status == ComplianceStatus.PARTIAL

    def test_signed_provenance_met(self, repo_root: Path) -> None:
        """Signed provenance is met when both signing and provenance enabled."""
        controls = evaluate_compliance(
            repo_root,
            has_signing=True,
            has_provenance=True,
        )
        sp = next(c for c in controls if c.id == 'OSPS-BLD-02')
        assert sp.status == ComplianceStatus.MET

    def test_signed_provenance_gap(self, repo_root: Path) -> None:
        """Signed provenance is gap when signing disabled."""
        controls = evaluate_compliance(
            repo_root,
            has_signing=False,
            has_provenance=True,
        )
        sp = next(c for c in controls if c.id == 'OSPS-BLD-02')
        assert sp.status == ComplianceStatus.GAP

    def test_all_controls_have_osps_level(self, repo_root: Path) -> None:
        """Every control has an OSPS level."""
        controls = evaluate_compliance(repo_root)
        for c in controls:
            assert isinstance(c.osps_level, OSPSLevel)

    def test_well_configured_repo(self, repo_root: Path) -> None:
        """Well-configured repo has mostly MET controls."""
        (repo_root / 'SECURITY.md').write_text('# Security\n')
        (repo_root / 'LICENSE').write_text('Apache-2.0\n')
        (repo_root / 'uv.lock').write_text('# lock\n')
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'dependabot.yml').write_text('version: 2\n')

        controls = evaluate_compliance(
            repo_root,
            has_signing=True,
            has_provenance=True,
            has_sbom=True,
            has_vuln_scanning=True,
            has_slsa_l3=True,
            ecosystems=frozenset(),
        )
        met = sum(1 for c in controls if c.status == ComplianceStatus.MET)
        assert met == len(controls), f'Expected all MET, got: {[(c.id, c.status) for c in controls]}'


class TestComplianceToJson:
    """Tests for JSON serialization."""

    def test_valid_json(self, repo_root: Path) -> None:
        """Output is valid JSON."""
        controls = evaluate_compliance(repo_root)
        output = compliance_to_json(controls)
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == len(controls)

    def test_json_fields(self, repo_root: Path) -> None:
        """JSON records have expected fields including hint."""
        controls = evaluate_compliance(repo_root)
        output = compliance_to_json(controls)
        data = json.loads(output)
        for record in data:
            assert 'id' in record
            assert 'control' in record
            assert 'osps_level' in record
            assert 'status' in record
            assert 'hint' in record
            assert record['status'] in ('met', 'partial', 'gap')

    def test_json_osps_level_format(self, repo_root: Path) -> None:
        """OSPS level is formatted as L1/L2/L3."""
        controls = evaluate_compliance(repo_root)
        output = compliance_to_json(controls)
        data = json.loads(output)
        for record in data:
            assert record['osps_level'] in ('L1', 'L2', 'L3')


class TestLockfileVariants:
    """Tests for various lockfile detection."""

    def test_pnpm_lock(self, repo_root: Path) -> None:
        """pnpm-lock.yaml is detected."""
        (repo_root / 'pnpm-lock.yaml').write_text('lockfileVersion: 9\n')
        controls = evaluate_compliance(repo_root)
        pin = next(c for c in controls if c.id == 'OSPS-SCA-05')
        assert pin.status == ComplianceStatus.MET

    def test_package_lock(self, repo_root: Path) -> None:
        """package-lock.json is detected."""
        (repo_root / 'package-lock.json').write_text('{}')
        controls = evaluate_compliance(repo_root)
        pin = next(c for c in controls if c.id == 'OSPS-SCA-05')
        assert pin.status == ComplianceStatus.MET

    def test_cargo_lock(self, repo_root: Path) -> None:
        """Cargo.lock is detected."""
        (repo_root / 'Cargo.lock').write_text('# cargo lock\n')
        controls = evaluate_compliance(repo_root)
        pin = next(c for c in controls if c.id == 'OSPS-SCA-05')
        assert pin.status == ComplianceStatus.MET

    def test_go_sum(self, repo_root: Path) -> None:
        """go.sum is detected."""
        (repo_root / 'go.sum').write_text('# go sum\n')
        controls = evaluate_compliance(repo_root)
        pin = next(c for c in controls if c.id == 'OSPS-SCA-05')
        assert pin.status == ComplianceStatus.MET


class TestLicenseVariants:
    """Tests for various license file detection."""

    def test_license_md(self, repo_root: Path) -> None:
        """LICENSE.md is detected."""
        (repo_root / 'LICENSE.md').write_text('# MIT\n')
        controls = evaluate_compliance(repo_root)
        lic = next(c for c in controls if c.id == 'OSPS-LEG-01')
        assert lic.status == ComplianceStatus.MET

    def test_license_txt(self, repo_root: Path) -> None:
        """LICENSE.txt is detected."""
        (repo_root / 'LICENSE.txt').write_text('MIT License\n')
        controls = evaluate_compliance(repo_root)
        lic = next(c for c in controls if c.id == 'OSPS-LEG-01')
        assert lic.status == ComplianceStatus.MET

    def test_copying(self, repo_root: Path) -> None:
        """COPYING is detected."""
        (repo_root / 'COPYING').write_text('GPL\n')
        controls = evaluate_compliance(repo_root)
        lic = next(c for c in controls if c.id == 'OSPS-LEG-01')
        assert lic.status == ComplianceStatus.MET


class TestSecurityMdVariants:
    """Tests for SECURITY.md detection in compliance."""

    def test_github_security_md(self, repo_root: Path) -> None:
        """.github/SECURITY.md is detected."""
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'SECURITY.md').write_text('# Security\n')
        controls = evaluate_compliance(repo_root)
        gov = next(c for c in controls if c.id == 'OSPS-GOV-01')
        assert gov.status == ComplianceStatus.MET

    def test_docs_security_md(self, repo_root: Path) -> None:
        """docs/SECURITY.md is detected."""
        (repo_root / 'docs').mkdir()
        (repo_root / 'docs' / 'SECURITY.md').write_text('# Security\n')
        controls = evaluate_compliance(repo_root)
        gov = next(c for c in controls if c.id == 'OSPS-GOV-01')
        assert gov.status == ComplianceStatus.MET


class TestDependencyUpdateToolCompliance:
    """Tests for dependency update tool detection in compliance."""

    def test_dependabot_detected(self, repo_root: Path) -> None:
        """dependabot.yml is detected for OSPS-SCA-06."""
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'dependabot.yml').write_text('version: 2\n')
        controls = evaluate_compliance(repo_root)
        dep = next(c for c in controls if c.id == 'OSPS-SCA-06')
        assert dep.status == ComplianceStatus.MET

    def test_renovate_detected(self, repo_root: Path) -> None:
        """renovate.json is detected for OSPS-SCA-06."""
        (repo_root / 'renovate.json').write_text('{}')
        controls = evaluate_compliance(repo_root)
        dep = next(c for c in controls if c.id == 'OSPS-SCA-06')
        assert dep.status == ComplianceStatus.MET

    def test_no_dep_tool(self, repo_root: Path) -> None:
        """Missing dependency update tool is a gap."""
        controls = evaluate_compliance(repo_root)
        dep = next(c for c in controls if c.id == 'OSPS-SCA-06')
        assert dep.status == ComplianceStatus.GAP


class TestNISTSSDF:
    """Tests for NIST SSDF mapping."""

    def test_all_controls_have_nist_or_empty(self, repo_root: Path) -> None:
        """Every control has a nist_ssdf field (may be empty for some)."""
        controls = evaluate_compliance(repo_root)
        for c in controls:
            assert isinstance(c.nist_ssdf, str)

    def test_sbom_maps_to_ps32(self, repo_root: Path) -> None:
        """SBOM control maps to NIST SSDF PS.3.2."""
        controls = evaluate_compliance(repo_root)
        sbom = next(c for c in controls if c.id == 'OSPS-SCA-01')
        assert sbom.nist_ssdf == 'PS.3.2'

    def test_signing_maps_to_ps21(self, repo_root: Path) -> None:
        """Signing control maps to NIST SSDF PS.2.1."""
        controls = evaluate_compliance(repo_root)
        sign = next(c for c in controls if c.id == 'OSPS-SCA-02')
        assert sign.nist_ssdf == 'PS.2.1'


class TestComplianceNotes:
    """Tests for compliance control notes."""

    def test_sbom_met_has_notes(self, repo_root: Path) -> None:
        """SBOM met control has format notes."""
        controls = evaluate_compliance(repo_root, has_sbom=True)
        sbom = next(c for c in controls if c.id == 'OSPS-SCA-01')
        assert 'CycloneDX' in sbom.notes

    def test_signing_met_has_notes(self, repo_root: Path) -> None:
        """Signing met control has Sigstore notes."""
        controls = evaluate_compliance(repo_root, has_signing=True)
        sign = next(c for c in controls if c.id == 'OSPS-SCA-02')
        assert 'Sigstore' in sign.notes

    def test_provenance_met_has_notes(self, repo_root: Path) -> None:
        """Provenance met control has SLSA notes."""
        controls = evaluate_compliance(repo_root, has_provenance=True)
        prov = next(c for c in controls if c.id == 'OSPS-SCA-03')
        assert 'SLSA' in prov.notes


class TestComplianceControl:
    """Tests for the ComplianceControl dataclass."""

    def test_frozen(self) -> None:
        """ComplianceControl is frozen."""
        c = ComplianceControl(
            id='TEST-01',
            control='Test control',
            osps_level=OSPSLevel.L1,
            status=ComplianceStatus.MET,
        )
        with pytest.raises(AttributeError):
            c.status = ComplianceStatus.GAP  # type: ignore[misc]

    def test_all_fields_populated(self) -> None:
        """All fields can be populated."""
        c = ComplianceControl(
            id='TEST-01',
            control='Test control',
            osps_level=OSPSLevel.L2,
            status=ComplianceStatus.PARTIAL,
            module='test.py',
            nist_ssdf='PS.1.1',
            notes='Some notes',
            hint='Do this to fix it.',
        )
        assert c.id == 'TEST-01'
        assert c.osps_level == OSPSLevel.L2
        assert c.module == 'test.py'
        assert c.notes == 'Some notes'
        assert c.hint == 'Do this to fix it.'


class TestComplianceHints:
    """Tests for actionable hints on gap/partial controls."""

    def test_all_gaps_have_hints(self, repo_root: Path) -> None:
        """Every gap control has a non-empty hint."""
        controls = evaluate_compliance(repo_root)
        for c in controls:
            if c.status == ComplianceStatus.GAP:
                assert c.hint, f'{c.id} is a gap but has no hint'

    def test_all_partials_have_hints(self, repo_root: Path) -> None:
        """Every partial control has a non-empty hint."""
        controls = evaluate_compliance(repo_root)
        for c in controls:
            if c.status == ComplianceStatus.PARTIAL:
                assert c.hint, f'{c.id} is partial but has no hint'

    def test_met_controls_have_no_hints(self, repo_root: Path) -> None:
        """Met controls have empty hints."""
        controls = evaluate_compliance(repo_root)
        for c in controls:
            if c.status == ComplianceStatus.MET:
                assert c.hint == '', f'{c.id} is met but has hint: {c.hint}'


class TestFormatComplianceTable:
    """Tests for Rust-style compliance table formatting."""

    def test_no_module_column(self, repo_root: Path) -> None:
        """Output does not contain a Module column header."""
        controls = evaluate_compliance(repo_root)
        output = format_compliance_table(controls)
        header_line = output.split('\n')[0]
        assert 'Module' not in header_line

    def test_has_error_diagnostics(self, repo_root: Path) -> None:
        """Output contains error[] diagnostics for gap controls."""
        controls = evaluate_compliance(repo_root)
        output = format_compliance_table(controls)
        assert 'error[' in output

    def test_has_help_hints(self, repo_root: Path) -> None:
        """Output contains = help: lines for gap/partial controls."""
        controls = evaluate_compliance(repo_root)
        output = format_compliance_table(controls)
        assert '= help:' in output

    def test_has_osps_baseline_reference(self, repo_root: Path) -> None:
        """Diagnostics reference OSPS Baseline level."""
        controls = evaluate_compliance(repo_root)
        output = format_compliance_table(controls)
        assert '--> OSPS Baseline L' in output

    def test_no_diagnostics_when_all_met(self, repo_root: Path) -> None:
        """No error/warning diagnostics when all controls are met."""
        (repo_root / 'SECURITY.md').write_text('# Security\n')
        (repo_root / 'LICENSE').write_text('Apache-2.0\n')
        (repo_root / 'uv.lock').write_text('# lock\n')
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'dependabot.yml').write_text('version: 2\n')
        controls = evaluate_compliance(
            repo_root,
            has_signing=True,
            has_provenance=True,
            has_sbom=True,
            has_vuln_scanning=True,
            has_slsa_l3=True,
            ecosystems=frozenset(),
        )
        output = format_compliance_table(controls)
        assert 'error[' not in output
        assert 'warning[' not in output


class TestComplianceStatus:
    """Tests for ComplianceStatus enum."""

    def test_values(self) -> None:
        """Status values are correct strings."""
        assert ComplianceStatus.MET.value == 'met'
        assert ComplianceStatus.PARTIAL.value == 'partial'
        assert ComplianceStatus.GAP.value == 'gap'


class TestOSPSLevel:
    """Tests for OSPSLevel enum."""

    def test_values(self) -> None:
        """Level values are correct integers."""
        assert OSPSLevel.L1.value == 1
        assert OSPSLevel.L2.value == 2
        assert OSPSLevel.L3.value == 3
