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

"""Shared constants for workspace health checks."""

from __future__ import annotations

import re

# PEP 440 version pattern (simplified but covers all valid forms).
_PEP440_RE = re.compile(
    r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*'
    r'((a|b|rc)(0|[1-9][0-9]*))?'
    r'(\.post(0|[1-9][0-9]*))?'
    r'(\.dev(0|[1-9][0-9]*))?$'
)

# Dependency name extraction: "requests>=2.0" → "requests".
_DEP_NAME_RE = re.compile(r'^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)')

# Known deprecated classifiers → replacement (or empty string if no replacement).
DEPRECATED_CLASSIFIERS: dict[str, str] = {
    'Natural Language :: Ukranian': 'Natural Language :: Ukrainian',
    'Topic :: Software Development :: Version Control :: Bazaar': '',
    'Development Status :: 1 - Planning': '',
}

# License detection: patterns in LICENSE file content → expected classifier prefix.
_LICENSE_PATTERNS: dict[str, str] = {
    'Apache License': 'License :: OSI Approved :: Apache Software License',
    'MIT License': 'License :: OSI Approved :: MIT License',
    'BSD License': 'License :: OSI Approved :: BSD License',
    'GNU General Public License': 'License :: OSI Approved :: GNU General Public License',
    'GNU Lesser General Public License': 'License :: OSI Approved :: GNU Lesser General Public License',
    'Mozilla Public License': 'License :: OSI Approved :: Mozilla Public License',
    'ISC License': 'License :: OSI Approved :: ISC License',
    'Artistic License': 'License :: OSI Approved :: Artistic License',
    'Eclipse Public License': 'License :: OSI Approved :: Eclipse Public License',
    'European Union Public Licence': 'License :: OSI Approved :: European Union Public Licence',
    'The Unlicense': 'License :: OSI Approved :: The Unlicense (Unlicense)',
}

# Placeholder URL patterns that indicate unfinished metadata.
_PLACEHOLDER_URL_PATTERNS: list[str] = [
    'example.com',
    'example.org',
    'example.net',
    'your-url-here',
    'TODO',
    'FIXME',
    'CHANGEME',
]

# Private classifier used to exclude packages from PyPI upload.
_PRIVATE_CLASSIFIER = 'Private :: Do Not Upload'
