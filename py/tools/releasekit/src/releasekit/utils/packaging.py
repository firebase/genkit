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

"""Python package name helpers (PEP 503 / PEP 508).

These helpers are used by the workspace discovery layer and the uv
workspace backend to normalise and parse Python package names.

.. note::

   npm package names follow different normalisation rules (case-
   insensitive but no underscore/hyphen folding).  The pnpm backend
   keeps its own ``_normalize_name`` for that reason.
"""

from __future__ import annotations

import re

from packaging.requirements import InvalidRequirement, Requirement


def normalize_name(name: str) -> str:
    """Normalize a Python package name per PEP 503.

    Lowercases the name and replaces underscores with hyphens so that
    ``My_Package`` and ``my-package`` compare equal.
    """
    return name.lower().replace('_', '-')


def parse_dep_name(dep_spec: str) -> str:
    """Extract the normalized package name from a PEP 508 dependency specifier.

    Uses the ``packaging`` library for robust parsing of all valid PEP 508
    forms including extras, version specifiers, and environment markers.
    Falls back to basic string splitting if parsing fails.
    """
    try:
        return Requirement(dep_spec).name.lower()
    except InvalidRequirement:
        # Fallback for malformed specifiers: split at first specifier char.
        name = re.split(r'[<>=!~,;\[]', dep_spec, maxsplit=1)[0].strip()
        return name.lower()
