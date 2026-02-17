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

"""Interactive license fixer for ``releasekit licenses --fix``.

Walks the license tree, prompts the user for each problematic dependency,
and writes the chosen resolution back to ``releasekit.toml`` using
comment-preserving ``tomlkit`` edits.

Supported actions per dependency:

- **exempt** — add to ``[license].exempt_packages``
- **allow** — add the SPDX ID to ``[license].allow_licenses``
- **deny** — add the SPDX ID to ``[license].deny_licenses``
- **override** — set a manual SPDX expression in ``[license.overrides]``
- **skip** — leave unchanged

Example session::

    $ releasekit licenses --fix

    ✗ myapp → gpl-lib (GPL-3.0-only) — incompatible with Apache-2.0

    How should releasekit handle gpl-lib?
      [1] exempt   — skip license checks for this package
      [2] allow    — allow GPL-3.0-only globally
      [3] deny     — block GPL-3.0-only globally
      [4] override — set a different SPDX expression for gpl-lib
      [5] skip     — do nothing (leave as-is)
    Choice [1-5]: 1

    ✓ Added gpl-lib to exempt_packages in releasekit.toml
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.items

from releasekit.checks._license_tree import DepNode, DepStatus, LicenseTree

# ── Data types ───────────────────────────────────────────────────────


class FixAction:
    """Constants for the user-chosen fix action."""

    EXEMPT = 'exempt'
    ALLOW = 'allow'
    DENY = 'deny'
    OVERRIDE = 'override'
    SKIP = 'skip'


@dataclass
class LicenseFixChoice:
    """A single user decision for a problematic dependency.

    Attributes:
        dep_name: The dependency package name.
        dep_license: The resolved (or raw) SPDX ID.
        parent_package: The parent package that depends on this dep.
        action: One of :class:`FixAction` constants.
        override_value: When action is ``override``, the SPDX expression.
    """

    dep_name: str
    dep_license: str
    parent_package: str
    action: str = FixAction.SKIP
    override_value: str = ''


@dataclass
class LicenseFixReport:
    """Summary of all fixes applied.

    Attributes:
        choices: All user decisions (including skips).
        written: Whether ``releasekit.toml`` was modified.
        config_path: Path to the config file that was (or would be) written.
    """

    choices: list[LicenseFixChoice] = field(default_factory=list)
    written: bool = False
    config_path: Path | None = None


# ── ANSI helpers ─────────────────────────────────────────────────────

_RESET = '\033[0m'
_BOLD = '\033[1m'
_DIM = '\033[2m'
_RED = '\033[31m'
_GREEN = '\033[32m'
_YELLOW = '\033[33m'
_CYAN = '\033[36m'
_BOLD_RED = '\033[1;31m'
_BOLD_GREEN = '\033[1;32m'
_BOLD_CYAN = '\033[1;36m'


def _c(text: str, code: str, *, color: bool) -> str:
    """Wrap *text* in ANSI *code* if *color* is True."""
    if not color:
        return text
    return f'{code}{text}{_RESET}'


# ── Actionable statuses ──────────────────────────────────────────────

_FIXABLE_STATUSES = frozenset({
    DepStatus.INCOMPATIBLE,
    DepStatus.DENIED,
    DepStatus.NO_LICENSE,
    DepStatus.UNRESOLVED,
})


def collect_fixable_deps(tree: LicenseTree) -> list[tuple[str, DepNode]]:
    """Extract all (parent_package, dep_node) pairs that need fixing.

    Returns:
        List of ``(parent_package_name, dep_node)`` tuples for deps
        whose status is in :data:`_FIXABLE_STATUSES`.
    """
    results: list[tuple[str, DepNode]] = []
    seen: set[str] = set()
    for pkg in tree.packages:
        for dep in pkg.deps:
            if dep.status in _FIXABLE_STATUSES and dep.name not in seen:
                results.append((pkg.name, dep))
                seen.add(dep.name)
    return results


# ── Interactive prompting ────────────────────────────────────────────

_MENU = """\
How should releasekit handle {dep_name}?
  [1] exempt   — skip license checks for this package
  [2] allow    — allow {license} globally
  [3] deny     — block {license} globally
  [4] override — set a different SPDX expression for {dep_name}
  [5] skip     — do nothing (leave as-is)\
