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

"""Tests for OSV vulnerability checking.

Validates the OSV API client and vulnerability parsing in
:mod:`releasekit.osv`.

Key Concepts::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ What We Test                                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Batch query         │ Multiple purls queried in one API call        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Severity parsing    │ CVSS scores mapped to OSVSeverity levels     │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Threshold filter    │ Only vulns at/above threshold are returned    │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Network failure     │ API errors return empty list (fail-open)      │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    test → mock httpx.AsyncClient → check_osv_vulnerabilities() → assert results
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from releasekit.osv import (
    OSVSeverity,
    OSVVulnerability,
    _parse_severity,
    check_osv_vulnerabilities,
)


class TestOSVSeverity:
    """Tests for severity level ordering."""

    def test_ordering(self) -> None:
        """Severity levels are ordered LOW < MEDIUM < HIGH < CRITICAL."""
        assert OSVSeverity.LOW < OSVSeverity.MEDIUM
        assert OSVSeverity.MEDIUM < OSVSeverity.HIGH
        assert OSVSeverity.HIGH < OSVSeverity.CRITICAL

    def test_int_values(self) -> None:
        """Severity levels have expected integer values."""
        assert int(OSVSeverity.LOW) == 1
        assert int(OSVSeverity.CRITICAL) == 4


class TestParseSeverity:
    """Tests for vulnerability severity parsing."""

    def test_critical_cvss(self) -> None:
        """CVSS score >= 9.0 maps to CRITICAL."""
        vuln = {'severity': [{'score': '9.8'}]}
        assert _parse_severity(vuln) == OSVSeverity.CRITICAL

    def test_high_cvss(self) -> None:
        """CVSS score >= 7.0 maps to HIGH."""
        vuln = {'severity': [{'score': '7.5'}]}
        assert _parse_severity(vuln) == OSVSeverity.HIGH

    def test_medium_cvss(self) -> None:
        """CVSS score >= 4.0 maps to MEDIUM."""
        vuln = {'severity': [{'score': '5.3'}]}
        assert _parse_severity(vuln) == OSVSeverity.MEDIUM

    def test_low_cvss(self) -> None:
        """CVSS score < 4.0 maps to LOW."""
        vuln = {'severity': [{'score': '2.1'}]}
        assert _parse_severity(vuln) == OSVSeverity.LOW

    def test_no_severity_defaults_medium(self) -> None:
        """Missing severity defaults to MEDIUM."""
        vuln = {}
        assert _parse_severity(vuln) == OSVSeverity.MEDIUM

    def test_database_specific_severity(self) -> None:
        """database_specific.severity is used as fallback."""
        vuln = {'database_specific': {'severity': 'HIGH'}}
        assert _parse_severity(vuln) == OSVSeverity.HIGH

    def test_multiple_scores_takes_highest(self) -> None:
        """Multiple CVSS entries: highest severity wins."""
        vuln = {'severity': [{'score': '3.0'}, {'score': '8.5'}]}
        assert _parse_severity(vuln) == OSVSeverity.HIGH

    def test_invalid_cvss_score_string(self) -> None:
        """Non-numeric CVSS score string falls back to 0.0 (LOW)."""
        vuln = {'severity': [{'score': 'not-a-number'}]}
        assert _parse_severity(vuln) == OSVSeverity.LOW

    def test_empty_score_string(self) -> None:
        """Empty CVSS score string falls back to 0.0 (LOW)."""
        vuln = {'severity': [{'score': ''}]}
        assert _parse_severity(vuln) == OSVSeverity.LOW

    def test_none_score(self) -> None:
        """None score falls back to 0.0 (LOW)."""
        vuln = {'severity': [{'score': None}]}
        assert _parse_severity(vuln) == OSVSeverity.LOW

    def test_missing_score_key(self) -> None:
        """Missing 'score' key in severity entry falls back to 0.0."""
        vuln = {'severity': [{'type': 'CVSS_V3'}]}
        assert _parse_severity(vuln) == OSVSeverity.LOW

    def test_database_specific_unknown_severity(self) -> None:
        """Unknown database_specific severity defaults to MEDIUM."""
        vuln = {'database_specific': {'severity': 'UNKNOWN'}}
        assert _parse_severity(vuln) == OSVSeverity.MEDIUM

    def test_database_specific_low(self) -> None:
        """database_specific severity LOW is parsed."""
        vuln = {'database_specific': {'severity': 'LOW'}}
        assert _parse_severity(vuln) == OSVSeverity.LOW

    def test_database_specific_critical(self) -> None:
        """database_specific severity CRITICAL is parsed."""
        vuln = {'database_specific': {'severity': 'CRITICAL'}}
        assert _parse_severity(vuln) == OSVSeverity.CRITICAL

    def test_boundary_score_9_0(self) -> None:
        """Score exactly 9.0 maps to CRITICAL."""
        vuln = {'severity': [{'score': '9.0'}]}
        assert _parse_severity(vuln) == OSVSeverity.CRITICAL

    def test_boundary_score_7_0(self) -> None:
        """Score exactly 7.0 maps to HIGH."""
        vuln = {'severity': [{'score': '7.0'}]}
        assert _parse_severity(vuln) == OSVSeverity.HIGH

    def test_boundary_score_4_0(self) -> None:
        """Score exactly 4.0 maps to MEDIUM."""
        vuln = {'severity': [{'score': '4.0'}]}
        assert _parse_severity(vuln) == OSVSeverity.MEDIUM

    def test_boundary_score_3_9(self) -> None:
        """Score 3.9 maps to LOW."""
        vuln = {'severity': [{'score': '3.9'}]}
        assert _parse_severity(vuln) == OSVSeverity.LOW


class TestOSVVulnerability:
    """Tests for the OSVVulnerability dataclass."""

    def test_default_values(self) -> None:
        """Default vulnerability has expected defaults."""
        v = OSVVulnerability(purl='pkg:pypi/foo@1.0', id='GHSA-1234')
        assert v.severity == OSVSeverity.MEDIUM
        assert v.aliases == []
        assert v.summary == ''

    def test_details_url(self) -> None:
        """details_url is constructed correctly."""
        v = OSVVulnerability(
            purl='pkg:pypi/foo@1.0',
            id='GHSA-1234',
            details_url='https://osv.dev/vulnerability/GHSA-1234',
        )
        assert 'GHSA-1234' in v.details_url

    def test_with_aliases(self) -> None:
        """Vulnerability with aliases stores them."""
        v = OSVVulnerability(
            purl='pkg:pypi/foo@1.0',
            id='GHSA-1234',
            aliases=['CVE-2024-1234', 'PYSEC-2024-1'],
        )
        assert len(v.aliases) == 2
        assert 'CVE-2024-1234' in v.aliases

    def test_frozen(self) -> None:
        """OSVVulnerability is frozen."""
        v = OSVVulnerability(purl='pkg:pypi/foo@1.0', id='GHSA-1234')
        with pytest.raises(AttributeError):
            v.id = 'changed'  # type: ignore[misc]


@pytest.mark.asyncio()
class TestCheckOSVVulnerabilities:
    """Tests for the OSV batch query function."""

    async def test_empty_purls(self) -> None:
        """Empty purl list returns empty results."""
        result = await check_osv_vulnerabilities([])
        assert result == []

    async def test_no_vulnerabilities(self) -> None:
        """Clean packages return empty results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [{'vulns': []}, {'vulns': []}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('releasekit.osv.httpx.AsyncClient', return_value=mock_client):
            result = await check_osv_vulnerabilities(
                ['pkg:pypi/safe@1.0', 'pkg:npm/clean@2.0'],
            )

        assert result == []

    async def test_vulnerabilities_found(self) -> None:
        """Vulnerabilities above threshold are returned."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'vulns': [
                        {
                            'id': 'GHSA-critical',
                            'summary': 'Critical vuln',
                            'severity': [{'score': '9.8'}],
                            'aliases': ['CVE-2024-1234'],
                        },
                    ],
                },
                {
                    'vulns': [
                        {
                            'id': 'GHSA-low',
                            'summary': 'Low vuln',
                            'severity': [{'score': '2.0'}],
                        },
                    ],
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('releasekit.osv.httpx.AsyncClient', return_value=mock_client):
            result = await check_osv_vulnerabilities(
                ['pkg:pypi/vuln@1.0', 'pkg:pypi/low@1.0'],
                severity_threshold=OSVSeverity.HIGH,
            )

        # Only the critical vuln should be returned (LOW is below threshold).
        assert len(result) == 1
        assert result[0].id == 'GHSA-critical'
        assert result[0].severity == OSVSeverity.CRITICAL
        assert 'CVE-2024-1234' in result[0].aliases

    async def test_medium_threshold(self) -> None:
        """MEDIUM threshold returns MEDIUM, HIGH, and CRITICAL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'vulns': [
                        {
                            'id': 'GHSA-med',
                            'summary': 'Medium vuln',
                            'severity': [{'score': '5.0'}],
                        },
                        {
                            'id': 'GHSA-low',
                            'summary': 'Low vuln',
                            'severity': [{'score': '1.0'}],
                        },
                    ],
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('releasekit.osv.httpx.AsyncClient', return_value=mock_client):
            result = await check_osv_vulnerabilities(
                ['pkg:pypi/mixed@1.0'],
                severity_threshold=OSVSeverity.MEDIUM,
            )

        assert len(result) == 1
        assert result[0].id == 'GHSA-med'

    async def test_network_error_returns_empty(self) -> None:
        """Network error returns empty list (fail-open)."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError('Connection refused')
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('releasekit.osv.httpx.AsyncClient', return_value=mock_client):
            result = await check_osv_vulnerabilities(['pkg:pypi/foo@1.0'])

        assert result == []

    async def test_api_error_returns_empty(self) -> None:
        """HTTP error returns empty list (fail-open)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            'Server Error',
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('releasekit.osv.httpx.AsyncClient', return_value=mock_client):
            result = await check_osv_vulnerabilities(['pkg:pypi/foo@1.0'])

        assert result == []
