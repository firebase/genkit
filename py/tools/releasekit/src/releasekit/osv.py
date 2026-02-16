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

r"""OSV vulnerability checking for release dependencies.

Queries the `OSV.dev API`_ for known vulnerabilities in workspace
dependencies before publishing.  Complements ``pip-audit`` (Python-only)
with a universal vulnerability database covering all ecosystems.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ OSV                 │ Open Source Vulnerabilities — a universal     │
    │                     │ database of known security bugs.              │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ PURL                │ Package URL — a standard way to identify a   │
    │                     │ package (e.g. pkg:pypi/requests@2.31.0).     │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Severity threshold  │ Only vulnerabilities at or above this level  │
    │                     │ are reported (CRITICAL, HIGH, MEDIUM, LOW).  │
    └─────────────────────┴────────────────────────────────────────────────┘

Query flow::

    check_osv_vulnerabilities(purls)
         │
         ├── POST https://api.osv.dev/v1/querybatch
         │   body: { "queries": [{"package": {"purl": "pkg:pypi/foo@1.0"}}] }
         ├── Parse response: list of vulnerability matches per query
         ├── Filter by severity threshold
         └── Return list of OSVVulnerability results

Usage::

    from releasekit.osv import check_osv_vulnerabilities, OSVSeverity

    vulns = await check_osv_vulnerabilities(
        purls=['pkg:pypi/requests@2.31.0', 'pkg:npm/lodash@4.17.21'],
        severity_threshold=OSVSeverity.HIGH,
    )
    for v in vulns:
        print(f'{v.purl}: {v.id} ({v.severity}) — {v.summary}')

.. _OSV.dev API: https://osv.dev/docs/
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

import httpx

from releasekit.logging import get_logger

logger = get_logger(__name__)

# OSV batch query endpoint.
_OSV_BATCH_URL = 'https://api.osv.dev/v1/querybatch'

# HTTP timeout for OSV API calls.
_OSV_TIMEOUT: float = 30.0


class OSVSeverity(enum.IntEnum):
    """Vulnerability severity levels, ordered from lowest to highest."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


def _parse_severity(vuln: dict[str, Any]) -> OSVSeverity:
    """Extract the highest severity from an OSV vulnerability record.

    OSV vulnerabilities may have multiple severity entries (CVSS v2, v3,
    ecosystem-specific). We take the highest.

    Args:
        vuln: An OSV vulnerability dict.

    Returns:
        The highest :class:`OSVSeverity`, defaulting to ``MEDIUM``.
    """
    severity_entries = vuln.get('severity', [])
    if not severity_entries:
        # Check database_specific for ecosystem severity.
        db_specific = vuln.get('database_specific', {})
        raw = db_specific.get('severity', '').upper()
        if raw in OSVSeverity.__members__:
            return OSVSeverity[raw]
        return OSVSeverity.MEDIUM

    max_severity = OSVSeverity.LOW
    for entry in severity_entries:
        score_str = entry.get('score', '')
        # CVSS v3 score ranges.
        try:
            score = float(score_str) if score_str else 0.0
        except (ValueError, TypeError):
            score = 0.0

        if score >= 9.0:
            max_severity = max(max_severity, OSVSeverity.CRITICAL)
        elif score >= 7.0:
            max_severity = max(max_severity, OSVSeverity.HIGH)
        elif score >= 4.0:
            max_severity = max(max_severity, OSVSeverity.MEDIUM)
        else:
            max_severity = max(max_severity, OSVSeverity.LOW)

    return max_severity


@dataclass(frozen=True)
class OSVVulnerability:
    """A single vulnerability found by OSV.

    Attributes:
        purl: The Package URL that matched.
        id: The OSV vulnerability ID (e.g. ``'GHSA-xxxx-xxxx-xxxx'``).
        summary: Short description of the vulnerability.
        severity: Parsed severity level.
        aliases: Alternative IDs (CVE numbers, etc.).
        details_url: URL to the full vulnerability report.
    """

    purl: str
    id: str
    summary: str = ''
    severity: OSVSeverity = OSVSeverity.MEDIUM
    aliases: list[str] = field(default_factory=list)
    details_url: str = ''


async def check_osv_vulnerabilities(
    purls: list[str],
    *,
    severity_threshold: OSVSeverity = OSVSeverity.HIGH,
    timeout: float = _OSV_TIMEOUT,
) -> list[OSVVulnerability]:
    """Query OSV for known vulnerabilities in the given packages.

    Args:
        purls: List of Package URLs to check.
        severity_threshold: Only return vulnerabilities at or above
            this severity level.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of :class:`OSVVulnerability` at or above the threshold.
        Returns an empty list if the API is unreachable (fail-open
        with a warning).
    """
    if not purls:
        return []

    queries = [{'package': {'purl': purl}} for purl in purls]
    payload = {'queries': queries}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(_OSV_BATCH_URL, json=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            'osv_query_failed',
            error=str(exc),
            purl_count=len(purls),
        )
        return []

    results: list[OSVVulnerability] = []
    batch_results = data.get('results', [])

    for i, query_result in enumerate(batch_results):
        purl = purls[i] if i < len(purls) else 'unknown'
        vulns = query_result.get('vulns', [])

        for vuln in vulns:
            severity = _parse_severity(vuln)
            if severity < severity_threshold:
                continue

            vuln_id = vuln.get('id', 'UNKNOWN')
            results.append(
                OSVVulnerability(
                    purl=purl,
                    id=vuln_id,
                    summary=vuln.get('summary', ''),
                    severity=severity,
                    aliases=vuln.get('aliases', []),
                    details_url=f'https://osv.dev/vulnerability/{vuln_id}',
                )
            )

    if results:
        logger.warning(
            'osv_vulnerabilities_found',
            count=len(results),
            critical=sum(1 for v in results if v.severity == OSVSeverity.CRITICAL),
            high=sum(1 for v in results if v.severity == OSVSeverity.HIGH),
        )
    else:
        logger.info('osv_no_vulnerabilities', purl_count=len(purls))

    return results


__all__ = [
    'OSVSeverity',
    'OSVVulnerability',
    'check_osv_vulnerabilities',
]
