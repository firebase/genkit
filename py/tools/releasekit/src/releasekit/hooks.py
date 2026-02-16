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

"""Lifecycle hooks for releasekit.

Executes shell commands at specific points in the release pipeline:

- ``before_prepare``: Before version bumps and changelog generation.
- ``before_publish``: Before publishing packages to registries.
- ``after_publish``: After publishing packages to registries.
- ``after_tag``: After creating git tags.

Hooks are defined in ``[hooks]`` sections of ``releasekit.toml`` and
support template variables: ``${version}``, ``${name}``, ``${tag}``.

Hook merge semantics:

    Hooks **concatenate** across tiers (root → workspace → package)
    unless ``hooks_replace = true`` is set at the workspace or package
    level, in which case only that level's hooks are used.

Usage::

    from releasekit.hooks import merge_hooks, run_hooks

    effective = merge_hooks(root_hooks, ws_hooks, pkg_hooks, replace=False)
    results = await run_hooks(
        effective,
        event='before_publish',
        variables={'version': '1.2.3', 'name': 'my-pkg', 'tag': 'v1.2.3'},
        cwd=workspace_root,
    )
"""

from __future__ import annotations

import asyncio
import shlex
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.config import HooksConfig
from releasekit.logging import get_logger

log = get_logger('releasekit.hooks')


def merge_hooks(
    root: HooksConfig,
    workspace: HooksConfig | None = None,
    package: HooksConfig | None = None,
    *,
    replace: bool = False,
) -> HooksConfig:
    """Merge hooks across configuration tiers.

    By default, hooks **concatenate** (root → workspace → package).
    If ``replace`` is ``True``, only the most specific tier is used.

    Args:
        root: Root-level hooks from ``releasekit.toml``.
        workspace: Workspace-level hooks (optional).
        package: Package-level hooks (optional).
        replace: If ``True``, use only the most specific tier.

    Returns:
        Merged :class:`HooksConfig`.
    """
    if replace:
        # Most specific tier wins.
        if package and _has_hooks(package):
            return package
        if workspace and _has_hooks(workspace):
            return workspace
        return root

    # Concatenate: root → workspace → package.
    before_prepare = list(root.before_prepare)
    before_publish = list(root.before_publish)
    after_publish = list(root.after_publish)
    after_tag = list(root.after_tag)

    for tier in (workspace, package):
        if tier is None:
            continue
        before_prepare.extend(tier.before_prepare)
        before_publish.extend(tier.before_publish)
        after_publish.extend(tier.after_publish)
        after_tag.extend(tier.after_tag)

    return HooksConfig(
        before_prepare=before_prepare,
        before_publish=before_publish,
        after_publish=after_publish,
        after_tag=after_tag,
    )


def expand_template(
    command: str,
    variables: dict[str, str],
) -> str:
    """Expand ``${variable}`` placeholders in a hook command.

    Args:
        command: Shell command string with ``${version}``, ``${name}``,
            ``${tag}`` placeholders.
        variables: Mapping of variable names to values.

    Returns:
        Command with placeholders replaced.
    """
    result = command
    for key, value in variables.items():
        result = result.replace(f'${{{key}}}', value)
    return result


async def run_hooks(
    hooks: HooksConfig,
    event: str,
    *,
    variables: dict[str, str] | None = None,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> list[CommandResult]:
    """Execute hooks for a specific lifecycle event.

    Args:
        hooks: Merged hooks configuration.
        event: Hook event name (``"before_prepare"``,
            ``"before_publish"``, ``"after_publish"``, ``"after_tag"``).
        variables: Template variables for ``${version}``, ``${name}``,
            ``${tag}`` expansion.
        cwd: Working directory for hook commands.
        dry_run: If ``True``, log commands without executing.

    Returns:
        List of :class:`CommandResult` for each hook command.

    Raises:
        ValueError: If ``event`` is not a recognized hook event.
    """
    commands = getattr(hooks, event, None)
    if commands is None:
        msg = f"Unknown hook event: '{event}'"
        raise ValueError(msg)

    if not commands:
        return []

    vars_ = variables or {}
    results: list[CommandResult] = []

    for raw_cmd in commands:
        expanded = expand_template(raw_cmd, vars_)
        log.info('hook', hook_event=event, command=expanded, dry_run=dry_run)

        # Parse the command string into a list for subprocess.
        cmd_parts = shlex.split(expanded)
        result = await asyncio.to_thread(
            run_command,
            cmd_parts,
            cwd=cwd,
            dry_run=dry_run,
        )
        results.append(result)

        if not result.ok:
            log.error(
                'hook_failed',
                hook_event=event,
                command=expanded,
                return_code=result.return_code,
                stderr=result.stderr[:500],
            )
            break  # Stop on first failure.

    return results


def _has_hooks(hooks: HooksConfig) -> bool:
    """Return True if any hook event has commands."""
    return bool(hooks.before_prepare or hooks.before_publish or hooks.after_publish or hooks.after_tag)


__all__ = [
    'expand_template',
    'merge_hooks',
    'run_hooks',
]
