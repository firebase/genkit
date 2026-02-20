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

"""Branch-to-channel mapping for releasekit.

Maps the current git branch to a release channel (dist-tag or
prerelease suffix) using the ``[branches]`` configuration.

Configuration example::

    [branches]
    main             = "latest"
    next             = "next"
    beta             = "beta"
    "release/v1.*"   = "v1-maintenance"

The mapping supports exact matches and glob patterns (via
:func:`fnmatch.fnmatch`).

Usage::

    from releasekit.channels import resolve_channel

    channel = resolve_channel('next', {'main': 'latest', 'next': 'next'})
    assert channel == 'next'

    channel = resolve_channel('release/v1.5', {'release/v1.*': 'v1-maint'})
    assert channel == 'v1-maint'
"""

from __future__ import annotations

import fnmatch

from releasekit.logging import get_logger

log = get_logger('releasekit.channels')


def resolve_channel(
    branch: str,
    branches: dict[str, str],
    *,
    default: str = 'latest',
) -> str:
    """Resolve the release channel for a git branch.

    Tries exact match first, then glob patterns.

    Args:
        branch: Current git branch name (e.g. ``"main"``, ``"next"``,
            ``"release/v1.5"``).
        branches: Branch-to-channel mapping from ``[branches]`` config.
        default: Default channel if no match is found.

    Returns:
        The channel name (e.g. ``"latest"``, ``"next"``, ``"beta"``).
    """
    if not branches:
        return default

    # Exact match first.
    if branch in branches:
        channel = branches[branch]
        log.debug('channel_exact_match', branch=branch, channel=channel)
        return channel

    # Glob pattern match.
    for pattern, channel in branches.items():
        if fnmatch.fnmatch(branch, pattern):
            log.debug('channel_glob_match', branch=branch, pattern=pattern, channel=channel)
            return channel

    log.debug('channel_default', branch=branch, default=default)
    return default


def channel_to_dist_tag(channel: str) -> str | None:
    """Convert a channel name to an npm dist-tag.

    Returns ``None`` for ``"latest"`` (the npm default), otherwise
    returns the channel name as the dist-tag.

    Args:
        channel: Channel name from :func:`resolve_channel`.

    Returns:
        Dist-tag string, or ``None`` for the default channel.
    """
    if channel == 'latest':
        return None
    return channel


def channel_to_prerelease(channel: str) -> str:
    """Convert a channel name to a prerelease label.

    Returns an empty string for ``"latest"`` (stable release),
    otherwise returns the channel name as the prerelease label
    (e.g. ``"next"`` → ``"next"``, ``"beta"`` → ``"beta"``).

    Args:
        channel: Channel name from :func:`resolve_channel`.

    Returns:
        Prerelease label string, or empty string for stable.
    """
    if channel == 'latest':
        return ''
    return channel


__all__ = [
    'channel_to_dist_tag',
    'channel_to_prerelease',
    'resolve_channel',
]
