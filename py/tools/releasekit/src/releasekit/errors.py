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

"""Structured error system for releasekit.

Every error has a unique ``RK-NAMED-KEY`` code, a human-readable message,
and an optional hint with a suggested fix.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ ErrorCode           │ A unique named ID like "RK-CONFIG-NOT-FOUND"  │
    │                     │ for each error. Readable at a glance.         │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ ErrorInfo           │ A bundle of code + message + hint. Like an    │
    │                     │ error card with a fix suggestion stapled on.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ ReleaseKitError     │ An exception you can raise. Carries the       │
    │                     │ error card so renderers can display it.       │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ ERRORS catalog      │ Pre-built error cards for common mistakes.    │
    │                     │ Like a FAQ for release problems.              │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ explain()           │ Looks up an error code and prints details.    │
    │                     │ Like typing a code into a help desk kiosk.    │
    └─────────────────────┴────────────────────────────────────────────────┘

Code categories::

    RK-CONFIG-*       Configuration errors
    RK-WORKSPACE-*    Workspace discovery errors
    RK-GRAPH-*        Dependency graph errors
    RK-VERSION-*      Versioning errors
    RK-PREFLIGHT-*    Preflight check errors
    RK-BUILD-*        Build errors
    RK-PUBLISH-*      Publish errors
    RK-TAG-*          Tag / release creation errors
    RK-STATE-*        State / resume errors

Usage::

    from releasekit.errors import ReleaseKitError, E

    raise ReleaseKitError(
        code=E.CONFIG_NOT_FOUND,
        message='No [tool.releasekit] section found in pyproject.toml',
        hint="Run 'releasekit init' to generate a default config.",
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCode(str, Enum):
    """Enumeration of all releasekit diagnostic codes.

    Each code maps to a unique ``RK-NAMED-KEY`` identifier. Use these
    constants instead of raw strings when raising :class:`ReleaseKitError`.
    """

    # Configuration
    CONFIG_NOT_FOUND = 'RK-CONFIG-NOT-FOUND'
    CONFIG_INVALID_KEY = 'RK-CONFIG-INVALID-KEY'
    CONFIG_INVALID_VALUE = 'RK-CONFIG-INVALID-VALUE'
    CONFIG_MISSING_REQUIRED = 'RK-CONFIG-MISSING-REQUIRED'

    # Workspace discovery
    WORKSPACE_NOT_FOUND = 'RK-WORKSPACE-NOT-FOUND'
    WORKSPACE_NO_MEMBERS = 'RK-WORKSPACE-NO-MEMBERS'
    WORKSPACE_PARSE_ERROR = 'RK-WORKSPACE-PARSE-ERROR'
    WORKSPACE_DUPLICATE_PACKAGE = 'RK-WORKSPACE-DUPLICATE-PACKAGE'

    # Dependency graph
    GRAPH_CYCLE_DETECTED = 'RK-GRAPH-CYCLE-DETECTED'
    GRAPH_MISSING_DEPENDENCY = 'RK-GRAPH-MISSING-DEPENDENCY'

    # Versioning
    VERSION_INVALID = 'RK-VERSION-INVALID'
    VERSION_NOT_BUMPED = 'RK-VERSION-NOT-BUMPED'
    VERSION_TAG_EXISTS = 'RK-VERSION-TAG-EXISTS'

    # Preflight
    PREFLIGHT_DIRTY_WORKTREE = 'RK-PREFLIGHT-DIRTY-WORKTREE'
    PREFLIGHT_LOCK_STALE = 'RK-PREFLIGHT-LOCK-STALE'
    PREFLIGHT_SHALLOW_CLONE = 'RK-PREFLIGHT-SHALLOW-CLONE'
    PREFLIGHT_CONCURRENT_RELEASE = 'RK-PREFLIGHT-CONCURRENT-RELEASE'
    PREFLIGHT_GH_UNAVAILABLE = 'RK-PREFLIGHT-GH-UNAVAILABLE'
    PREFLIGHT_VERSION_EXISTS = 'RK-PREFLIGHT-VERSION-EXISTS'

    # Build / publish
    BUILD_FAILED = 'RK-BUILD-FAILED'
    PUBLISH_FAILED = 'RK-PUBLISH-FAILED'
    PUBLISH_TIMEOUT = 'RK-PUBLISH-TIMEOUT'
    PUBLISH_CHECKSUM_MISMATCH = 'RK-PUBLISH-CHECKSUM-MISMATCH'
    PUBLISH_ALREADY_EXISTS = 'RK-PUBLISH-ALREADY-EXISTS'
    SMOKE_TEST_FAILED = 'RK-SMOKE-TEST-FAILED'
    PIN_RESTORE_FAILED = 'RK-PIN-RESTORE-FAILED'

    # Post-pipeline
    TAG_CREATION_FAILED = 'RK-TAG-CREATION-FAILED'
    RELEASE_CREATION_FAILED = 'RK-RELEASE-CREATION-FAILED'
    CHANGELOG_GENERATION_FAILED = 'RK-CHANGELOG-GENERATION-FAILED'

    # State / resume
    STATE_CORRUPTED = 'RK-STATE-CORRUPTED'
    STATE_SHA_MISMATCH = 'RK-STATE-SHA-MISMATCH'
    LOCK_ACQUISITION_FAILED = 'RK-LOCK-ACQUISITION-FAILED'


# Convenience alias for shorter imports.
E = ErrorCode


@dataclass(frozen=True)
class ErrorInfo:
    """Metadata for a single error code.

    Attributes:
        code: The ``RK-NAMED-KEY`` error code.
        message: Human-readable description of what went wrong.
        hint: Optional suggestion for how to fix the error.
    """

    code: ErrorCode
    message: str
    hint: str = ''


class ReleaseKitError(Exception):
    """Base exception for all releasekit errors.

    Carries structured diagnostic information (code, message, hint) that
    can be rendered as a rich terminal message or structured JSON.

    Args:
        code: The error code from :class:`ErrorCode`.
        message: Human-readable description of what went wrong.
        hint: Optional suggestion for how to fix the error.
    """

    def __init__(self, code: ErrorCode, message: str, hint: str = '') -> None:
        """Initialize with an error code, message, and optional hint."""
        self.info = ErrorInfo(code=code, message=message, hint=hint)
        super().__init__(f'[{code.value}] {message}')

    @property
    def code(self) -> ErrorCode:
        """The error code."""
        return self.info.code

    @property
    def hint(self) -> str:
        """Suggestion for fixing this error, or empty string."""
        return self.info.hint


class ReleaseKitWarning(UserWarning):
    """Base warning for all releasekit warnings.

    Same structure as :class:`ReleaseKitError` but emitted via
    :func:`warnings.warn` instead of being raised.

    Args:
        code: The error code from :class:`ErrorCode`.
        message: Human-readable description of the warning.
        hint: Optional suggestion for how to address the warning.
    """

    def __init__(self, code: ErrorCode, message: str, hint: str = '') -> None:
        """Initialize with an error code, message, and optional hint."""
        self.info = ErrorInfo(code=code, message=message, hint=hint)
        super().__init__(f'[{code.value}] {message}')

    @property
    def code(self) -> ErrorCode:
        """The error code."""
        return self.info.code

    @property
    def hint(self) -> str:
        """Suggestion for addressing this warning, or empty string."""
        return self.info.hint


ERRORS: dict[ErrorCode, ErrorInfo] = {
    E.CONFIG_NOT_FOUND: ErrorInfo(
        code=E.CONFIG_NOT_FOUND,
        message='No [tool.releasekit] section found in pyproject.toml.',
        hint="Run 'releasekit init' to generate a default configuration.",
    ),
    E.WORKSPACE_NOT_FOUND: ErrorInfo(
        code=E.WORKSPACE_NOT_FOUND,
        message='No [tool.uv.workspace] section found in pyproject.toml.',
        hint='Ensure the project root contains a pyproject.toml with a [tool.uv.workspace] section.',
    ),
    E.GRAPH_CYCLE_DETECTED: ErrorInfo(
        code=E.GRAPH_CYCLE_DETECTED,
        message='Circular dependency detected in the workspace dependency graph.',
        hint="Run 'releasekit check-cycles' to identify the cycle.",
    ),
    E.PREFLIGHT_DIRTY_WORKTREE: ErrorInfo(
        code=E.PREFLIGHT_DIRTY_WORKTREE,
        message='Working tree has uncommitted changes.',
        hint='Commit or stash your changes before publishing.',
    ),
    E.PREFLIGHT_SHALLOW_CLONE: ErrorInfo(
        code=E.PREFLIGHT_SHALLOW_CLONE,
        message='Repository is a shallow clone; git log data may be incomplete.',
        hint="Run 'git fetch --unshallow' to fetch full history.",
    ),
}


def explain(code: str) -> str | None:
    """Return a detailed explanation for an error code.

    Args:
        code: The error code string, e.g. ``"RK-CONFIG-NOT-FOUND"``.

    Returns:
        A formatted explanation string, or ``None`` if the code is unknown.
    """
    try:
        error_code = ErrorCode(code)
    except ValueError:
        return None

    info = ERRORS.get(error_code)
    if info is None:
        return f'{code}: No detailed explanation available.'

    lines = [f'{code}: {info.message}']
    if info.hint:
        lines.append(f'  Hint: {info.hint}')
    return '\n'.join(lines)


__all__ = [
    'E',
    'ERRORS',
    'ErrorCode',
    'ErrorInfo',
    'ReleaseKitError',
    'ReleaseKitWarning',
    'explain',
]
