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

r"""Plugin trust verification for releasekit.

Enforces a trust chain for backend plugins and hook scripts.
Releasekit refuses to load unsigned or untrusted extensions in
strict mode (default in CI).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Hook allowlist      │ Only commands in the allowlist can be run as  │
    │                     │ lifecycle hooks. Blocks arbitrary execution.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Script pinning      │ Hook scripts referenced by path must have    │
    │                     │ their SHA-256 digest pinned in config.        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Strict mode         │ In CI, unpinned scripts and disallowed       │
    │                     │ commands are refused (fail-closed).           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Trusted publishers  │ OIDC identity → list of allowed packages.    │
    │                     │ Backend plugins must match to be loaded.      │
    └─────────────────────┴────────────────────────────────────────────────┘

Trust chain::

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    Plugin Trust Chain                                │
    │                                                                     │
    │  Hook command ──▶ Is executable in allowlist? ──▶ Allow / Refuse   │
    │                                                                     │
    │  Hook script  ──▶ SHA-256 matches pinned digest? ──▶ Allow / Refuse│
    │                                                                     │
    │  Backend pkg  ──▶ Publisher in trusted_publishers? ──▶ Allow / Refuse│
    └─────────────────────────────────────────────────────────────────────┘

Usage::

    from releasekit.trust import (
        TrustConfig,
        verify_hook_command,
        verify_hook_script,
    )

    cfg = TrustConfig(
        hook_allowlist=['uv', 'pnpm', 'go', 'bazel'],
        strict_hooks=True,
    )
    result = verify_hook_command('uv run pytest', cfg)
    assert result.allowed
"""

from __future__ import annotations

import hashlib
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.logging import get_logger

logger = get_logger(__name__)

# Default set of executables allowed in lifecycle hooks.
DEFAULT_HOOK_ALLOWLIST: frozenset[str] = frozenset({
    'bazel',
    'cargo',
    'dart',
    'go',
    'gradle',
    'mvn',
    'npm',
    'npx',
    'pnpm',
    'pub',
    'uv',
})


@dataclass(frozen=True)
class TrustConfig:
    """Configuration for plugin and hook trust verification.

    Attributes:
        hook_allowlist: Set of executable names allowed in hooks.
        strict_hooks: If ``True``, refuse unpinned scripts and
            disallowed commands. Defaults to ``True`` in CI.
        pinned_scripts: Mapping of script path → expected SHA-256 hex digest.
        plugin_verification: If ``True``, require Sigstore attestation
            for backend plugins.
        trusted_publishers: Mapping of OIDC issuer → list of allowed
            publisher subjects.
    """

    hook_allowlist: frozenset[str] = DEFAULT_HOOK_ALLOWLIST
    strict_hooks: bool = True
    pinned_scripts: dict[str, str] = field(default_factory=dict)
    plugin_verification: bool = True
    trusted_publishers: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class TrustResult:
    """Result of a trust verification check.

    Attributes:
        allowed: Whether the operation is allowed.
        subject: The command, script path, or package name checked.
        reason: Human-readable explanation.
        hint: Actionable suggestion if not allowed.
    """

    allowed: bool
    subject: str
    reason: str = ''
    hint: str = ''


def verify_hook_command(
    command: str,
    config: TrustConfig,
) -> TrustResult:
    """Verify that a hook command uses an allowed executable.

    Parses the command string and checks that the first token (the
    executable) is in the hook allowlist.

    Args:
        command: The full hook command string (e.g. ``'uv run pytest'``).
        config: Trust configuration with the allowlist.

    Returns:
        A :class:`TrustResult`.
    """
    if not command.strip():
        return TrustResult(
            allowed=False,
            subject=command,
            reason='Empty hook command',
            hint='Remove empty hook entries from releasekit.toml.',
        )

    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return TrustResult(
            allowed=False,
            subject=command,
            reason=f'Failed to parse hook command: {exc}',
            hint='Ensure the hook command is valid shell syntax.',
        )

    executable = Path(tokens[0]).name
    if executable in config.hook_allowlist:
        return TrustResult(
            allowed=True,
            subject=command,
            reason=f'Executable {executable!r} is in the allowlist',
        )

    if not config.strict_hooks:
        logger.warning(
            'hook_not_in_allowlist',
            command=command,
            executable=executable,
        )
        return TrustResult(
            allowed=True,
            subject=command,
            reason=f'Executable {executable!r} not in allowlist (strict_hooks=false, allowing)',
        )

    return TrustResult(
        allowed=False,
        subject=command,
        reason=f'Executable {executable!r} is not in the hook allowlist',
        hint=(
            f'Add {executable!r} to [security].hook_allowlist in releasekit.toml, '
            f'or set strict_hooks = false to allow any executable.'
        ),
    )


