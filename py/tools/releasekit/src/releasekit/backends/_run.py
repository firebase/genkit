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

"""Central subprocess abstraction for releasekit.

All external tool calls (``uv``, ``git``, ``gh``) go through
:func:`run_command`. This provides:

- Structured logging of every subprocess invocation.
- Dry-run support: when ``dry_run=True``, the command is logged but not
  executed, and a synthetic success result is returned.
- Configurable timeout with clear error messages.
- Consistent return type (:class:`CommandResult`) across all backends.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ run_command         │ A single function that runs any shell command. │
    │                     │ Like a universal remote for uv, git, and gh.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ CommandResult       │ A receipt for the command you ran. Tells you  │
    │                     │ if it worked, what it printed, and how long.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ dry_run             │ Pretend mode. Logs what would happen but       │
    │                     │ doesn't actually do anything. Safe to test.   │
    └─────────────────────┴────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import subprocess  # noqa: S404 - subprocess is the core purpose of this module
import time
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.logging import get_logger

log = get_logger('releasekit.backends.run')

# Default timeout for subprocess calls (5 minutes).
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class CommandResult:
    """Result of a subprocess invocation.

    Attributes:
        command: The command that was executed (as a list of strings).
        return_code: Process exit code (0 = success).
        stdout: Captured standard output.
        stderr: Captured standard error.
        duration: Wall-clock duration in milliseconds.
        dry_run: Whether this was a dry-run (command was not actually executed).
    """

    command: list[str]
    return_code: int
    stdout: str = ''
    stderr: str = ''
    duration: float = 0.0
    dry_run: bool = False
    env_overrides: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Whether the command succeeded (return_code == 0 or dry-run)."""
        return self.return_code == 0

    @property
    def command_str(self) -> str:
        """The command as a single shell-style string."""
        return ' '.join(self.command)


def run_command(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False,
    capture: bool = True,
    check: bool = False,
) -> CommandResult:
    """Execute a subprocess command with logging and dry-run support.

    Args:
        cmd: Command and arguments as a list of strings.
        cwd: Working directory for the command.
        env: Extra environment variables to set (merged with current env).
        timeout: Maximum seconds to wait before killing the process.
        dry_run: If ``True``, log the command but don't execute it.
        capture: If ``True``, capture stdout and stderr.
        check: If ``True``, raise :class:`subprocess.CalledProcessError`
            on non-zero exit code.

    Returns:
        A :class:`CommandResult` with the command output and metadata.

    Raises:
        subprocess.CalledProcessError: If ``check=True`` and the command
            exits with a non-zero code.
        subprocess.TimeoutExpired: If the command exceeds ``timeout``.
    """
    cmd_str = ' '.join(cmd)
    log.debug('run_command', cmd=cmd_str, cwd=str(cwd or '.'), dry_run=dry_run)

    if dry_run:
        log.info('dry_run', cmd=cmd_str)
        return CommandResult(
            command=cmd,
            return_code=0,
            stdout='',
            stderr='',
            duration=0.0,
            dry_run=True,
            env_overrides=env or {},
        )

    full_env: dict[str, str] | None = None
    if env:
        full_env = {**os.environ, **env}

    start = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603 -- trusted inputs from backends
            cmd,
            cwd=cwd,
            env=full_env,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        duration = (time.monotonic() - start) * 1000
        log.error('command_timeout', cmd=cmd_str, timeout=timeout, duration=duration)
        raise

    duration = (time.monotonic() - start) * 1000
    cmd_result = CommandResult(
        command=cmd,
        return_code=result.returncode,
        stdout=result.stdout if capture else '',
        stderr=result.stderr if capture else '',
        duration=duration,
        dry_run=False,
        env_overrides=env or {},
    )

    if result.returncode != 0:
        log.warning(
            'command_failed',
            cmd=cmd_str,
            return_code=result.returncode,
            stderr=result.stderr[:500] if capture else '',
            duration=duration,
        )
        if check:
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=result.stderr,
            )
    else:
        log.debug('command_ok', cmd=cmd_str, duration=duration)

    return cmd_result


__all__ = [
    'CalledProcessError',
    'CommandResult',
    'DEFAULT_TIMEOUT_SECONDS',
    'TimeoutExpired',
    'run_command',
]

# Re-export subprocess exceptions so consumers don't need to import
# subprocess directly (which triggers S404).
CalledProcessError = subprocess.CalledProcessError
TimeoutExpired = subprocess.TimeoutExpired
