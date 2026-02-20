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
# SPDX-License-Identifier: Apache-2.0

"""Compare licenses.toml against google/licenseclassifier license_type.go.

Checks that every license in google/licenseclassifier is present in our
licenses.toml, and reports any gaps or extras.

Usage:
    python py/bin/check_license_coverage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# ── All licenses from google/licenseclassifier license_type.go ───────
# Source: https://github.com/google/licenseclassifier/blob/main/license_type.go
# Last synced: 2026-02-17

CLASSIFIER_LICENSES: dict[str, str] = {
    # restricted
    'BCL': 'restricted',
    'CC-BY-ND-1.0': 'restricted',
    'CC-BY-ND-2.0': 'restricted',
    'CC-BY-ND-2.5': 'restricted',
    'CC-BY-ND-3.0': 'restricted',
    'CC-BY-ND-4.0': 'restricted',
    'CC-BY-SA-1.0': 'restricted',
    'CC-BY-SA-2.0': 'restricted',
    'CC-BY-SA-2.5': 'restricted',
    'CC-BY-SA-3.0': 'restricted',
    'CC-BY-SA-4.0': 'restricted',
    'GPL-1.0': 'restricted',
    'GPL-2.0': 'restricted',
    'GPL-2.0-with-autoconf-exception': 'restricted',
    'GPL-2.0-with-bison-exception': 'restricted',
    'GPL-2.0-with-classpath-exception': 'restricted',
    'GPL-2.0-with-font-exception': 'restricted',
    'GPL-2.0-with-GCC-exception': 'restricted',
    'GPL-3.0': 'restricted',
    'GPL-3.0-with-autoconf-exception': 'restricted',
    'GPL-3.0-with-GCC-exception': 'restricted',
    'LGPL-2.0': 'restricted',
    'LGPL-2.1': 'restricted',
    'LGPL-3.0': 'restricted',
    'LGPLLR': 'restricted',
    'NPL-1.0': 'restricted',
    'NPL-1.1': 'restricted',
    'OSL-1.0': 'restricted',
    'OSL-1.1': 'restricted',
    'OSL-2.0': 'restricted',
    'OSL-2.1': 'restricted',
    'OSL-3.0': 'restricted',
    'QPL-1.0': 'restricted',
    'Sleepycat': 'restricted',
    # reciprocal
    'APSL-1.0': 'reciprocal',
    'APSL-1.1': 'reciprocal',
    'APSL-1.2': 'reciprocal',
    'APSL-2.0': 'reciprocal',
    'CDDL-1.0': 'reciprocal',
    'CDDL-1.1': 'reciprocal',
    'CPL-1.0': 'reciprocal',
    'EPL-1.0': 'reciprocal',
    'EPL-2.0': 'reciprocal',
    'FreeImage': 'reciprocal',
    'IPL-1.0': 'reciprocal',
    'MPL-1.0': 'reciprocal',
    'MPL-1.1': 'reciprocal',
    'MPL-2.0': 'reciprocal',
    'Ruby': 'reciprocal',
    # notice
    'AFL-1.1': 'notice',
    'AFL-1.2': 'notice',
    'AFL-2.0': 'notice',
    'AFL-2.1': 'notice',
    'AFL-3.0': 'notice',
    'Apache-1.0': 'notice',
    'Apache-1.1': 'notice',
    'Apache-2.0': 'notice',
    'Artistic-1.0-cl8': 'notice',
    'Artistic-1.0-Perl': 'notice',
    'Artistic-1.0': 'notice',
    'Artistic-2.0': 'notice',
    'BSL-1.0': 'notice',
    'BSD-2-Clause-FreeBSD': 'notice',
    'BSD-2-Clause-NetBSD': 'notice',
    'BSD-2-Clause': 'notice',
    'BSD-3-Clause-Attribution': 'notice',
    'BSD-3-Clause-Clear': 'notice',
    'BSD-3-Clause-LBNL': 'notice',
    'BSD-3-Clause': 'notice',
    'BSD-4-Clause': 'notice',
    'BSD-4-Clause-UC': 'notice',
    'BSD-Protection': 'notice',
    'CC-BY-1.0': 'notice',
    'CC-BY-2.0': 'notice',
    'CC-BY-2.5': 'notice',
    'CC-BY-3.0': 'notice',
    'CC-BY-4.0': 'notice',
    'FTL': 'notice',
    'ISC': 'notice',
    'ImageMagick': 'notice',
    'Libpng': 'notice',
    'Lil-1.0': 'notice',
    'Linux-OpenIB': 'notice',
    'LPL-1.02': 'notice',
    'LPL-1.0': 'notice',
    'MS-PL': 'notice',
    'MIT': 'notice',
    'NCSA': 'notice',
    'OpenSSL': 'notice',
    'PHP-3.01': 'notice',
    'PHP-3.0': 'notice',
    'PIL': 'notice',
    'Python-2.0': 'notice',
    'Python-2.0-complete': 'notice',
    'PostgreSQL': 'notice',
    'SGI-B-1.0': 'notice',
    'SGI-B-1.1': 'notice',
    'SGI-B-2.0': 'notice',
    'Unicode-DFS-2015': 'notice',
    'Unicode-DFS-2016': 'notice',
    'Unicode-TOU': 'notice',
    'UPL-1.0': 'notice',
    'W3C-19980720': 'notice',
    'W3C-20150513': 'notice',
    'W3C': 'notice',
    'X11': 'notice',
    'Xnet': 'notice',
    'Zend-2.0': 'notice',
    'zlib-acknowledgement': 'notice',
    'Zlib': 'notice',
    'ZPL-1.1': 'notice',
    'ZPL-2.0': 'notice',
    'ZPL-2.1': 'notice',
    'eGenix': 'notice',
    'GUST-Font-License': 'notice',
    # unencumbered
    'CC0-1.0': 'unencumbered',
    'Unlicense': 'unencumbered',
    '0BSD': 'unencumbered',
    # by_exception_only
    'Beerware': 'by_exception_only',
    'OFL-1.1': 'by_exception_only',
    'OpenVision': 'by_exception_only',
    # forbidden
    'AGPL-1.0': 'forbidden',
    'AGPL-3.0': 'forbidden',
    'CC-BY-NC-1.0': 'forbidden',
    'CC-BY-NC-2.0': 'forbidden',
    'CC-BY-NC-2.5': 'forbidden',
    'CC-BY-NC-3.0': 'forbidden',
    'CC-BY-NC-4.0': 'forbidden',
    'CC-BY-NC-ND-1.0': 'forbidden',
    'CC-BY-NC-ND-2.0': 'forbidden',
    'CC-BY-NC-ND-2.5': 'forbidden',
    'CC-BY-NC-ND-3.0': 'forbidden',
    'CC-BY-NC-ND-4.0': 'forbidden',
    'CC-BY-NC-SA-1.0': 'forbidden',
    'CC-BY-NC-SA-2.0': 'forbidden',
    'CC-BY-NC-SA-2.5': 'forbidden',
    'CC-BY-NC-SA-3.0': 'forbidden',
    'CC-BY-NC-SA-4.0': 'forbidden',
    'Commons-Clause': 'forbidden',
    'Facebook-2-Clause': 'forbidden',
    'Facebook-3-Clause': 'forbidden',
    'Facebook-Examples': 'forbidden',
    'WTFPL': 'forbidden',
    # Present as constants in licenseclassifier but NOT placed into any
    # category set (restrictedType, reciprocalType, noticeType, etc.).
    # We include them here for completeness with category=None so the
    # coverage check confirms they exist but skips category comparison.
    'CPAL-1.0': '',
    'EUPL-1.0': '',
    'EUPL-1.1': '',
    'LPPL-1.3c': '',
    'SISSL': '',
    'SISSL-1.2': '',
}

# licenseclassifier uses deprecated SPDX IDs (no -only/-or-later suffix).
# Map them to current SPDX IDs used in our licenses.toml.
DEPRECATED_TO_CURRENT: dict[str, str] = {
    'AGPL-1.0': 'AGPL-1.0-only',
    'AGPL-3.0': 'AGPL-3.0-only',
    'GPL-1.0': 'GPL-1.0-only',
    'GPL-2.0': 'GPL-2.0-only',
    'GPL-3.0': 'GPL-3.0-only',
    'LGPL-2.0': 'LGPL-2.0-only',
    'LGPL-2.1': 'LGPL-2.1-only',
    'LGPL-3.0': 'LGPL-3.0-only',
}


def main() -> int:
    """Compare licenses.toml against licenseclassifier and report gaps."""
    licenses_toml = Path(__file__).resolve().parent.parent.parent / 'src' / 'releasekit' / 'data' / 'licenses.toml'

    if not licenses_toml.is_file():
        return 1

    with open(licenses_toml, 'rb') as f:
        data = tomllib.load(f)

    our_ids: set[str] = set(data.keys())

    # Normalize classifier IDs to current SPDX
    normalized: dict[str, str] = {}
    for lid, cat in CLASSIFIER_LICENSES.items():
        current = DEPRECATED_TO_CURRENT.get(lid, lid)
        normalized[current] = cat

    classifier_ids = set(normalized.keys())

    missing = classifier_ids - our_ids
    extra = our_ids - classifier_ids

    # Category mismatches
    mismatches: list[str] = []
    for lid, expected_cat in normalized.items():
        if lid in our_ids:
            actual = data[lid].get('google_category', '')
            if expected_cat and actual and actual != expected_cat:
                mismatches.append(f'  {lid}: expected={expected_cat}, got={actual}')

    ok = True

    if missing:
        ok = False
        for lid in sorted(missing):
            cat = normalized[lid]
    else:
        pass

    if extra:
        for _lid in sorted(extra):
            pass
    else:
        pass

    if mismatches:
        ok = False
        for _m in sorted(mismatches):
            pass
    else:
        pass

    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
