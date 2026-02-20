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

"""Add missing docstrings to test methods and test classes.

Generates a one-line docstring from the method/class name by stripping
the ``test_`` / ``Test`` prefix and converting underscores to spaces.

Examples::

    def test_parse_empty_string(self) -> None:
        ...
    # becomes:
    def test_parse_empty_string(self) -> None:
        \"\"\"Parse empty string.\"\"\"
        ...

    class TestParseConfig:
        ...
    # becomes:
    class TestParseConfig:
        \"\"\"Tests for ParseConfig.\"\"\"
        ...

The script is idempotent: running it twice produces the same result.

Usage:
    python fix_test_docstrings.py <directory> [--dry-run]
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _name_to_docstring(name: str) -> str:
    """Convert a test_method_name to a human-readable docstring."""
    # Strip test_ prefix.
    text = re.sub(r'^test_', '', name)
    # Convert underscores to spaces.
    text = text.replace('_', ' ')
    # Capitalize first letter, add period.
    text = text[0].upper() + text[1:] if text else name
    if not text.endswith('.'):
        text += '.'
    return text


def _class_name_to_docstring(name: str) -> str:
    """Convert a TestClassName to a human-readable docstring."""
    # Strip Test prefix.
    inner = re.sub(r'^Test', '', name)
    if not inner:
        return f'Tests for {name}.'
    # Insert spaces before uppercase letters (CamelCase → words).
    spaced = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', inner)
    return f'Tests for {spaced}.'


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    """Return True if the node already has a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return True
    return False


def _get_indent(line: str) -> str:
    """Return the leading whitespace of a line."""
    return line[: len(line) - len(line.lstrip())]


def fix_file(path: Path, *, dry_run: bool = False) -> int:
    """Add missing docstrings to test methods/classes in a single file.

    Returns the number of docstrings added.
    """
    source = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return 0

    lines = source.splitlines(keepends=True)
    # Collect insertions as (line_number, indent, docstring_text).
    # line_number is 0-indexed, pointing to the line AFTER the def/class.
    insertions: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test') and not _has_docstring(node):
                doc = _class_name_to_docstring(node.name)
                # The body starts on the line after the class declaration.
                body_line = node.body[0].lineno - 1  # 0-indexed
                indent = _get_indent(lines[body_line]) if body_line < len(lines) else '        '
                insertions.append((body_line, indent, doc))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith('test_') and not _has_docstring(node):
                doc = _name_to_docstring(node.name)
                body_line = node.body[0].lineno - 1  # 0-indexed
                indent = _get_indent(lines[body_line]) if body_line < len(lines) else '            '
                insertions.append((body_line, indent, doc))

    if not insertions:
        return 0

    # Sort by line number descending so insertions don't shift earlier lines.
    insertions.sort(key=lambda x: x[0], reverse=True)

    for line_idx, indent, doc in insertions:
        docstring_line = f'{indent}"""{doc}"""\n'
        lines.insert(line_idx, docstring_line)

    new_source = ''.join(lines)
    if not dry_run:
        path.write_text(new_source, encoding='utf-8')

    return len(insertions)


def main() -> None:
    """Add missing docstrings to test methods in the given directory."""
    if len(sys.argv) < 2:
        sys.exit(1)

    target = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv

    if not target.is_dir():
        sys.exit(1)

    total_added = 0
    total_files = 0
    for py_file in sorted(target.rglob('*_test.py')):
        if '.venv' in py_file.parts or '__pycache__' in py_file.parts:
            continue
        count = fix_file(py_file, dry_run=dry_run)
        if count > 0:
            total_files += 1
            total_added += count


if __name__ == '__main__':
    main()
