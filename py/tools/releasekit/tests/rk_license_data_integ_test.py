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

"""Integration tests that verify licenses.toml against upstream sources.

These tests require internet access and are **deselected by default**.
Run them explicitly with::

    pytest -m network tests/rk_license_data_integ_test.py

They fetch the latest data from:
    - SPDX license list (spdx.org)
    - Google licenseclassifier (github.com/google/licenseclassifier)
"""

from __future__ import annotations

import json
import re
import socket
import urllib.request
from pathlib import Path

import pytest

# ── Markers ─────────────────────────────────────────────────────────────

pytestmark = pytest.mark.network

# ── Constants ───────────────────────────────────────────────────────────

SPDX_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json'

GOOGLE_URL = 'https://raw.githubusercontent.com/google/licenseclassifier/main/license_type.go'

CUSTOM_SPDX_IDS: frozenset[str] = frozenset({
    'BCL',
    'Beerware',
    'Commons-Clause',
    'eGenix',
    'Facebook-2-Clause',
    'Facebook-3-Clause',
    'Facebook-Examples',
    'FreeImage',
    'GUST-Font-License',
    'ImageMagick',
    'JSON',
    'LGPLLR',
    'Lil-1.0',
    'Linux-OpenIB',
    'OpenSSL',
    'OpenVision',
    'PIL',
    'Proprietary',
    'Python-2.0-complete',
    'Ruby',
    'X11',
})

DATA_DIR = Path(__file__).resolve().parent.parent / 'src' / 'releasekit' / 'data'

# ── Helpers ─────────────────────────────────────────────────────────────


def _has_internet(host: str = '8.8.8.8', port: int = 53, timeout: float = 3) -> bool:
    """Return True if we can reach the internet."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def _load_licenses_toml() -> dict[str, dict]:
    try:
        import tomllib  # type: ignore[unresolved-import]  # stdlib 3.11+; tomli fallback below
    except ModuleNotFoundError:
        import tomli as tomllib

    with open(DATA_DIR / 'licenses.toml', 'rb') as f:
        return tomllib.load(f)


def _fetch(url: str) -> bytes:
    """Fetch *url* and return raw bytes.  Only https:// is allowed."""
    if not url.startswith('https://'):
        msg = f'Only https:// URLs are allowed, got: {url}'
        raise ValueError(msg)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        return resp.read()


# ── Skip if offline ─────────────────────────────────────────────────────

if not _has_internet():
    pytest.skip('No internet access', allow_module_level=True)

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope='module')
def our_licenses() -> dict[str, dict]:
    """Load and return the parsed licenses.toml."""
    return _load_licenses_toml()


@pytest.fixture(scope='module')
def spdx_lookup() -> dict[str, bool]:
    """Fetch the SPDX license list and return {id: osi_approved} mapping."""
    data = json.loads(_fetch(SPDX_URL))
    return {lic['licenseId']: lic.get('isOsiApproved', False) for lic in data['licenses']}


@pytest.fixture(scope='module')
def google_lookup() -> dict[str, str]:
    """Fetch Google licenseclassifier and return {id: category} mapping."""
    source = _fetch(GOOGLE_URL).decode()

    const_to_spdx: dict[str, str] = dict(re.findall(r'(\w+)\s+=\s+"([^"]+)"', source))

    category_sets = {
        'restricted': 'restrictedType',
        'reciprocal': 'reciprocalType',
        'notice': 'noticeType',
        'permissive': 'permissiveType',
        'unencumbered': 'unencumberedType',
        'by_exception_only': 'byExceptionOnlyType',
        'forbidden': 'forbiddenType',
    }

    lookup: dict[str, str] = {}
    for category, set_name in category_sets.items():
        pattern = rf'{set_name}\s*=\s*sets\.NewStringSet\((.*?)\)'
        m = re.search(pattern, source, re.DOTALL)
        if not m:
            continue
        for const_name in re.findall(r'\b([A-Z][A-Za-z0-9_]+)\b', m.group(1)):
            spdx_id = const_to_spdx.get(const_name, const_name)
            lookup[spdx_id] = category
    return lookup


# ── SPDX tests ──────────────────────────────────────────────────────────


class TestSPDXCompliance:
    """Verify licenses.toml against the SPDX license list."""

    def test_all_spdx_ids_are_valid(
        self,
        our_licenses: dict[str, dict],
        spdx_lookup: dict[str, bool],
    ) -> None:
        """Every non-custom SPDX ID in licenses.toml must exist in the official list."""
        missing = [sid for sid in our_licenses if sid not in spdx_lookup and sid not in CUSTOM_SPDX_IDS]
        assert not missing, f'SPDX IDs not found in official list: {missing}'

    def test_osi_approved_matches_spdx(
        self,
        our_licenses: dict[str, dict],
        spdx_lookup: dict[str, bool],
    ) -> None:
        """osi_approved must match the SPDX-provided value."""
        mismatches: list[str] = []
        for spdx_id, entry in our_licenses.items():
            if spdx_id in CUSTOM_SPDX_IDS or spdx_id not in spdx_lookup:
                continue
            ours = entry.get('osi_approved', False)
            theirs = spdx_lookup[spdx_id]
            if ours != theirs:
                mismatches.append(f'{spdx_id}: ours={ours}, SPDX={theirs}')
        assert not mismatches, 'osi_approved mismatches:\n' + '\n'.join(mismatches)


# ── Google licenseclassifier tests ──────────────────────────────────────


class TestGoogleClassifierCompliance:
    """Verify google_category values against Google licenseclassifier."""

    def test_google_category_matches(
        self,
        our_licenses: dict[str, dict],
        google_lookup: dict[str, str],
    ) -> None:
        """google_category must match Google licenseclassifier."""
        mismatches: list[str] = []
        for spdx_id, entry in our_licenses.items():
            if spdx_id not in google_lookup:
                continue
            ours = entry.get('google_category', '')
            theirs = google_lookup[spdx_id]
            if ours != theirs:
                mismatches.append(f'{spdx_id}: ours={ours!r}, google={theirs!r}')
        assert not mismatches, 'google_category mismatches:\n' + '\n'.join(mismatches)
