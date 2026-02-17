#!/usr/bin/env python3
# Copyright 2025-2026 Google LLC
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

"""Add missing docstrings to test classes (fixes D101).

Uses the AST to find classes without docstrings and inserts a docstring
derived from the class name.  The script is idempotent — running it twice
produces the same result.

Usage:
    python py/bin/fix_missing_class_docstrings.py <directory_or_file> [...]

Examples:
    # Fix all test files under releasekit tests
    python py/bin/fix_missing_class_docstrings.py py/tools/releasekit/tests/

    # Fix a single file
    python py/bin/fix_missing_class_docstrings.py py/tools/releasekit/tests/rk_license_graph_test.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _class_name_to_docstring(name: str) -> str:
    """Convert a CamelCase class name to a human-readable docstring.

    Strips a leading ``Test`` prefix and splits on CamelCase boundaries.

    Examples:
        TestLoading           -> "Tests for loading."
        TestPermissiveCompat  -> "Tests for permissive compat."
        TestGplVersionCompat  -> "Tests for GPL version compat."
        TestLicenseTomlValidation -> "Tests for license TOML validation."
    """
    clean = name
    if clean.startswith('Test'):
        clean = clean[4:]

    # Split on CamelCase boundaries: insert space before each uppercase
    # letter that follows a lowercase letter or precedes a lowercase letter
    # in a run of uppercase (e.g. "GPL" stays together, "GPLVersion" -> "GPL Version").
    words = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', clean)
    words = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', words)

    # Lowercase everything, then capitalize first letter.
    words = words.strip()
    if not words:
        return f'Tests for {name}.'
    result = words[0].lower() + words[1:]
    if not result.endswith('.'):
        result += '.'
    return f'Tests for {result}'


def _has_docstring(node: ast.ClassDef) -> bool:
    """Check if a class already has a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)


def _get_indent(source_lines: list[str], lineno: int) -> str:
    """Get the indentation of the first statement in a class body.

    lineno is 1-indexed (from AST).
    """
    idx = lineno - 1  # Convert to 0-indexed
    if idx < len(source_lines):
        line = source_lines[idx]
        return line[: len(line) - len(line.lstrip())]
    return '        '


def fix_file(path: Path) -> int:
    """Add missing docstrings to classes in a single file.

    Returns the number of docstrings added.
    """
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    # Collect insertion points (line number, indent, docstring text)
    # We process in reverse order so line numbers stay valid after insertions.
    insertions: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if _has_docstring(node):
            continue
        if not node.body:
            continue

        # Get the line of the first body statement (1-indexed).
        # If the first body element has decorators, we must insert
        # *before* the first decorator, not before the def/class line.
        first: ast.stmt = node.body[0]
        dec_list = getattr(first, 'decorator_list', None)
        if dec_list:
            insert_line = dec_list[0].lineno
        else:
            insert_line = first.lineno
        indent = _get_indent(lines, insert_line)
        docstring = _class_name_to_docstring(node.name)
        insertions.append((insert_line, indent, docstring))

    if not insertions:
        return 0

    # Sort by line number descending so we can insert without shifting earlier indices
    insertions.sort(key=lambda x: x[0], reverse=True)

    for body_line, indent, docstring in insertions:
        idx = body_line - 1  # Convert to 0-indexed
        docstring_line = f'{indent}"""{docstring}"""\n\n'
        lines.insert(idx, docstring_line)

    path.write_text(''.join(lines), encoding='utf-8')
    return len(insertions)


def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <path> [<path> ...]')  # noqa: T201
        print('  <path> can be a file or directory (recurses into *_test.py files)')  # noqa: T201
        sys.exit(1)

    total = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_file():
            files = [p]
        elif p.is_dir():
            files = sorted(p.rglob('*_test.py'))
        else:
            print(f'Warning: {p} does not exist, skipping')  # noqa: T201
            continue

        for f in files:
            count = fix_file(f)
            if count:
                print(f'  {f}: added {count} class docstring(s)')  # noqa: T201
                total += count

    print(f'Total: {total} class docstring(s) added')  # noqa: T201


if __name__ == '__main__':
    main()
