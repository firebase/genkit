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

"""Fix classifiers for all Genkit Python packages.

Adds missing classifiers like 'Typing :: Typed' and 'License :: OSI Approved'.
"""

import re
from pathlib import Path

# Classifiers to add if missing
REQUIRED_CLASSIFIERS = [
    'Typing :: Typed',
    'License :: OSI Approved :: Apache Software License',
]


def add_classifiers(content: str) -> str:
    """Add missing classifiers to pyproject.toml content."""
    # Find the classifiers section
    classifiers_match = re.search(r'classifiers\s*=\s*\[([^\]]*)\]', content, re.DOTALL)
    if not classifiers_match:
        return content

    classifiers_content = classifiers_match.group(1)
    modified = False

    for classifier in REQUIRED_CLASSIFIERS:
        if classifier not in classifiers_content:
            # Add the classifier before the closing bracket
            # Find the last classifier line
            lines = classifiers_content.rstrip().split('\n')
            # Add new classifier
            new_classifier = f'  "{classifier}",'
            lines.append(new_classifier)
            classifiers_content = '\n'.join(lines) + '\n'
            modified = True

    if modified:
        # Replace the classifiers section
        new_classifiers = f'classifiers = [{classifiers_content}]'
        content = re.sub(r'classifiers\s*=\s*\[[^\]]*\]', new_classifiers, content, flags=re.DOTALL)

    return content


def fix_pyproject(pyproject_path: Path) -> bool:
    """Fix a single pyproject.toml file."""
    content = pyproject_path.read_text()
    original_content = content

    content = add_classifiers(content)

    if content != original_content:
        pyproject_path.write_text(content)
        return True
    return False


def main() -> None:
    """Fix all pyproject.toml files."""
    py_dir = Path(__file__).parent.parent

    updated = 0

    # Fix core package
    core_pyproject = py_dir / 'packages' / 'genkit' / 'pyproject.toml'
    if core_pyproject.exists() and fix_pyproject(core_pyproject):
        updated += 1

    # Fix all plugins
    plugins_dir = py_dir / 'plugins'
    for pyproject_path in plugins_dir.glob('*/pyproject.toml'):
        if fix_pyproject(pyproject_path):
            updated += 1


if __name__ == '__main__':
    main()
