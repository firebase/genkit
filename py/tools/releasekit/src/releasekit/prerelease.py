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

"""Pre-release and release candidate version management.

Handles pre-release labels (alpha, beta, rc, dev) for both semver and
PEP 440 versioning schemes. Supports incrementing pre-release counters,
promoting pre-releases to stable, and collapsing pre-release changelog
entries into the final release.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Pre-release label       │ A tag like "alpha", "beta", "rc" appended  │
    │                         │ to a version to mark it as not-yet-stable.  │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ PEP 440                 │ Python's version spec. Pre-releases use    │
    │                         │ suffixes like ``a1``, ``b2``, ``rc3``,     │
    │                         │ ``dev4`` (no hyphen, no dot).              │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ semver                  │ Semantic Versioning. Pre-releases use      │
    │                         │ ``-alpha.1``, ``-beta.2``, ``-rc.3``.     │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ promote                 │ Strip the pre-release suffix to produce    │
    │                         │ the stable version (e.g. 1.2.0rc1 → 1.2.0)│
    └─────────────────────────┴─────────────────────────────────────────────┘

Version format examples::

    Scheme   │ alpha         │ beta          │ rc            │ dev
    ─────────┼───────────────┼───────────────┼───────────────┼──────────────
    semver   │ 1.2.0-alpha.1 │ 1.2.0-beta.1  │ 1.2.0-rc.1    │ 1.2.0-dev.1
    pep440   │ 1.2.0a1       │ 1.2.0b1       │ 1.2.0rc1      │ 1.2.0.dev1

Usage::

    from releasekit.prerelease import (
        apply_prerelease,
        increment_prerelease,
        promote_to_stable,
        parse_prerelease,
    )

    # Create a pre-release version
    v = apply_prerelease('1.2.0', 'rc', scheme='semver')
    assert v == '1.2.0-rc.1'

    # Increment the pre-release counter
    v2 = increment_prerelease('1.2.0-rc.1', scheme='semver')
    assert v2 == '1.2.0-rc.2'

    # Promote to stable
    stable = promote_to_stable('1.2.0-rc.2', scheme='semver')
    assert stable == '1.2.0'
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from packaging.version import InvalidVersion, Version

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

# Valid pre-release labels.
VALID_LABELS: frozenset[str] = frozenset({'alpha', 'beta', 'rc', 'dev'})

# Label precedence order for escalation and sorting.
_LABEL_ORDER: dict[str, int] = {'dev': 0, 'alpha': 1, 'beta': 2, 'rc': 3}

# PEP 440 label mapping (label → PEP 440 suffix letter(s)).
_PEP440_SUFFIXES: dict[str, str] = {
    'alpha': 'a',
    'beta': 'b',
    'rc': 'rc',
    'dev': '.dev',
}

# Reverse mapping: PEP 440 suffix → label.
_PEP440_REVERSE: dict[str, str] = {v: k for k, v in _PEP440_SUFFIXES.items()}

# Regex for parsing semver pre-release: 1.2.3-label.N
_SEMVER_PRE_RE = re.compile(
    r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'
    r'-(?P<label>alpha|beta|rc|dev)\.(?P<num>\d+)'
    r'(?:\+.*)?$'
)

# Regex for parsing PEP 440 pre-release: 1.2.3a1, 1.2.3b1, 1.2.3rc1, 1.2.3.dev1
_PEP440_PRE_RE = re.compile(
    r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'
    r'(?P<suffix>\.dev|a|b|rc)(?P<num>\d+)'
    r'$'
)

# Regex for a plain semver base version (no pre-release).
_SEMVER_BASE_RE = re.compile(r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$')


@dataclass(frozen=True)
class PrereleaseInfo:
    """Parsed pre-release version information.

    Attributes:
        major: Major version number.
        minor: Minor version number.
        patch: Patch version number.
        label: Pre-release label (``"alpha"``, ``"beta"``, ``"rc"``,
            ``"dev"``). Empty string if this is a stable version.
        number: Pre-release counter (e.g. 1 for ``rc.1``). 0 for stable.
        scheme: Versioning scheme (``"semver"`` or ``"pep440"``).
    """

    major: int
    minor: int
    patch: int
    label: str = ''
    number: int = 0
    scheme: str = 'semver'

    @property
    def is_prerelease(self) -> bool:
        """Whether this is a pre-release version."""
        return bool(self.label)

    @property
    def base_version(self) -> str:
        """The base version without pre-release suffix."""
        return f'{self.major}.{self.minor}.{self.patch}'

    def format(self) -> str:
        """Format as a version string in the appropriate scheme."""
        if not self.label:
            return self.base_version
        if self.scheme == 'pep440':
            suffix = _PEP440_SUFFIXES[self.label]
            return f'{self.base_version}{suffix}{self.number}'
        # semver
        return f'{self.base_version}-{self.label}.{self.number}'


def parse_prerelease(version: str, *, scheme: str = '') -> PrereleaseInfo:
    """Parse a version string and extract pre-release information.

    Auto-detects the scheme if not specified by trying semver first,
    then PEP 440.

    Args:
        version: Version string to parse.
        scheme: ``"semver"``, ``"pep440"``, or ``""`` for auto-detect.

    Returns:
        Parsed :class:`PrereleaseInfo`.

    Raises:
        ReleaseKitError: If the version string cannot be parsed.
    """
    # Try semver pre-release.
    if scheme in ('semver', ''):
        m = _SEMVER_PRE_RE.match(version)
        if m:
            return PrereleaseInfo(
                major=int(m.group('major')),
                minor=int(m.group('minor')),
                patch=int(m.group('patch')),
                label=m.group('label'),
                number=int(m.group('num')),
                scheme='semver',
            )

    # Try PEP 440 pre-release.
    if scheme in ('pep440', ''):
        m = _PEP440_PRE_RE.match(version)
        if m:
            suffix = m.group('suffix')
            label = _PEP440_REVERSE.get(suffix, '')
            if label:
                return PrereleaseInfo(
                    major=int(m.group('major')),
                    minor=int(m.group('minor')),
                    patch=int(m.group('patch')),
                    label=label,
                    number=int(m.group('num')),
                    scheme='pep440',
                )

    # Try plain base version (stable).
    m = _SEMVER_BASE_RE.match(version.split('-')[0].split('+')[0])
    if m:
        return PrereleaseInfo(
            major=int(m.group('major')),
            minor=int(m.group('minor')),
            patch=int(m.group('patch')),
            scheme=scheme or 'semver',
        )

    raise ReleaseKitError(
        code=E.VERSION_INVALID,
        message=f'Cannot parse version {version!r} as a pre-release or stable version',
        hint='Use a version like "1.2.3", "1.2.3-rc.1" (semver), or "1.2.3rc1" (PEP 440).',
    )


def apply_prerelease(
    version: str,
    label: str,
    *,
    scheme: str = 'semver',
    number: int = 1,
) -> str:
    """Apply a pre-release label to a base version.

    If the version already has a pre-release suffix, it is replaced.

    Args:
        version: Base version (e.g. ``"1.2.0"``) or existing pre-release.
        label: Pre-release label: ``"alpha"``, ``"beta"``, ``"rc"``,
            or ``"dev"``.
        scheme: ``"semver"`` or ``"pep440"``.
        number: Pre-release counter (default 1).

    Returns:
        Version string with pre-release suffix.

    Raises:
        ReleaseKitError: If the label is invalid.
    """
    if label not in VALID_LABELS:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'Invalid pre-release label {label!r}',
            hint=f'Use one of: {sorted(VALID_LABELS)}',
        )

    info = parse_prerelease(version, scheme=scheme)
    result = PrereleaseInfo(
        major=info.major,
        minor=info.minor,
        patch=info.patch,
        label=label,
        number=number,
        scheme=scheme,
    )
    return result.format()


def increment_prerelease(version: str, *, scheme: str = '') -> str:
    """Increment the pre-release counter.

    ``1.2.0-rc.1`` → ``1.2.0-rc.2``, ``1.2.0a1`` → ``1.2.0a2``.

    Args:
        version: Existing pre-release version.
        scheme: ``"semver"``, ``"pep440"``, or ``""`` for auto-detect.

    Returns:
        Version with incremented counter.

    Raises:
        ReleaseKitError: If the version is not a pre-release.
    """
    info = parse_prerelease(version, scheme=scheme)
    if not info.is_prerelease:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Version {version!r} is not a pre-release — cannot increment',
            hint='Use apply_prerelease() to create a pre-release version first.',
        )

    result = PrereleaseInfo(
        major=info.major,
        minor=info.minor,
        patch=info.patch,
        label=info.label,
        number=info.number + 1,
        scheme=info.scheme,
    )
    return result.format()


def promote_to_stable(version: str, *, scheme: str = '') -> str:
    """Promote a pre-release version to stable by stripping the suffix.

    ``1.2.0-rc.2`` → ``1.2.0``, ``1.2.0rc2`` → ``1.2.0``.

    Args:
        version: Pre-release version to promote.
        scheme: ``"semver"``, ``"pep440"``, or ``""`` for auto-detect.

    Returns:
        Stable version string.

    Raises:
        ReleaseKitError: If the version is not a pre-release.
    """
    info = parse_prerelease(version, scheme=scheme)
    if not info.is_prerelease:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Version {version!r} is already stable — nothing to promote',
            hint='Only pre-release versions (e.g. 1.2.0-rc.1) can be promoted.',
        )

    logger.info(
        'promote_to_stable',
        from_version=version,
        to_version=info.base_version,
    )
    return info.base_version


def escalate_prerelease(
    version: str,
    new_label: str,
    *,
    scheme: str = '',
) -> str:
    """Escalate a pre-release to a higher stage.

    ``alpha`` → ``beta`` → ``rc``. Resets the counter to 1.

    Args:
        version: Current pre-release version.
        new_label: Target label (must be higher than current).
        scheme: ``"semver"``, ``"pep440"``, or ``""`` for auto-detect.

    Returns:
        Version with the new label and counter reset to 1.

    Raises:
        ReleaseKitError: If the escalation is invalid (e.g. rc → alpha).
    """
    if new_label not in _LABEL_ORDER:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'Invalid pre-release label {new_label!r}',
            hint=f'Use one of: {sorted(VALID_LABELS)}',
        )

    info = parse_prerelease(version, scheme=scheme)
    if not info.is_prerelease:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Version {version!r} is stable — cannot escalate',
            hint='Use apply_prerelease() to create a pre-release version first.',
        )

    current_order = _LABEL_ORDER.get(info.label, -1)
    new_order = _LABEL_ORDER[new_label]

    if new_order <= current_order:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Cannot escalate from {info.label!r} to {new_label!r} (not a higher stage)',
            hint=f'Escalation order: dev → alpha → beta → rc. Current: {info.label}.',
        )

    effective_scheme = scheme or info.scheme
    result = PrereleaseInfo(
        major=info.major,
        minor=info.minor,
        patch=info.patch,
        label=new_label,
        number=1,
        scheme=effective_scheme,
    )

    logger.info(
        'escalate_prerelease',
        from_version=version,
        to_version=result.format(),
        from_label=info.label,
        to_label=new_label,
    )
    return result.format()


def is_prerelease(version: str) -> bool:
    """Check if a version string is a pre-release.

    Args:
        version: Version string to check.

    Returns:
        True if the version has a pre-release suffix.
    """
    try:
        info = parse_prerelease(version)
        return info.is_prerelease
    except ReleaseKitError:
        return False


def prerelease_sort_key(version: str) -> tuple[int, int, int, int, int]:
    """Return a sort key for pre-release ordering.

    Stable versions sort after all pre-releases of the same base version.

    Args:
        version: Version string.

    Returns:
        Tuple suitable for sorting.
    """
    try:
        info = parse_prerelease(version)
    except ReleaseKitError:
        return (0, 0, 0, 99, 0)

    if info.is_prerelease:
        label_idx = _LABEL_ORDER.get(info.label, 0)
        return (info.major, info.minor, info.patch, label_idx, info.number)
    # Stable sorts after all pre-releases.
    return (info.major, info.minor, info.patch, 99, 0)


def validate_pep440(version: str) -> bool:
    """Check whether ``version`` is a valid PEP 440 version string.

    Uses :mod:`packaging.version` for canonical validation.

    Args:
        version: Version string to validate.

    Returns:
        ``True`` if the version is PEP 440 compliant.
    """
    try:
        Version(version)
    except InvalidVersion:
        return False
    return True


def normalize_pep440(version: str) -> str:
    """Normalize a version string to PEP 440 canonical form.

    ``1.02.3`` → ``1.2.3``, ``1.2.3.RC1`` → ``1.2.3rc1``, etc.

    Args:
        version: Version string to normalize.

    Returns:
        Normalized version string.

    Raises:
        ReleaseKitError: If the version is not PEP 440 compliant.
    """
    try:
        return str(Version(version))
    except InvalidVersion as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Version {version!r} is not PEP 440 compliant',
            hint=(
                'PEP 440 versions look like: 1.2.3, 1.2.3a1, 1.2.3b1, '
                '1.2.3rc1, 1.2.3.dev1, 1.2.3.post1. '
                'See https://peps.python.org/pep-0440/'
            ),
        ) from exc


def ensure_pep440(version: str, *, ecosystem: str = '') -> str:
    """Validate and normalize a version for the Python ecosystem.

    For non-Python ecosystems (or when ``ecosystem`` is empty), the
    version is returned unchanged.  For Python, the version is
    normalized to PEP 440 canonical form.

    Args:
        version: Version string.
        ecosystem: Ecosystem identifier (e.g. ``"python"``).

    Returns:
        The (possibly normalized) version string.

    Raises:
        ReleaseKitError: If the ecosystem is Python and the version
            is not PEP 440 compliant.
    """
    if ecosystem != 'python':
        return version
    return normalize_pep440(version)


__all__ = [
    'VALID_LABELS',
    'PrereleaseInfo',
    'apply_prerelease',
    'ensure_pep440',
    'escalate_prerelease',
    'increment_prerelease',
    'is_prerelease',
    'normalize_pep440',
    'parse_prerelease',
    'prerelease_sort_key',
    'promote_to_stable',
    'validate_pep440',
]
