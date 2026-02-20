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

"""Release group filtering for releasekit.

A release group is a named subset of workspace packages that should be
released together. Groups are defined in ``[tool.releasekit]`` using
glob patterns that match package names::

    [tool.releasekit]
    groups.core = ['genkit', 'genkit-plugin-*']
    groups.samples = ['sample-*']

When a ``--group`` flag is passed to the CLI, only packages matching
the selected group's patterns are included in the release pipeline.
This enables monorepos with multiple independent release cadences.

Key Concepts (ELI5)::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ Explanation                               │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Release Group           │ A named set of glob patterns that match   │
    │                         │ package names. Like a label on a box.     │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ filter_by_group()       │ Takes all packages + a group name, and    │
    │                         │ returns only the ones whose names match   │
    │                         │ the group's glob patterns.                │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ list_groups()           │ Returns all available group names and     │
    │                         │ their patterns for display.               │
    └─────────────────────────┴────────────────────────────────────────────┘

Data Flow::

    groups config                filter_by_group()
    ┌──────────────────┐        ┌──────────────────────────┐
    │ core:            │        │ 1. Look up group name    │
    │   - genkit       │ ──────>│ 2. For each package:     │
    │   - genkit-*     │        │    match name vs patterns│
    │ samples:         │        │ 3. Return matches only   │
    │   - sample-*     │        └──────────┬───────────────┘
    └──────────────────┘                   │
                                     list[Package]
                                    (filtered subset)

Usage::

    from releasekit.groups import filter_by_group, list_groups

    # Filter packages to just the "core" group.
    core_pkgs = filter_by_group(packages, groups=config.groups, group='core')

    # Show available groups.
    for name, patterns in list_groups(config.groups):
        print(f'{name}: {patterns}')
"""

from __future__ import annotations

import fnmatch

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger
from releasekit.workspace import Package

log = get_logger(__name__)


def filter_by_group(
    packages: list[Package],
    *,
    groups: dict[str, list[str]],
    group: str,
) -> list[Package]:
    """Filter packages to those matching a named release group.

    Each group is a list of glob patterns applied against package names.
    A package is included if its name matches **any** pattern in the group.

    Args:
        packages: All workspace packages.
        groups: Group definitions from ``[tool.releasekit]``.
        group: Name of the group to filter by.

    Returns:
        Filtered list of packages whose names match the group patterns.

    Raises:
        ReleaseKitError: If the named group does not exist.

    Example::

        >>> groups = {'core': ['genkit', 'genkit-plugin-*']}
        >>> pkgs = [Package(name='genkit', ...), Package(name='sample-chat', ...)]
        >>> filter_by_group(pkgs, groups=groups, group='core')
        [Package(name='genkit', ...)]
    """
    if group not in groups:
        available = ', '.join(sorted(groups)) if groups else '(none defined)'
        raise ReleaseKitError(
            E.CONFIG_INVALID_VALUE,
            f"Unknown release group '{group}'.",
            hint=f'Available groups: {available}. Define groups in [tool.releasekit] groups.{group} = ["pattern"]',
        )

    patterns = groups[group]
    log.info('filter_by_group', group=group, patterns=patterns, total=len(packages))

    matched = [pkg for pkg in packages if any(fnmatch.fnmatch(pkg.name, pat) for pat in patterns)]

    log.info(
        'group_filter_result',
        group=group,
        matched=len(matched),
        names=[pkg.name for pkg in matched],
    )

    return matched


def list_groups(groups: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    """Return all available groups as sorted (name, patterns) pairs.

    Args:
        groups: Group definitions from ``[tool.releasekit]``.

    Returns:
        Sorted list of ``(group_name, patterns)`` tuples.
    """
    return sorted(groups.items())


def validate_group(
    groups: dict[str, list[str]],
    group: str,
    packages: list[Package],
) -> list[str]:
    """Validate a group and return warnings about empty matches.

    Checks each pattern in the group against the workspace packages.
    Returns a list of warning messages for patterns that match zero packages.
    This helps catch typos in group definitions.

    Args:
        groups: Group definitions.
        group: Group name to validate.
        packages: All workspace packages.

    Returns:
        List of warning strings. Empty means all patterns matched something.

    Raises:
        ReleaseKitError: If the group does not exist.
    """
    if group not in groups:
        available = ', '.join(sorted(groups)) if groups else '(none defined)'
        raise ReleaseKitError(
            E.CONFIG_INVALID_VALUE,
            f"Unknown release group '{group}'.",
            hint=f'Available groups: {available}.',
        )

    warnings: list[str] = []
    patterns = groups[group]
    pkg_names = [pkg.name for pkg in packages]

    for pattern in patterns:
        matched_names = fnmatch.filter(pkg_names, pattern)
        if not matched_names:
            warnings.append(f"Pattern '{pattern}' in group '{group}' matches 0 packages.")

    return warnings


__all__ = [
    'filter_by_group',
    'list_groups',
    'validate_group',
]
