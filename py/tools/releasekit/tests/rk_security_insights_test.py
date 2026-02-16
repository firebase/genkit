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

"""Tests for SECURITY-INSIGHTS.yml generation."""

from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from releasekit.security_insights import (
    Contact,
    SecurityInsightsConfig,
    SecurityInsightsResult,
    SecurityTool,
    default_security_tools,
    generate_security_insights,
)

# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------


class TestContact:
    """Tests for the Contact dataclass."""

    def test_minimal_contact(self) -> None:
        """Minimal contact has only name and primary."""
        c = Contact(name='Alice')
        d = c.to_dict()
        assert d['name'] == 'Alice'
        assert d['primary'] is False
        assert 'email' not in d
        assert 'affiliation' not in d
        assert 'social' not in d

    def test_full_contact(self) -> None:
        """Full contact includes all optional fields."""
        c = Contact(
            name='Bob',
            email='bob@example.com',
            affiliation='ACME',
            social='https://social.example.com/bob',
            primary=True,
        )
        d = c.to_dict()
        assert d['name'] == 'Bob'
        assert d['email'] == 'bob@example.com'
        assert d['affiliation'] == 'ACME'
        assert d['social'] == 'https://social.example.com/bob'
        assert d['primary'] is True


# ---------------------------------------------------------------------------
# SecurityTool
# ---------------------------------------------------------------------------


class TestSecurityTool:
    """Tests for the SecurityTool dataclass."""

    def test_minimal_tool(self) -> None:
        """Minimal tool has name, type, and default integration."""
        t = SecurityTool(name='ruff', tool_type='SAST')
        d = t.to_dict()
        assert d['name'] == 'ruff'
        assert d['type'] == 'SAST'
        assert d['rulesets'] == 'default'
        assert d['integration']['ci'] is True
        assert d['integration']['release'] is False
        assert d['integration']['adhoc'] is False
        assert 'version' not in d
        assert 'comment' not in d

    def test_full_tool(self) -> None:
        """Full tool includes version, comment, and all integrations."""
        t = SecurityTool(
            name='Dependabot',
            tool_type='SCA',
            rulesets='built-in',
            integration_ci=True,
            integration_release=True,
            integration_adhoc=True,
            version='1.2.3',
            comment='Dependency scanning.',
        )
        d = t.to_dict()
        assert d['version'] == '1.2.3'
        assert d['comment'] == 'Dependency scanning.'
        assert d['integration']['adhoc'] is True
        assert d['integration']['release'] is True


# ---------------------------------------------------------------------------
# SecurityInsightsConfig defaults
# ---------------------------------------------------------------------------


class TestSecurityInsightsConfig:
    """Tests for SecurityInsightsConfig defaults."""

    def test_defaults(self) -> None:
        """Default config has sensible values."""
        cfg = SecurityInsightsConfig()
        assert cfg.project_name == ''
        assert cfg.license_expression == 'Apache-2.0'
        assert cfg.reports_accepted is True
        assert cfg.bug_bounty_available is False
        assert cfg.status == 'active'
        assert cfg.automated_pipeline is True


# ---------------------------------------------------------------------------
# generate_security_insights
# ---------------------------------------------------------------------------


