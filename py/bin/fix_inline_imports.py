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

"""Move in-function imports to the top of each Python file.

Per GEMINI.md: "All imports must be at the top of the file, outside any
function definitions."

This script:
1. Parses each .py file with ``ast``.
2. Finds import statements nested inside function/method bodies.
3. Moves them to the top-level import block (after the last existing
   top-level import).
4. Removes the inline import lines and any trailing blank line left behind.
5. Skips files where the result would not parse (safety net).
6. Runs ``ruff check --select I --fix`` at the end to sort/deduplicate.

Usage::

    python py/bin/fix_inline_imports.py py/tools/releasekit/src/releasekit
    python py/bin/fix_inline_imports.py py/tools/releasekit/tests

The script is idempotent — running it twice produces the same result.
"""

from __future__ import annotations

import ast
import re
import subprocess  # noqa: S404 – intentional: runs ruff to sort imports.
import sys
from pathlib import Path


def _find_inline_imports(
    tree: ast.Module,
    source_lines: list[str],
) -> list[tuple[int, int, str]]:
    """Return ``(start_line, end_line, cleaned_text)`` for every inline import.

    Finds import statements nested inside a function or method body.
    Line numbers are 1-indexed to match ``ast`` conventions.
    """
    results: list[tuple[int, int, str]] = []

    def _walk_func_body(node: ast.AST) -> None:
        """Recurse into compound statements inside a function."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                end = child.end_lineno or child.lineno
                raw_lines = source_lines[child.lineno - 1 : end]
                raw = '\n'.join(raw_lines)
                # Strip leading whitespace (indentation) and trailing noqa.
                clean = raw.strip()
                clean = re.sub(r'\s*#\s*noqa:.*$', '', clean, flags=re.MULTILINE).strip()
                results.append((child.lineno, end, clean))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Descend into nested functions — their imports are
                # local to that nested scope, but the guideline says *all*
                # imports must be at the top of the file.
                _walk_func_body(child)
            else:
                _walk_func_body(child)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _walk_func_body(node)

    return results


def _top_level_import_texts(tree: ast.Module, source_lines: list[str]) -> set[str]:
    """Return the set of cleaned import texts already at the module level."""
    texts: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raw = '\n'.join(source_lines[node.lineno - 1 : node.end_lineno]).strip()
            raw = re.sub(r'\s*#\s*noqa:.*$', '', raw, flags=re.MULTILINE).strip()
            texts.add(raw)
    return texts


def _last_top_level_import_line(tree: ast.Module) -> int:
    """Return the 1-indexed line number of the last top-level import."""
    last = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = max(last, node.end_lineno or node.lineno)
    return last


def _extract_import_key(text: str) -> tuple[str, str]:
    """Return a sort key ``(module, names)`` for an import statement."""
    m = re.match(r'^from\s+([\w.]+)\s+import\s+(.+)', text, re.DOTALL)
    if m:
        return (m.group(1), m.group(2).strip())
    m2 = re.match(r'^import\s+([\w.]+)', text)
    if m2:
        return (m2.group(1), '')
    return (text, '')


def fix_file(path: Path) -> int:
    """Fix one file.  Returns the number of import lines moved."""
    source = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0

    source_lines = source.splitlines()
    inline = _find_inline_imports(tree, source_lines)
    if not inline:
        return 0

    existing = _top_level_import_texts(tree, source_lines)
    insert_after = _last_top_level_import_line(tree)

    # Decide which imports to add at the top.
    new_imports: list[str] = []
    lines_to_remove: set[int] = set()  # 1-indexed

    for start, end, clean in inline:
        for ln in range(start, end + 1):
            lines_to_remove.add(ln)
        if clean not in existing:
            new_imports.append(clean)
            existing.add(clean)

    if not lines_to_remove:
        return 0

    # Build new source: remove inline import lines.
    new_lines: list[str] = []
    i = 0
    while i < len(source_lines):
        lineno = i + 1  # 1-indexed
        if lineno in lines_to_remove:
            # Also skip a single blank line immediately after the removed block
            # (the blank line that separated the import from the function body).
            next_i = i + 1
            if next_i < len(source_lines) and source_lines[next_i].strip() == '':
                # Only skip if the *previous* kept line is not already blank.
                if new_lines and new_lines[-1].strip() != '':
                    i = next_i + 1
                    continue
            i += 1
            continue
        new_lines.append(source_lines[i])
        i += 1

    # Insert new imports after the last top-level import.
    if new_imports and insert_after > 0:
        # Adjust insert_after for removed lines above it.
        removed_above = sum(1 for ln in lines_to_remove if ln <= insert_after)
        adj = insert_after - removed_above
        # Deduplicate and sort.
        unique = sorted(set(new_imports), key=_extract_import_key)
        for imp in reversed(unique):
            new_lines.insert(adj, imp)

    result = '\n'.join(new_lines)
    # Ensure file ends with a newline.
    if not result.endswith('\n'):
        result += '\n'

    # Safety: verify the result parses.
    try:
        ast.parse(result)
    except SyntaxError:
        return 0

    if result != source:
        path.write_text(result, encoding='utf-8')
        return len(lines_to_remove)
    return 0


def main() -> None:
    """Move in-function imports to the top of each file and reformat."""
    if len(sys.argv) < 2:
        sys.exit(1)

    total = 0
    files_changed = 0
    for arg in sys.argv[1:]:
        root = Path(arg)
        if root.is_file():
            targets = [root]
        else:
            targets = sorted(root.rglob('*.py'))

        for p in targets:
            n = fix_file(p)
            if n:
                total += n
                files_changed += 1

    if files_changed:
        # Run ruff to sort and deduplicate imports.
        # Filter out option-like arguments to prevent command injection.
        dirs = [p for p in sys.argv[1:] if not p.startswith('-')]
        subprocess.run(  # noqa: S603
            ['uv', 'run', 'ruff', 'check', '--select', 'I', '--fix', *dirs],  # noqa: S607
            check=False,
        )
        subprocess.run(  # noqa: S603
            ['uv', 'run', 'ruff', 'format', *dirs],  # noqa: S607
            check=False,
        )


if __name__ == '__main__':
    main()
