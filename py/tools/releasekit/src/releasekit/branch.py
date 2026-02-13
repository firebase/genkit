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

"""Default branch resolution.

Provides :func:`resolve_default_branch` which checks the config override
first, then falls back to VCS auto-detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from releasekit.logging import get_logger

if TYPE_CHECKING:
    from releasekit.backends.vcs import VCS

logger = get_logger(__name__)


async def resolve_default_branch(
    vcs: VCS,
    config_override: str = '',
) -> str:
    """Resolve the default (trunk) branch name.

    Resolution order:

    1. ``config_override`` — if non-empty, use it directly (from
       ``releasekit.toml`` ``default_branch`` or CLI ``--default-branch``).
    2. ``vcs.default_branch()`` — auto-detect from the VCS backend
       (e.g. ``git symbolic-ref refs/remotes/origin/HEAD``).

    Args:
        vcs: VCS backend for auto-detection.
        config_override: Explicit branch name from config. If empty,
            auto-detect from VCS.

    Returns:
        The resolved branch name (e.g. ``"main"``, ``"master"``).
    """
    if config_override:
        logger.debug('default_branch_from_config', branch=config_override)
        return config_override

    branch = await vcs.default_branch()
    logger.debug('default_branch_auto_detected', branch=branch)
    return branch


__all__ = [
    'resolve_default_branch',
]