class TestGenerateSecurityInsights:
    """Tests for SECURITY-INSIGHTS.yml generation."""

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run builds data but doesn't write file."""
        cfg = SecurityInsightsConfig(project_name='TestProject')
        out = tmp_path / 'SECURITY-INSIGHTS.yml'
        result = generate_security_insights(cfg, output_path=out, dry_run=True)
        assert not result.generated
        assert 'dry-run' in result.reason
        assert result.data
        assert not out.exists()

    def test_generates_yaml_file(self, tmp_path: Path) -> None:
        """Generates a valid YAML file."""
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
        out = tmp_path / 'SECURITY-INSIGHTS.yml'
        result = generate_security_insights(cfg, output_path=out)
        assert result.generated
        assert out.exists()
        content = out.read_text(encoding='utf-8')
        assert 'GenKit' in content
        assert 'schema-version' in content

    def test_default_output_path(self) -> None:
        """Default output path is SECURITY-INSIGHTS.yml."""
        cfg = SecurityInsightsConfig(project_name='Test')
        result = generate_security_insights(cfg, dry_run=True)
        assert result.output_path == Path('SECURITY-INSIGHTS.yml')

    def test_minimal_config(self, tmp_path: Path) -> None:
        """Minimal config still produces valid output."""
        cfg = SecurityInsightsConfig()
        out = tmp_path / 'si.yml'
        result = generate_security_insights(cfg, output_path=out)
        assert result.generated
        assert result.data['project']['name'] == 'Unknown Project'

    def test_with_security_contact(self, tmp_path: Path) -> None:
        """Security contact is included in vulnerability reporting."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            security_contact=Contact(
                name='Security Team',
                email='security@example.com',
                primary=True,
            ),
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        vuln = result.data['project']['vulnerability-reporting']
        assert vuln['contact']['name'] == 'Security Team'

    def test_with_vuln_reporting_url(self, tmp_path: Path) -> None:
        """Vulnerability reporting URL is included."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            vulnerability_reporting_url='https://example.com/security',
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        vuln = result.data['project']['vulnerability-reporting']
        assert vuln['policy'] == 'https://example.com/security'

    def test_with_security_policy_url(self, tmp_path: Path) -> None:
        """Security policy URL is in repository documentation."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            repo_url='https://github.com/test/test',
            security_policy_url='https://example.com/security-policy',
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        docs = result.data['repository'].get('documentation', {})
        assert docs['security-policy'] == 'https://example.com/security-policy'

    def test_with_changelog_url(self, tmp_path: Path) -> None:
        """Changelog URL is in release section."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            changelog_url='https://example.com/CHANGELOG',
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        release = result.data['repository']['release']
        assert release['changelog'] == 'https://example.com/CHANGELOG'

    def test_with_distribution_points(self, tmp_path: Path) -> None:
        """Custom distribution points are included."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            distribution_points=[
                {'uri': 'https://pypi.org/project/test/', 'comment': 'PyPI'},
            ],
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        dps = result.data['repository']['release']['distribution-points']
        assert dps[0]['uri'] == 'https://pypi.org/project/test/'

    def test_attestations_always_present(self, tmp_path: Path) -> None:
        """SLSA and PEP 740 attestations are always in release section."""
        cfg = SecurityInsightsConfig(project_name='Test')
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        attestations = result.data['repository']['release']['attestations']
        names = [a['name'] for a in attestations]
        assert 'SLSA Provenance' in names
        assert 'PEP 740 Publish Attestation' in names

    def test_yaml_import_error_fallback_json(self, tmp_path: Path) -> None:
        """Falls back to JSON when PyYAML is not available."""
        cfg = SecurityInsightsConfig(project_name='FallbackTest')
        out = tmp_path / 'si.yml'

        real_import = builtins.__import__
        saved_yaml = sys.modules.pop('yaml', None)

        def _block_yaml(name: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            if name == 'yaml':
                raise ImportError('no yaml')
            return real_import(name, *args, **kwargs)

        builtins.__import__ = _block_yaml  # type: ignore[assignment]
        try:
            result = generate_security_insights(cfg, output_path=out)
        finally:
            builtins.__import__ = real_import
            if saved_yaml is not None:
                sys.modules['yaml'] = saved_yaml

        assert result.generated
        assert 'JSON' in result.reason
        # Should be valid JSON.
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['project']['name'] == 'FallbackTest'

    def test_write_error_returns_reason(self, tmp_path: Path) -> None:
        """Write error returns a reason."""
        cfg = SecurityInsightsConfig(project_name='Test')
        # Use a path that can't be written to.
        out = tmp_path / 'nonexistent_dir' / 'deep' / 'si.yml'
        # This should succeed because mkdir(parents=True) is called.
        result = generate_security_insights(cfg, output_path=out)
        assert result.generated

    def test_custom_dates(self, tmp_path: Path) -> None:
        """Custom last-updated and last-reviewed dates."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            last_updated='2025-01-01',
            last_reviewed='2025-02-01',
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        header = result.data['header']
        assert header['last-updated'] == '2025-01-01'
        assert header['last-reviewed'] == '2025-02-01'

    def test_si_url_in_header(self, tmp_path: Path) -> None:
        """SI URL is included in header."""
        cfg = SecurityInsightsConfig(
            project_name='Test',
            si_url='https://example.com/SECURITY-INSIGHTS.yml',
        )
        result = generate_security_insights(cfg, output_path=tmp_path / 'si.yml')
        assert result.data['header']['url'] == 'https://example.com/SECURITY-INSIGHTS.yml'


# ---------------------------------------------------------------------------
# default_security_tools
# ---------------------------------------------------------------------------


class TestDefaultSecurityTools:
    """Tests for the default security tools list."""

    def test_returns_list(self) -> None:
        """Returns a non-empty list of SecurityTool."""
        tools = default_security_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 4

    def test_tool_names(self) -> None:
        """Default tools include Sigstore, OSV, ruff, pip-audit."""
        tools = default_security_tools()
        names = {t.name for t in tools}
        assert 'Sigstore' in names
        assert 'OSV' in names
        assert 'ruff' in names
        assert 'pip-audit' in names

    def test_all_have_type(self) -> None:
        """All default tools have a tool_type."""
        tools = default_security_tools()
        for t in tools:
            assert t.tool_type, f'{t.name} missing tool_type'


# ---------------------------------------------------------------------------
# SecurityInsightsResult
# ---------------------------------------------------------------------------


class TestSecurityInsightsResult:
    """Tests for the SecurityInsightsResult dataclass."""

    def test_default_values(self) -> None:
        """Default result is not generated."""
        result = SecurityInsightsResult()
        assert not result.generated
        assert result.reason == ''
        assert result.data == {}

    def test_frozen(self) -> None:
        """SecurityInsightsResult is frozen."""
        result = SecurityInsightsResult()
        with pytest.raises(AttributeError):
            result.generated = True  # type: ignore[misc]
