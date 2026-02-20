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

"""Shared async file I/O helpers for workspace backends.

All workspace protocol methods are ``async def`` to avoid blocking
the event loop. These helpers wrap ``aiofiles`` with consistent
error handling so that each backend doesn't need to duplicate the
boilerplate.
"""

from __future__ import annotations

from pathlib import Path

import aiofiles

from releasekit.errors import E, ReleaseKitError


async def read_file(path: Path) -> str:
    """Read a UTF-8 text file asynchronously via aiofiles."""
    try:
        async with aiofiles.open(path, encoding='utf-8') as f:
            return await f.read()
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to read {path}: {exc}',
            hint=f'Check that {path} exists and is readable.',
        ) from exc


async def write_file(path: Path, content: str) -> None:
    """Write a UTF-8 text file asynchronously via aiofiles."""
    try:
        async with aiofiles.open(path, mode='w', encoding='utf-8') as f:
            await f.write(content)
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to write {path}: {exc}',
            hint=f'Check file permissions for {path}.',
        ) from exc
