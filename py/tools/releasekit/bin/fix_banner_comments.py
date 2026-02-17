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

"""Remove banner/section-divider comments from Python source files.

Removes lines that are purely decorative section dividers, such as:

    # ── Section Name ──────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    # ---------------------------------------------------------------------------
    # Section Name
    # ---------------------------------------------------------------------------

These add visual noise without conveying information that isn't already
expressed by the code structure (classes, functions, blank lines).

The script is idempotent: running it twice produces the same result.

Usage:
    python fix_banner_comments.py <directory> [--dry-run]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that match banner-only comment lines.
# These must match the ENTIRE line (after stripping leading whitespace).
_BANNER_PATTERNS: list[re.Pattern[str]] = [
    # ── Section Name ──────  (box-drawing dashes with optional text)
    re.compile(r'^#\s*──.*──\s*$'),
    # # ═══════════════════  (box-drawing double lines, no text)
    re.compile(r'^#\s*═{4,}\s*$'),
    # # ---------------------------------------------------------------------------
    re.compile(r'^#\s*-{10,}\s*$'),
    # # ===========================================================================
    re.compile(r'^#\s*={10,}\s*$'),
    # # ###########################################################################
    re.compile(r'^#\s*#{10,}\s*$'),
    # # ***********************************************************************
    re.compile(r'^#\s*\*{10,}\s*$'),
    # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    re.compile(r'^#\s*~{10,}\s*$'),
]


def _is_banner_line(line: str) -> bool:
    """Return True if the line is a banner/divider comment."""
    stripped = line.strip()
    if not stripped.startswith('#'):
        return False
    return any(p.match(stripped) for p in _BANNER_PATTERNS)


def _collapse_blank_runs(lines: list[str]) -> list[str]:
    """Collapse runs of 3+ consecutive blank lines down to 2."""
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return result


def fix_file(path: Path, *, dry_run: bool = False) -> int:
    """Remove banner comments from a single file.

    Returns the number of lines removed.
    """
    original = path.read_text(encoding='utf-8')
    lines = original.splitlines(keepends=True)

    new_lines: list[str] = []
    removed = 0
    for line in lines:
        if _is_banner_line(line):
            removed += 1
        else:
            new_lines.append(line)

    if removed == 0:
        return 0

    # Collapse excessive blank lines left behind.
    new_lines = _collapse_blank_runs(new_lines)

    new_text = ''.join(new_lines)
    if not dry_run:
        path.write_text(new_text, encoding='utf-8')

    return removed


def main() -> None:
    """Remove banner comments from Python files in the given directory."""
    if len(sys.argv) < 2:
        sys.exit(1)

    target = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv

    if not target.is_dir():
        sys.exit(1)

    total_removed = 0
    total_files = 0
    for py_file in sorted(target.rglob('*.py')):
        if '.venv' in py_file.parts or '__pycache__' in py_file.parts:
            continue
        count = fix_file(py_file, dry_run=dry_run)
        if count > 0:
            total_files += 1
            total_removed += count


if __name__ == '__main__':
    main()