"""

_ACTION_MAP: dict[str, str] = {
    '1': FixAction.EXEMPT,
    '2': FixAction.ALLOW,
    '3': FixAction.DENY,
    '4': FixAction.OVERRIDE,
    '5': FixAction.SKIP,
}


def _prompt_status_line(
    parent: str,
    dep: DepNode,
    project_license: str,
    *,
    color: bool,
) -> str:
    """Format the status line shown before the menu."""
    symbol = '\u2717' if dep.status == DepStatus.INCOMPATIBLE else '\u2718' if dep.status == DepStatus.DENIED else '?'
    lic = dep.license or '(unknown)'
    reason = dep.detail or f'{dep.status.value} with {project_license}'
    line = f'{symbol} {parent} \u2192 {dep.name} ({lic}) \u2014 {reason}'
    if dep.status in (DepStatus.INCOMPATIBLE, DepStatus.DENIED):
        return _c(line, _BOLD_RED, color=color)
    return _c(line, _YELLOW, color=color)


def prompt_for_fix(
    parent: str,
    dep: DepNode,
    project_license: str,
    *,
    color: bool = False,
    input_fn: Callable[..., str] | None = None,
    print_fn: Callable[..., Any] | None = None,
) -> LicenseFixChoice:
    """Interactively prompt the user for a fix action.

    Args:
        parent: Parent package name.
        dep: The problematic dependency node.
        project_license: The project's SPDX license ID.
        color: Whether to use ANSI colors.
        input_fn: Override for ``input()`` (for testing).
        print_fn: Override for ``print()`` (for testing).

    Returns:
        A :class:`LicenseFixChoice` with the user's decision.
    """
    _input = input_fn or input
    _print = print_fn or print

    _print('')
    _print(_prompt_status_line(parent, dep, project_license, color=color))

    # Show detection source and registry URL as Rust-style notes.
    if dep.source:
        note = _c('note', _BOLD_CYAN, color=color)
        src = _c(dep.source, _DIM, color=color)
        _print(f'  {note}: detected via {src}')
    if dep.registry_url:
        note = _c('note', _BOLD_CYAN, color=color)
        url = _c(dep.registry_url, _CYAN, color=color)
        _print(f'  {note}: {url}')

    _print('')

    lic = dep.license or '(unknown)'
    _print(_MENU.format(dep_name=dep.name, license=lic))

    while True:
        try:
            raw = _input('Choice [1-5]: ')
        except EOFError:
            _print('')
            _print('  Input stream ended, skipping remaining fixes.')
            return LicenseFixChoice(
                dep_name=dep.name,
                dep_license=lic,
                parent_package=parent,
                action=FixAction.SKIP,
            )

        raw = raw.strip()
        if raw in _ACTION_MAP:
            action = _ACTION_MAP[raw]
            break
        _print(f'  Invalid choice: {raw!r}. Enter 1-5.')

    override_value = ''
    if action == FixAction.OVERRIDE:
        while True:
            try:
                override_value = _input(f'SPDX expression for {dep.name}: ').strip()
            except EOFError:
                _print('')
                _print('  Input stream ended, skipping override.')
                action = FixAction.SKIP
                break
            if override_value:
                break
            _print('  Expression cannot be empty.')

    return LicenseFixChoice(
        dep_name=dep.name,
        dep_license=lic,
        parent_package=parent,
        action=action,
        override_value=override_value,
    )


# ── TOML writer ──────────────────────────────────────────────────────


def _ensure_license_section(doc: tomlkit.TOMLDocument) -> tomlkit.items.Table:
    """Ensure ``[license]`` section exists in the TOML document.

    Returns:
        The ``[license]`` table (created if absent).
    """
    if 'license' not in doc:
        doc.add(tomlkit.nl())
        doc.add('license', tomlkit.table())
    return doc['license']  # type: ignore[return-value]  # tomlkit


def _ensure_list(table: tomlkit.items.Table, key: str) -> tomlkit.items.Array:
    """Ensure *key* exists as a list in *table*.

    Returns:
        The list (created if absent).
    """
    if key not in table:
        table.add(key, tomlkit.array())
    return table[key]  # type: ignore[return-value]  # tomlkit


def _ensure_inline_table(table: tomlkit.items.Table, key: str) -> tomlkit.items.Table:
    """Ensure *key* exists as a table in *table*.

    Returns:
        The sub-table (created if absent).
    """
    if key not in table:
        table.add(key, tomlkit.table())
    return table[key]  # type: ignore[return-value]  # tomlkit


def apply_fixes(
    config_path: Path,
    choices: list[LicenseFixChoice],
    *,
    dry_run: bool = False,
) -> LicenseFixReport:
    """Apply user-chosen fixes to ``releasekit.toml``.

    Uses ``tomlkit`` for comment-preserving edits.

    Args:
        config_path: Path to ``releasekit.toml``.
        choices: List of user decisions from :func:`prompt_for_fix`.
        dry_run: If ``True``, compute changes but don't write.

    Returns:
        A :class:`LicenseFixReport` summarizing what was done.
    """
    report = LicenseFixReport(choices=choices, config_path=config_path)

    actionable = [c for c in choices if c.action != FixAction.SKIP]
    if not actionable:
        return report

    text = config_path.read_text(encoding='utf-8')
    doc = tomlkit.parse(text)
    lic = _ensure_license_section(doc)

    for choice in actionable:
        if choice.action == FixAction.EXEMPT:
            arr = _ensure_list(lic, 'exempt_packages')
            if choice.dep_name not in arr:
                arr.append(choice.dep_name)

        elif choice.action == FixAction.ALLOW:
            arr = _ensure_list(lic, 'allow_licenses')
            if choice.dep_license not in arr:
                arr.append(choice.dep_license)

        elif choice.action == FixAction.DENY:
            arr = _ensure_list(lic, 'deny_licenses')
            if choice.dep_license not in arr:
                arr.append(choice.dep_license)

        elif choice.action == FixAction.OVERRIDE:
            overrides = _ensure_inline_table(lic, 'overrides')
            overrides[choice.dep_name] = choice.override_value

    if not dry_run:
        config_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
        report.written = True

    return report


# ── Orchestrator ─────────────────────────────────────────────────────


def interactive_license_fix(
    tree: LicenseTree,
    config_path: Path,
    *,
    color: bool = False,
    dry_run: bool = False,
    input_fn: Callable[..., str] | None = None,
    print_fn: Callable[..., Any] | None = None,
) -> LicenseFixReport:
    """Run the full interactive license fix flow.

    1. Collect all fixable deps from the tree.
    2. Prompt the user for each one.
    3. Apply the chosen fixes to ``releasekit.toml``.

    Args:
        tree: The license tree from the compatibility check.
        config_path: Path to ``releasekit.toml``.
        color: Whether to use ANSI colors.
        dry_run: If ``True``, don't write changes.
        input_fn: Override for ``input()`` (for testing).
        print_fn: Override for ``print()`` (for testing).

    Returns:
        A :class:`LicenseFixReport` summarizing all decisions.
    """
    _print = print_fn or print

    fixable = collect_fixable_deps(tree)
    if not fixable:
        _print(_c('No license issues to fix.', _BOLD_GREEN, color=color))
        return LicenseFixReport(config_path=config_path)

    _print(
        _c(
            f'Found {len(fixable)} license issue(s) to resolve.',
            _BOLD_CYAN,
            color=color,
        )
    )

    choices: list[LicenseFixChoice] = []
    try:
        for parent, dep in fixable:
            choice = prompt_for_fix(
                parent,
                dep,
                tree.project_license,
                color=color,
                input_fn=input_fn,
                print_fn=print_fn,
            )
            choices.append(choice)
    except KeyboardInterrupt:
        _print('')
        _print(_c('Aborted.', _BOLD_RED, color=color))

    report = apply_fixes(config_path, choices, dry_run=dry_run)

    # Summary.
    applied = [c for c in choices if c.action != FixAction.SKIP]
    skipped = len(choices) - len(applied)

    if applied:
        if dry_run:
            _print(
                _c(
                    f'\n(dry-run) Would apply {len(applied)} fix(es) to {config_path.name}.',
                    _YELLOW,
                    color=color,
                )
            )
        else:
            _print(
                _c(
                    f'\n\u2713 Applied {len(applied)} fix(es) to {config_path.name}.',
                    _BOLD_GREEN,
                    color=color,
                )
            )
            for c in applied:
                _print(f'  {c.action}: {c.dep_name}' + (f' = {c.override_value}' if c.override_value else ''))

    if skipped:
        _print(_c(f'  {skipped} issue(s) skipped.', _DIM, color=color))

    return report
