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

r"""Version string rewriting in pyproject.toml and arbitrary files.

Rewrites version strings in ``pyproject.toml`` (via tomlkit for
comment-preserving edits) and in arbitrary files like ``__init__.py``
or constants modules (via regex-based pattern matching).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ BumpTarget          │ A file + regex pattern that contains a        │
    │                     │ version string to update. Like a search-and-  │
    │                     │ replace instruction.                          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ bump_pyproject      │ Updates the ``version`` key in pyproject.toml │
    │                     │ using tomlkit (preserves comments/formatting).│
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ bump_file           │ Applies a regex to replace a version string   │
    │                     │ in any text file (e.g. __init__.py).          │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.bump import BumpTarget, bump_file, bump_pyproject

    # Update pyproject.toml
    bump_pyproject(Path('pyproject.toml'), '0.5.0')

    # Update __init__.py
    target = BumpTarget(
        path=Path('src/mypackage/__init__.py'),
        pattern=r"^__version__\\s*=\\s*['\"]([^'\"]+)['\"]",
    )
    bump_file(target, '0.5.0')
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import tomlkit
import tomlkit.exceptions

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

# Default pattern for __version__ in Python files.
DEFAULT_VERSION_PATTERN: str = r"^(__version__\s*=\s*['\"])([^'\"]+)(['\"])"


@dataclass(frozen=True)
class BumpTarget:
    """A file and regex pattern for version string replacement.

    The regex must have exactly one or three capture groups:
    - **One group**: The group captures the version string itself.
    - **Three groups**: Group 1 is the prefix (e.g. ``__version__ = '``),
      group 2 is the version, group 3 is the suffix (e.g. ``'``).
      This is the preferred form because it preserves surrounding text.

    Attributes:
        path: Path to the file containing the version string.
        pattern: Regex pattern with capture group(s) for the version.
    """

    path: Path
    pattern: str = DEFAULT_VERSION_PATTERN


def bump_pyproject(pyproject_path: Path, new_version: str) -> str:
    """Update the version in a pyproject.toml file.

    Uses tomlkit to preserve comments, formatting, and ordering.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        new_version: The new version string (e.g. ``"0.5.0"``).

    Returns:
        The old version that was replaced.

    Raises:
        ReleaseKitError: If the file cannot be read, parsed, or written,
            or if no ``[project].version`` key exists.
    """
    try:
        text = pyproject_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot read {pyproject_path}: {exc}',
            hint=f'Check that {pyproject_path} exists and is readable.',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot parse {pyproject_path}: {exc}',
            hint=f'Check that {pyproject_path} contains valid TOML.',
        ) from exc

    project = doc.get('project')
    if not isinstance(project, dict) or 'version' not in project:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'No [project].version key in {pyproject_path}',
            hint='Add a version field to [project] in pyproject.toml.',
        )

    old_version = str(project['version'])
    project['version'] = new_version

    try:
        pyproject_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot write {pyproject_path}: {exc}',
            hint=f'Check file permissions for {pyproject_path}.',
        ) from exc

    logger.info(
        'pyproject_version_bumped',
        path=str(pyproject_path),
        old=old_version,
        new=new_version,
    )
    return old_version


def bump_file(target: BumpTarget, new_version: str) -> str:
    """Replace a version string in an arbitrary file using regex.

    Args:
        target: The :class:`BumpTarget` specifying the file and pattern.
        new_version: The new version string.

    Returns:
        The old version that was replaced.

    Raises:
        ReleaseKitError: If the file cannot be read/written, or if the
            pattern does not match.
    """
    try:
        text = target.path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot read {target.path}: {exc}',
            hint=f'Check that {target.path} exists and is readable.',
        ) from exc

    compiled = re.compile(target.pattern, re.MULTILINE)
    match = compiled.search(text)
    if not match:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Pattern {target.pattern!r} not found in {target.path}',
            hint='Check that the file contains a version string matching the pattern.',
        )

    groups = match.groups()
    if len(groups) == 3:
        # Three-group pattern: prefix + version + suffix.
        old_version = groups[1]
        new_text = compiled.sub(rf'\g<1>{new_version}\g<3>', text, count=1)
    elif len(groups) == 1:
        # Single-group pattern: just the version.
        old_version = groups[0]
        new_text = compiled.sub(new_version, text, count=1)
    else:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Pattern must have 1 or 3 capture groups, got {len(groups)}',
            hint="Use a pattern like r\"^__version__ = '([^']+)'\" (1 group) "
            "or r\"^(__version__ = ')([^']+)(')\" (3 groups).",
        )

    try:
        target.path.write_text(new_text, encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot write {target.path}: {exc}',
            hint=f'Check file permissions for {target.path}.',
        ) from exc

    logger.info(
        'file_version_bumped',
        path=str(target.path),
        pattern=target.pattern,
        old=old_version,
        new=new_version,
    )
    return old_version


__all__ = [
    'DEFAULT_VERSION_PATTERN',
    'BumpTarget',
    'bump_file',
    'bump_pyproject',
]
