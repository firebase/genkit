#!/usr/bin/env python3
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

"""Dump all releasekit diagnostic formatting to the terminal.

Run this script to preview every error and warning style:

    uv run scripts/dump_diagnostics.py
"""

from __future__ import annotations

import sys

from releasekit.errors import (
    ERRORS,
    E,
    ReleaseKitError,
    ReleaseKitWarning,
    render_error,
    render_warning,
)


def main() -> None:
    """Render all registered errors, then sample warnings."""
    print('─' * 60, file=sys.stderr)  # noqa: T201 - CLI script
    print(  # noqa: T201 - CLI script
        '  releasekit diagnostic formatting gallery',
        file=sys.stderr,
    )
    print('─' * 60, file=sys.stderr)  # noqa: T201 - CLI script
    print(file=sys.stderr)  # noqa: T201 - CLI script

    # Render every registered error (these have messages + hints).
    print(  # noqa: T201 - CLI script
        '── Registered errors (with hints) ──',
        file=sys.stderr,
    )
    print(file=sys.stderr)  # noqa: T201 - CLI script
    for code, info in ERRORS.items():
        exc = ReleaseKitError(code=code, message=info.message, hint=info.hint)
        render_error(exc, file=sys.stderr)

    # Render errors without hints.
    print(  # noqa: T201 - CLI script
        '── Error without hint ──',
        file=sys.stderr,
    )
    print(file=sys.stderr)  # noqa: T201 - CLI script
    render_error(
        ReleaseKitError(
            code=E.BUILD_FAILED,
            message='Package genkit-plugin-ollama failed to build.',
        ),
        file=sys.stderr,
    )

    # Render errors with brackets in messages (regression test).
    print(  # noqa: T201 - CLI script
        '── Bracket preservation ──',
        file=sys.stderr,
    )
    print(file=sys.stderr)  # noqa: T201 - CLI script
    render_error(
        ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message='No [tool.releasekit] section in pyproject.toml.',
            hint="Add [tool.releasekit] with 'releasekit init'.",
        ),
        file=sys.stderr,
    )

    # Render warnings.
    print(  # noqa: T201 - CLI script
        '── Warnings ──',
        file=sys.stderr,
    )
    print(file=sys.stderr)  # noqa: T201 - CLI script
    render_warning(
        ReleaseKitWarning(
            code=E.PREFLIGHT_SHALLOW_CLONE,
            message='Repository is a shallow clone; git log data may be incomplete.',
            hint="Run 'git fetch --unshallow' to fetch full history.",
        ),
        file=sys.stderr,
    )
    render_warning(
        ReleaseKitWarning(
            code=E.PREFLIGHT_DIRTY_WORKTREE,
            message='Working tree has uncommitted changes.',
        ),
        file=sys.stderr,
    )

    print('─' * 60, file=sys.stderr)  # noqa: T201 - CLI script
    print('  Done.', file=sys.stderr)  # noqa: T201 - CLI script
    print('─' * 60, file=sys.stderr)  # noqa: T201 - CLI script


if __name__ == '__main__':
    main()
