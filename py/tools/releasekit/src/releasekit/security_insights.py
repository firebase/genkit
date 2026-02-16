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

r"""SECURITY-INSIGHTS.yml generation per the OpenSSF Security Insights v2 spec.

Generates a machine-readable ``SECURITY-INSIGHTS.yml`` file that
communicates a project's security posture to consumers, security
researchers, and automated tools (CLOMonitor, LFX Insights, OSPS
Baseline Scanner).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Security Insights   │ OpenSSF standard for machine-readable         │
    │                     │ security metadata (YAML file in repo root).   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Header              │ Schema version, last-updated, URL.            │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Project             │ Name, admins, repos, vuln reporting policy.   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Repository          │ Status, team, license, release details,       │
    │                     │ security posture (tools, assessments).        │
    └─────────────────────┴────────────────────────────────────────────────┘

Generation flow::

    generate_security_insights(config)
         │
         ├── Build header (schema-version, dates, URL)
         ├── Build project section (name, admins, repos, vuln reporting)
         ├── Build repository section (status, team, license, release,
         │   security posture with tools)
         ├── Serialize to YAML
         └── Return SecurityInsightsResult

.. _Security Insights: https://github.com/ossf/security-insights
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from releasekit.logging import get_logger
from releasekit.utils.date import utc_today

logger = get_logger(__name__)

# Schema version we generate.
SCHEMA_VERSION = '2.0.0'


@dataclass(frozen=True)
class Contact:
    """A person or entity contact.

    Attributes:
        name: Contact person's name.
        email: Contact email address.
        affiliation: Organization affiliation.
        social: Social media handle or profile URL.
        primary: Whether this is the primary contact.
    """

    name: str
    email: str = ''
    affiliation: str = ''
    social: str = ''
    primary: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for YAML output."""
        d: dict[str, Any] = {'name': self.name, 'primary': self.primary}
        if self.email:
            d['email'] = self.email
        if self.affiliation:
            d['affiliation'] = self.affiliation
        if self.social:
            d['social'] = self.social
        return d


