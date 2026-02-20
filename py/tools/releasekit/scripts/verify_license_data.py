#!/usr/bin/env python3
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
"""Verify licenses.toml against authoritative upstream sources.

Runs two independent checks and reports a combined pass/fail:

1. **SPDX check** — Fetches the SPDX license list JSON and verifies
   that every SPDX ID in ``licenses.toml`` exists in the official list
   and that the ``osi_approved`` field matches.

2. **Google check** — Fetches ``license_type.go`` from
   ``google/licenseclassifier`` on GitHub and verifies that every
   ``google_category`` value in ``licenses.toml`` matches the
   authoritative category assignment.

Licenses that are custom (not in SPDX or not in Google's classifier)
are reported as warnings, not errors.

Exit codes:
    0  All checks passed.
    1  One or more errors found.

Usage::

    python scripts/verify_license_data.py          # run both checks
    python scripts/verify_license_data.py --spdx   # SPDX only
    python scripts/verify_license_data.py --google  # Google only

Sources:
    - SPDX License List:        https://spdx.org/licenses/
    - Google licenseclassifier: https://github.com/google/licenseclassifier
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

# ── URLs ────────────────────────────────────────────────────────────────

SPDX_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json'

GOOGLE_URL = 'https://raw.githubusercontent.com/google/licenseclassifier/main/license_type.go'

# ── Custom IDs ──────────────────────────────────────────────────────────
# IDs that we define ourselves and are NOT expected to appear in the
# official SPDX list or Google's classifier.  Keep sorted.

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

# ── Helpers ─────────────────────────────────────────────────────────────


def _load_licenses_toml() -> dict[str, dict]:
    """Load and return the parsed licenses.toml."""
    try:
        import tomllib  # type: ignore[unresolved-import]  # stdlib 3.11+; tomli fallback below
    except ModuleNotFoundError:
        import tomli as tomllib

    toml_path = Path(__file__).resolve().parent.parent / 'src' / 'releasekit' / 'data' / 'licenses.toml'
    with open(toml_path, 'rb') as f:
        return tomllib.load(f)


def _fetch(url: str) -> bytes:
    """Fetch a URL and return the raw bytes."""
    if not url.startswith('https://'):
        msg = f'Only https:// URLs are allowed, got: {url}'
        raise ValueError(msg)
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        return resp.read()


# ── SPDX verification ──────────────────────────────────────────────────


def check_spdx(our_licenses: dict[str, dict]) -> tuple[list[str], list[str]]:
    """Verify SPDX IDs and osi_approved against the SPDX license list.

    Returns:
        (errors, warnings) — lists of human-readable messages.
    """
    spdx_data = json.loads(_fetch(SPDX_URL))
    spdx_lookup: dict[str, bool] = {lic['licenseId']: lic.get('isOsiApproved', False) for lic in spdx_data['licenses']}

    errors: list[str] = []
    warnings: list[str] = []

    for spdx_id, entry in our_licenses.items():
        our_osi = entry.get('osi_approved', False)

        if spdx_id in CUSTOM_SPDX_IDS:
            warnings.append(f'  [CUSTOM] {spdx_id} — not in SPDX list (expected)')
            continue

        if spdx_id not in spdx_lookup:
            errors.append(f'  [MISSING] {spdx_id} — not found in SPDX license list')
            continue

        spdx_osi = spdx_lookup[spdx_id]
        if our_osi != spdx_osi:
            errors.append(f'  [OSI MISMATCH] {spdx_id}: ours={our_osi}, SPDX={spdx_osi}')

    return errors, warnings


# ── Google licenseclassifier verification ───────────────────────────────


def _parse_go_const_values(source: str) -> dict[str, str]:
    """Extract ``const Name = "SPDX-ID"`` mappings from Go source."""
    return dict(re.findall(r'(\w+)\s+=\s+"([^"]+)"', source))


def _parse_go_set_members(source: str, set_name: str) -> list[str]:
    """Extract member constant names from a ``sets.NewStringSet(...)`` block."""
    pattern = rf'{set_name}\s*=\s*sets\.NewStringSet\((.*?)\)'
    m = re.search(pattern, source, re.DOTALL)
    if not m:
        return []
    return re.findall(r'\b([A-Z][A-Za-z0-9_]+)\b', m.group(1))


def check_google(our_licenses: dict[str, dict]) -> tuple[list[str], list[str]]:
    """Verify google_category against Google licenseclassifier.

    Returns:
        (errors, warnings) — lists of human-readable messages.
    """
    source = _fetch(GOOGLE_URL).decode()

    const_to_spdx = _parse_go_const_values(source)

    category_sets = {
        'restricted': 'restrictedType',
        'reciprocal': 'reciprocalType',
        'notice': 'noticeType',
        'permissive': 'permissiveType',
        'unencumbered': 'unencumberedType',
        'by_exception_only': 'byExceptionOnlyType',
        'forbidden': 'forbiddenType',
    }

    google_lookup: dict[str, str] = {}
    for category, set_name in category_sets.items():
        for const_name in _parse_go_set_members(source, set_name):
            spdx_id = const_to_spdx.get(const_name, const_name)
            google_lookup[spdx_id] = category

    errors: list[str] = []
    warnings: list[str] = []

    for spdx_id, entry in our_licenses.items():
        our_cat = entry.get('google_category', '')

        if spdx_id not in google_lookup:
            warnings.append(f'  [NOT IN GOOGLE] {spdx_id}')
            continue

        google_cat = google_lookup[spdx_id]
        if our_cat != google_cat:
            errors.append(f'  [CATEGORY MISMATCH] {spdx_id}: ours={our_cat!r}, google={google_cat!r}')

    return errors, warnings


# ── Main ────────────────────────────────────────────────────────────────


def main() -> int:
    """Run verification checks and return 0 on success, 1 on failure."""
    parser = argparse.ArgumentParser(
        description='Verify licenses.toml against upstream sources.',
    )
    parser.add_argument(
        '--spdx',
        action='store_true',
        help='Run SPDX check only.',
    )
    parser.add_argument(
        '--google',
        action='store_true',
        help='Run Google classifier check only.',
    )
    args = parser.parse_args()

    run_spdx = args.spdx or not (args.spdx or args.google)
    run_google = args.google or not (args.spdx or args.google)

    our_licenses = _load_licenses_toml()

    all_errors: list[str] = []
    all_warnings: list[str] = []

    if run_spdx:
        errors, warnings = check_spdx(our_licenses)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        if warnings:
            for _w in warnings:
                pass
        if errors:
            for _e in errors:
                pass
        else:
            pass

    if run_google:
        errors, warnings = check_google(our_licenses)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        not_in_google = sum(1 for w in warnings if 'NOT IN GOOGLE' in w)
        if not_in_google:
            for _w in warnings:
                pass
        if errors:
            for _e in errors:
                pass
        else:
            pass

    # Summary.
    if all_errors:
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
