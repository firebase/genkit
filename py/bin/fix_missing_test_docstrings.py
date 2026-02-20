#!/usr/bin/env python3
# Copyright 2025 Google LLC
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

"""Add missing docstrings to test methods and private functions (fixes D102/D103).

Uses the AST to find methods/functions without docstrings and inserts a
docstring derived from the function name. The script is idempotent — running
it twice produces the same result.

Usage:
    python py/bin/fix_missing_test_docstrings.py <directory_or_file> [...]

Examples:
    # Fix all test files under releasekit tests
    python py/bin/fix_missing_test_docstrings.py py/tools/releasekit/tests/

    # Fix a single file
    python py/bin/fix_missing_test_docstrings.py py/tools/releasekit/tests/backends/rk_pm_cargo_test.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _name_to_docstring(name: str) -> str:
    """Convert a function/method name to a human-readable docstring.

    Examples:
        test_build_dry_run -> "Test build dry run."
        _fake_run_command  -> "Fake run command."
        test_returns_true_on_200 -> "Test returns true on 200."
    """
    # Strip leading underscores
    clean = name.lstrip('_')
    # Replace underscores with spaces
    words = clean.replace('_', ' ')
    # Capitalize first letter, add period
    if words:
        words = words[0].upper() + words[1:]
    if not words.endswith('.'):
        words += '.'
    return words


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function/method already has a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return True
    return False


def _get_indent(source_lines: list[str], lineno: int) -> str:
    """Get the indentation of the first statement in a function body.

    lineno is 1-indexed (from AST).
    """
    # The body starts after the def line. Find the first non-empty body line.
    idx = lineno - 1  # Convert to 0-indexed
    if idx < len(source_lines):
        line = source_lines[idx]
        return line[: len(line) - len(line.lstrip())]
    return '        '


def fix_file(path: Path) -> int:
    """Add missing docstrings to functions/methods in a single file.

    Returns the number of docstrings added.
    """
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    # Collect insertion points (line number, indent, docstring text)
    # We process in reverse order so line numbers stay valid after insertions.
    insertions: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _has_docstring(node):
            continue
        if not node.body:
            continue

        # Get the line of the first body statement (1-indexed)
        body_line = node.body[0].lineno
        indent = _get_indent(lines, body_line)
        docstring = _name_to_docstring(node.name)
        insertions.append((body_line, indent, docstring))

    if not insertions:
        return 0

    # Sort by line number descending so we can insert without shifting earlier indices
    insertions.sort(key=lambda x: x[0], reverse=True)

    for body_line, indent, docstring in insertions:
        idx = body_line - 1  # Convert to 0-indexed
        docstring_line = f'{indent}"""{docstring}"""\n'
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
                print(f'  {f}: added {count} docstring(s)')  # noqa: T201
                total += count

    print(f'Total: {total} docstring(s) added')  # noqa: T201


if __name__ == '__main__':
    main()