@dataclass(frozen=True)
class SecurityTool:
    """A security tool used in the repository.

    Attributes:
        name: Tool name (e.g. ``"Dependabot"``, ``"ruff"``).
        tool_type: Category (e.g. ``"SCA"``, ``"SAST"``, ``"linter"``).
        rulesets: Rule configuration (e.g. ``"default"``, ``"built-in"``).
        integration_ci: Whether the tool runs in CI.
        integration_release: Whether the tool runs during release.
        integration_adhoc: Whether the tool supports on-demand runs.
        version: Tool version string.
        comment: Additional notes.
    """

    name: str
    tool_type: str
    rulesets: str = 'default'
    integration_ci: bool = True
    integration_release: bool = False
    integration_adhoc: bool = False
    version: str = ''
    comment: str = ''

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for YAML output."""
        d: dict[str, Any] = {
            'name': self.name,
            'type': self.tool_type,
            'rulesets': self.rulesets,
            'integration': {
                'adhoc': self.integration_adhoc,
                'ci': self.integration_ci,
                'release': self.integration_release,
            },
            'results': {},
        }
        if self.version:
            d['version'] = self.version
        if self.comment:
            d['comment'] = self.comment
        return d


@dataclass
class SecurityInsightsConfig:
    """Configuration for generating SECURITY-INSIGHTS.yml.

    Attributes:
        project_name: Project display name.
        project_url: Project homepage or repository URL.
        repo_url: Repository URL.
        si_url: Canonical URL for the security-insights.yml file.
        administrators: Project administrators.
        core_team: Repository core team members.
        license_url: URL to the LICENSE file.
        license_expression: SPDX license expression.
        vulnerability_reporting_url: URL to vulnerability reporting policy.
        reports_accepted: Whether vulnerability reports are accepted.
        bug_bounty_available: Whether a bug bounty program exists.
        security_contact: Security contact for vulnerability reports.
        security_policy_url: URL to security policy.
        status: Repository status (``"active"``, ``"inactive"``, etc.).
        accepts_change_request: Whether the repo accepts change requests.
        accepts_automated_change_request: Whether automated PRs are accepted.
        automated_pipeline: Whether releases use an automated pipeline.
        changelog_url: URL to changelog.
        distribution_points: List of distribution point dicts.
        security_tools: Security tools used in the repository.
        assessment_comment: Self-assessment comment.
        last_updated: ISO date string for last-updated.
        last_reviewed: ISO date string for last-reviewed.
    """

    project_name: str = ''
    project_url: str = ''
    repo_url: str = ''
    si_url: str = ''
    administrators: list[Contact] = field(default_factory=list)
    core_team: list[Contact] = field(default_factory=list)
    license_url: str = ''
    license_expression: str = 'Apache-2.0'
    vulnerability_reporting_url: str = ''
    reports_accepted: bool = True
    bug_bounty_available: bool = False
    security_contact: Contact | None = None
    security_policy_url: str = ''
    status: str = 'active'
    accepts_change_request: bool = True
    accepts_automated_change_request: bool = True
    automated_pipeline: bool = True
    changelog_url: str = ''
    distribution_points: list[dict[str, str]] = field(default_factory=list)
    security_tools: list[SecurityTool] = field(default_factory=list)
    assessment_comment: str = 'Self assessment has not yet been completed.'
    last_updated: str = ''
    last_reviewed: str = ''


@dataclass(frozen=True)
class SecurityInsightsResult:
    """Result of SECURITY-INSIGHTS.yml generation.

    Attributes:
        output_path: Path to the generated file.
        generated: Whether the file was successfully generated.
        reason: Human-readable reason if generation was skipped or failed.
        data: The generated data dict (for validation).
    """

    output_path: Path = field(default_factory=Path)
    generated: bool = False
    reason: str = ''
    data: dict[str, Any] = field(default_factory=dict)


def _build_header(config: SecurityInsightsConfig) -> dict[str, Any]:
    """Build the header section."""
    header: dict[str, Any] = {
        'schema-version': SCHEMA_VERSION,
        'last-updated': config.last_updated or utc_today(),
        'last-reviewed': config.last_reviewed or utc_today(),
    }
    if config.si_url:
        header['url'] = config.si_url
    return header


def _build_project(config: SecurityInsightsConfig) -> dict[str, Any]:
    """Build the project section."""
    project: dict[str, Any] = {
        'name': config.project_name or 'Unknown Project',
    }

    # Administrators.
    if config.administrators:
        project['administrators'] = [a.to_dict() for a in config.administrators]
    else:
        project['administrators'] = [
            {'name': 'Project Maintainer', 'primary': True},
        ]

    # Repositories.
    repos = []
    if config.repo_url:
        repos.append({
            'name': config.project_name or 'main',
            'url': config.repo_url,
            'comment': 'Primary repository.',
        })
    project['repositories'] = repos or [
        {'name': 'main', 'url': config.project_url or '', 'comment': 'Primary repository.'},
    ]

    # Vulnerability reporting.
    vuln: dict[str, Any] = {
        'reports-accepted': config.reports_accepted,
        'bug-bounty-available': config.bug_bounty_available,
    }
    if config.vulnerability_reporting_url:
        vuln['policy'] = config.vulnerability_reporting_url
    if config.security_contact:
        vuln['contact'] = config.security_contact.to_dict()
    project['vulnerability-reporting'] = vuln

    return project


def _build_repository(config: SecurityInsightsConfig) -> dict[str, Any]:
    """Build the repository section."""
    repo: dict[str, Any] = {
        'url': config.repo_url or config.project_url or '',
        'status': config.status,
        'accepts-change-request': config.accepts_change_request,
        'accepts-automated-change-request': config.accepts_automated_change_request,
    }

    # Core team.
    if config.core_team:
        repo['core-team'] = [c.to_dict() for c in config.core_team]
    else:
        repo['core-team'] = [
            {'name': 'Project Maintainer', 'primary': True},
        ]

    # Documentation.
    docs: dict[str, str] = {}
    if config.security_policy_url:
        docs['security-policy'] = config.security_policy_url
    if docs:
        repo['documentation'] = docs

    # License.
    repo['license'] = {
        'url': config.license_url or f'{config.repo_url}/blob/main/LICENSE' if config.repo_url else '',
        'expression': config.license_expression,
    }

    # Release.
    release: dict[str, Any] = {
        'automated-pipeline': config.automated_pipeline,
    }
    if config.changelog_url:
        release['changelog'] = config.changelog_url
    if config.distribution_points:
        release['distribution-points'] = config.distribution_points
    else:
        release['distribution-points'] = [
            {'uri': config.repo_url or '', 'comment': 'Repository releases'},
        ]

    # Attestations.
    attestations = []
    attestations.append({
        'name': 'SLSA Provenance',
        'predicate-uri': 'https://slsa.dev/provenance/v1',
        'location': f'{config.repo_url}/releases' if config.repo_url else '',
        'comment': 'SLSA Provenance v1 attestation for release artifacts.',
    })
    attestations.append({
        'name': 'PEP 740 Publish Attestation',
        'predicate-uri': 'https://docs.pypi.org/attestations/publish/v1',
        'location': f'{config.repo_url}/releases' if config.repo_url else '',
        'comment': 'PEP 740 digital attestation for PyPI distributions.',
    })
    release['attestations'] = attestations
    repo['release'] = release

    # Security posture.
    security: dict[str, Any] = {
        'assessments': {
            'self': {
                'comment': config.assessment_comment,
            },
        },
    }
    if config.security_tools:
        security['tools'] = [t.to_dict() for t in config.security_tools]
    repo['security'] = security

    return repo


def generate_security_insights(
    config: SecurityInsightsConfig,
    *,
    output_path: Path | None = None,
    dry_run: bool = False,
) -> SecurityInsightsResult:
    """Generate a SECURITY-INSIGHTS.yml file.

    Args:
        config: Configuration for the security insights file.
        output_path: Path to write the file. If ``None``, defaults to
            ``SECURITY-INSIGHTS.yml`` in the current directory.
        dry_run: If ``True``, build the data but don't write the file.

    Returns:
        A :class:`SecurityInsightsResult` with the outcome.
    """
    if output_path is None:
        output_path = Path('SECURITY-INSIGHTS.yml')

    data: dict[str, Any] = {
        'header': _build_header(config),
        'project': _build_project(config),
        'repository': _build_repository(config),
    }

    if dry_run:
        logger.info(
            'security_insights_dry_run',
            output=str(output_path),
        )
        return SecurityInsightsResult(
            output_path=output_path,
            reason='dry-run: would generate SECURITY-INSIGHTS.yml',
            data=data,
        )

    try:
        import yaml  # Lazy import: allows JSON fallback when PyYAML is absent.

        yaml_str = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_str, encoding='utf-8')

        logger.info(
            'security_insights_generated',
            output=str(output_path),
        )
        return SecurityInsightsResult(
            output_path=output_path,
            generated=True,
            data=data,
        )
    except ImportError:
        # Fallback: write as JSON if PyYAML is not available.
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding='utf-8')

        logger.info(
            'security_insights_generated_json_fallback',
            output=str(output_path),
        )
        return SecurityInsightsResult(
            output_path=output_path,
            generated=True,
            reason='Generated as JSON (PyYAML not installed).',
            data=data,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            'security_insights_failed',
            error=str(exc),
        )
        return SecurityInsightsResult(
            output_path=output_path,
            reason=f'Generation failed: {exc}',
            data=data,
        )


def default_security_tools() -> list[SecurityTool]:
    """Return the default set of security tools for a releasekit-managed project.

    These represent the tools that releasekit integrates with or
    generates output for.
    """
    return [
        SecurityTool(
            name='Sigstore',
            tool_type='signing',
            rulesets='default',
            integration_ci=True,
            integration_release=True,
            comment='Keyless artifact signing via Sigstore OIDC.',
        ),
        SecurityTool(
            name='OSV',
            tool_type='SCA',
            rulesets='default',
            integration_ci=True,
            integration_release=True,
            comment='OSV vulnerability scanning for dependencies.',
        ),
        SecurityTool(
            name='ruff',
            tool_type='SAST',
            rulesets='built-in',
            integration_ci=True,
            integration_adhoc=True,
            comment='Python linter with security rules (bandit/S rules).',
        ),
        SecurityTool(
            name='pip-audit',
            tool_type='SCA',
            rulesets='default',
            integration_ci=True,
            integration_release=True,
            comment='Python dependency vulnerability auditing.',
        ),
    ]


__all__ = [
    'Contact',
    'SecurityInsightsConfig',
    'SecurityInsightsResult',
    'SecurityTool',
    'default_security_tools',
    'generate_security_insights',
]
