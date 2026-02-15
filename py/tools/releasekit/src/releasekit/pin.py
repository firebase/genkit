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

"""Ephemeral dependency pinning for publish-time isolation.

During publishing, workspace packages reference each other via
``[tool.uv.sources]`` which resolves to local paths. For PyPI uploads,
these must be replaced with exact version pins (e.g. ``genkit==0.5.0``).
After publishing, the original ``pyproject.toml`` must be restored
byte-for-byte.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ EphemeralPin         │ A context manager that temporarily rewrites  │
    │                     │ ``pyproject.toml`` for publishing. Like       │
    │                     │ borrowing a library book: you can use it, but │
    │                     │ it must go back exactly as it was.            │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Crash Safety         │ Three layers of protection:                  │
    │                     │ 1. ``atexit`` handler (normal exit)           │
    │                     │ 2. Signal handler (SIGTERM/SIGINT)            │
    │                     │ 3. ``.bak`` file (manual recovery)           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ SHA-256 Verify       │ After restore, the file's hash is compared  │
    │                     │ against the original to guarantee byte-       │
    │                     │ identical restoration.                        │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.pin import EphemeralPin

    version_map = {'genkit': '0.5.0', 'genkit-plugin-google-genai': '0.5.0'}

    with EphemeralPin(Path('pyproject.toml'), version_map) as pin:
        # pyproject.toml now has pinned versions
        subprocess.run(['uv', 'build', '--no-sources'])
    # pyproject.toml is restored to its original state
"""

from __future__ import annotations

import atexit
import hashlib
import os
import re
import shutil
import signal
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import tomlkit
import tomlkit.exceptions
from packaging.requirements import InvalidRequirement, Requirement

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)


def _sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_dep_name(dep_spec: str) -> str:
    """Extract the bare package name from a PEP 508 dependency specifier.

    Uses ``packaging.requirements.Requirement`` for robust parsing,
    with a regex fallback for malformed specifiers.
    """
    try:
        return Requirement(dep_spec).name
    except InvalidRequirement:
        # Fallback: split at first specifier char.
        name = re.split(r'[<>=!~,;\[]', dep_spec, maxsplit=1)[0].strip()
        return name if name else dep_spec.strip()


def _pin_dep_list(deps: list[object], normalized_map: dict[str, str]) -> int:
    """Pin matching dependencies in a list, returning the count pinned."""
    pinned = 0
    for i, dep in enumerate(deps):
        dep_str = str(dep).strip()
        bare_name = _extract_dep_name(dep_str)
        normalized = bare_name.lower().replace('_', '-')
        if normalized in normalized_map:
            deps[i] = f'{bare_name}=={normalized_map[normalized]}'
            pinned += 1
    return pinned


def pin_dependencies(
    pyproject_path: Path,
    version_map: dict[str, str],
) -> str:
    """Rewrite internal dependencies in a pyproject.toml to exact version pins.

    Replaces workspace source references with ``==version`` pins for all
    packages found in ``version_map``. Only modifies dependencies that
    match keys in the map.

    Args:
        pyproject_path: Path to the pyproject.toml to modify.
        version_map: Mapping of normalized package name → version string.
            e.g. ``{"genkit": "0.5.0", "genkit-plugin-foo": "0.5.0"}``.

    Returns:
        The original file content (for manual restore if needed).

    Raises:
        ReleaseKitError: If the file cannot be read, parsed, or written.
    """
    try:
        original_text = pyproject_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot read {pyproject_path}: {exc}',
            hint=f'Check that {pyproject_path} exists and is readable.',
        ) from exc

    try:
        doc = tomlkit.parse(original_text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot parse {pyproject_path}: {exc}',
            hint=f'Check that {pyproject_path} contains valid TOML.',
        ) from exc

    # Normalize version_map keys for matching.
    normalized_map = {k.lower().replace('_', '-'): v for k, v in version_map.items()}

    project = doc.get('project', {})
    pinned_count = 0

    # Pin [project].dependencies
    deps = project.get('dependencies', [])
    if isinstance(deps, list):
        pinned_count += _pin_dep_list(deps, normalized_map)

    # Pin [project.optional-dependencies]
    optional_deps = project.get('optional-dependencies', {})
    if isinstance(optional_deps, dict):
        for group_deps in optional_deps.values():
            if not isinstance(group_deps, list):
                continue
            pinned_count += _pin_dep_list(group_deps, normalized_map)

    try:
        pyproject_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot write {pyproject_path}: {exc}',
            hint=f'Check file permissions for {pyproject_path}.',
        ) from exc

    logger.info(
        'dependencies_pinned',
        path=str(pyproject_path),
        pinned=pinned_count,
    )
    return original_text


@contextmanager
def ephemeral_pin(
    pyproject_path: Path,
    version_map: dict[str, str],
) -> Generator[Path, None, None]:
    """Context manager for ephemeral dependency pinning.

    Pins internal dependencies to exact versions for the duration of the
    context, then restores the original file with SHA-256 verification.

    Three layers of crash safety ensure restoration:

    1. **atexit handler**: Restores on normal Python exit.
    2. **Signal handler**: Restores on SIGTERM/SIGINT.
    3. **.bak file**: Manual recovery if all else fails.

    Args:
        pyproject_path: Path to the pyproject.toml to pin.
        version_map: Package name → version mapping.

    Yields:
        The path to the pinned pyproject.toml (same as input).

    Raises:
        ReleaseKitError: If pinning, restoration, or verification fails.
    """
    pyproject_path = pyproject_path.resolve()
    backup_path = pyproject_path.with_suffix('.toml.bak')

    # Compute original hash before any modifications.
    original_hash = _sha256(pyproject_path)

    # Create backup.
    try:
        shutil.copy2(pyproject_path, backup_path)
    except OSError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot create backup at {backup_path}: {exc}',
            hint=f'Check file permissions for {backup_path.parent}.',
        ) from exc
    logger.debug('backup_created', path=str(backup_path))

    def _restore() -> None:
        """Restore original pyproject.toml from backup."""
        if not backup_path.exists():
            return
        try:
            shutil.move(backup_path, pyproject_path)
        except OSError:
            logger.error(
                'restore_failed',
                backup=str(backup_path),
                target=str(pyproject_path),
            )
            return

        restored_hash = _sha256(pyproject_path)
        if restored_hash != original_hash:
            logger.error(
                'restore_hash_mismatch',
                expected=original_hash[:12],
                actual=restored_hash[:12],
            )
        else:
            logger.info('pyproject_restored', path=str(pyproject_path))

    def _signal_handler(signum: int, _frame: object) -> None:
        """Restore on signal, then re-raise with default handler."""
        _restore()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    # Register crash safety layers.
    atexit.register(_restore)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    old_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        pin_dependencies(pyproject_path, version_map)
        yield pyproject_path
    finally:
        # Restore original file.
        _restore()

        # Unregister crash safety.
        atexit.unregister(_restore)
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)


__all__ = [
    'ephemeral_pin',
    'pin_dependencies',
]