def verify_hook_script(
    script_path: Path,
    config: TrustConfig,
) -> TrustResult:
    """Verify that a hook script's SHA-256 digest matches the pinned value.

    Args:
        script_path: Path to the hook script file.
        config: Trust configuration with pinned digests.

    Returns:
        A :class:`TrustResult`.
    """
    path_str = str(script_path)

    if not script_path.is_file():
        return TrustResult(
            allowed=False,
            subject=path_str,
            reason=f'Hook script not found: {script_path}',
            hint='Ensure the script path in [hooks] is correct.',
        )

    expected_digest = config.pinned_scripts.get(path_str)
    if expected_digest is None:
        if not config.strict_hooks:
            return TrustResult(
                allowed=True,
                subject=path_str,
                reason='Script not pinned (strict_hooks=false, allowing)',
            )
        return TrustResult(
            allowed=False,
            subject=path_str,
            reason='Hook script is not pinned in [security].pinned_scripts',
            hint=(
                f'Pin the script by adding its SHA-256 digest to releasekit.toml:\n'
                f'  [security.pinned_scripts]\n'
                f'  "{path_str}" = "<sha256>"'
            ),
        )

    # Compute actual digest.
    actual_digest = hashlib.sha256(script_path.read_bytes()).hexdigest()
    if actual_digest == expected_digest:
        return TrustResult(
            allowed=True,
            subject=path_str,
            reason='Script SHA-256 digest matches pinned value',
        )

    return TrustResult(
        allowed=False,
        subject=path_str,
        reason=(f'Script SHA-256 mismatch: expected {expected_digest[:16]}..., got {actual_digest[:16]}...'),
        hint=(
            'The hook script has been modified since it was pinned. '
            'Update the digest in [security].pinned_scripts or investigate the change.'
        ),
    )


def verify_publisher(
    package_name: str,
    publisher_issuer: str,
    publisher_subject: str,
    config: TrustConfig,
) -> TrustResult:
    """Verify that a backend package comes from a trusted publisher.

    Args:
        package_name: The Python package name (e.g. ``'releasekit-backend-go'``).
        publisher_issuer: The OIDC issuer of the package publisher.
        publisher_subject: The OIDC subject of the package publisher.
        config: Trust configuration with trusted publishers.

    Returns:
        A :class:`TrustResult`.
    """
    if not config.plugin_verification:
        return TrustResult(
            allowed=True,
            subject=package_name,
            reason='Plugin verification disabled (plugin_verification=false)',
        )

    allowed_subjects = config.trusted_publishers.get(publisher_issuer, [])
    if publisher_subject in allowed_subjects:
        return TrustResult(
            allowed=True,
            subject=package_name,
            reason=f'Publisher {publisher_subject!r} is trusted for issuer {publisher_issuer!r}',
        )

    return TrustResult(
        allowed=False,
        subject=package_name,
        reason=(f'Publisher {publisher_subject!r} (issuer {publisher_issuer!r}) is not in [trusted_publishers]'),
        hint=(
            f'Add the publisher to releasekit.toml:\n'
            f'  [trusted_publishers]\n'
            f'  "{publisher_issuer}" = ["{publisher_subject}"]'
        ),
    )


def compute_script_digest(script_path: Path) -> str:
    """Compute the SHA-256 hex digest of a script file.

    Utility for users to generate the digest for pinning.

    Args:
        script_path: Path to the script file.

    Returns:
        The SHA-256 hex digest string.

    Raises:
        FileNotFoundError: If the script does not exist.
    """
    return hashlib.sha256(script_path.read_bytes()).hexdigest()


__all__ = [
    'DEFAULT_HOOK_ALLOWLIST',
    'TrustConfig',
    'TrustResult',
    'compute_script_digest',
    'verify_hook_command',
    'verify_hook_script',
    'verify_publisher',
]
