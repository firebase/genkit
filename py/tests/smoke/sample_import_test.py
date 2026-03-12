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

"""Smoke tests for samples.

Verifies that every sample's main.py is syntactically valid Python.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Resolve py/samples/ relative to this test file (py/tests/smoke/).
_SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / 'samples'


def _find_sample_main_files() -> list[Path]:
    """Discover all sample main.py files."""
    results: list[Path] = []
    for sample_dir in sorted(_SAMPLES_DIR.iterdir()):
        if not sample_dir.is_dir() or sample_dir.name.startswith(('.', '_')):
            continue
        # Samples: main.py at root, or src/main.py for backward compat
        main_py = sample_dir / 'main.py'
        if main_py.is_file():
            results.append(main_py)
            continue
        main_py = sample_dir / 'src' / 'main.py'
        if main_py.is_file():
            results.append(main_py)
            continue
    return results


_SAMPLE_MAINS = _find_sample_main_files()


@pytest.mark.parametrize(
    'main_py',
    _SAMPLE_MAINS,
    ids=[str(p.relative_to(_SAMPLES_DIR)) for p in _SAMPLE_MAINS],
)
def test_sample_syntax_valid(main_py: Path) -> None:
    """Each sample main.py is syntactically valid Python."""
    source = main_py.read_text(encoding='utf-8')
    try:
        ast.parse(source, filename=str(main_py))
    except SyntaxError as exc:
        pytest.fail(f'Syntax error in {main_py}: {exc}')
