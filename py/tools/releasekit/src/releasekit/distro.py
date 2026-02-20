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

"""Distro packaging dependency synchronisation.

Reads ``[project].dependencies`` from ``pyproject.toml`` and keeps
Debian/Ubuntu ``control``, Fedora/RHEL ``.spec``, and Homebrew
formula (``.rb``) files in sync.

Naming conventions:

- **Debian/Ubuntu**: ``python3-{name}`` with ``(>= X.Y.Z)`` version
  constraints.  PyPI names are normalised: underscores and dots become
  dashes, everything is lowercased.
- **Fedora/RHEL**: ``python3dist({name})`` with ``>= X.Y`` version
  constraints.  Names are kept lowercase; Fedora's ``python3dist()``
  macro handles further normalisation.
- **Homebrew**: ``resource "{name}" do`` blocks with PyPI sdist URLs.
  Names are lowercased with underscores replaced by hyphens.

The module exposes:

- :func:`parse_pyproject_deps` — extract deps from ``pyproject.toml``.
- :func:`expected_debian_deps` — compute expected Debian/Ubuntu ``Depends:`` lines.
- :func:`expected_fedora_requires` — compute expected Fedora ``Requires:`` lines.
- :func:`expected_brew_resources` — compute expected Homebrew resource names.
- :func:`check_distro_deps` — compare expected vs actual, return mismatches.
- :func:`fix_debian_control` — rewrite the ``Depends:`` block in ``control``.
- :func:`fix_fedora_spec` — rewrite the ``Requires:`` block in ``.spec``.
- :func:`fix_brew_formula` — rewrite the ``resource`` blocks in a Homebrew formula.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import tomlkit

from releasekit.logging import get_logger

logger = get_logger(__name__)

# Regex to split a PEP 508 dependency into name and version specifier.
# Examples: "aiofiles>=24.1.0" → ("aiofiles", ">=24.1.0")
#           "rich[all]>=13.0.0" → ("rich", ">=13.0.0")
_DEP_SPLIT_RE = re.compile(
    r'^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)'  # name
    r'(\[[^\]]*\])?'  # optional extras
    r'\s*(.*)',  # version specifier
)

# Extract the minimum version from a specifier like ">=24.1.0" or ">=24.1.0,<25".
_MIN_VERSION_RE = re.compile(r'>=\s*([0-9][0-9a-zA-Z._]*)')


@dataclass(frozen=True)
class Dep:
    """A parsed Python dependency."""

    name: str
    min_version: str  # e.g. "24.1.0", empty if unconstrained


def parse_pyproject_deps(pyproject_path: Path) -> list[Dep]:
    """Parse ``[project].dependencies`` from a ``pyproject.toml``.

    Args:
        pyproject_path: Path to the ``pyproject.toml`` file.

    Returns:
        Sorted list of :class:`Dep` objects.
    """
    text = pyproject_path.read_text(encoding='utf-8')
    doc = tomlkit.parse(text)
    project = doc.get('project')
    if not isinstance(project, dict):
        return []
    raw_deps = project.get('dependencies')
    if not isinstance(raw_deps, list):
        return []

    deps: list[Dep] = []
    for raw in raw_deps:
        if not isinstance(raw, str):
            continue
        m = _DEP_SPLIT_RE.match(raw.strip())
        if not m:
            continue
        name = m.group(1)
        specifier = m.group(4) or ''
        vm = _MIN_VERSION_RE.search(specifier)
        min_ver = vm.group(1) if vm else ''
        deps.append(Dep(name=name, min_version=min_ver))

    deps.sort(key=lambda d: d.name.lower())
    return deps


def _debian_pkg_name(pypi_name: str) -> str:
    """Convert a PyPI package name to a Debian package name.

    ``aiofiles`` → ``python3-aiofiles``
    ``rich-argparse`` → ``python3-rich-argparse``
    ``rich_argparse`` → ``python3-rich-argparse``
    """
    normalised = pypi_name.lower().replace('_', '-').replace('.', '-')
    return f'python3-{normalised}'


def expected_debian_deps(deps: list[Dep]) -> list[str]:
    """Generate expected Debian/Ubuntu ``Depends:`` lines.

    Each line is formatted as ``python3-{name} (>= X.Y.Z)`` or
    ``python3-{name}`` if unconstrained.  Lines are prefixed with
    a single space for Debian ``control`` formatting.

    Args:
        deps: Parsed dependencies from :func:`parse_pyproject_deps`.

    Returns:
        List of dependency strings (without trailing comma).
    """
    lines: list[str] = []
    for dep in deps:
        pkg = _debian_pkg_name(dep.name)
        if dep.min_version:
            lines.append(f'{pkg} (>= {dep.min_version})')
        else:
            lines.append(pkg)
    return lines


def _parse_debian_runtime_deps(control_text: str) -> list[str]:
    """Extract runtime ``Depends:`` entries from a Debian ``control`` file.

    Returns only ``python3-*`` entries (skips ``${python3:Depends}``,
    ``${misc:Depends}``, etc.).
    """
    deps: list[str] = []
    in_binary = False
    in_depends = False

    for line in control_text.splitlines():
        # Detect binary package stanza.
        if line.startswith('Package:'):
            in_binary = True
            in_depends = False
            continue

        if not in_binary:
            continue

        # Start of Depends: field.
        if line.startswith('Depends:'):
            in_depends = True
            # Deps may start on the same line after "Depends:".
            rest = line[len('Depends:') :].strip()
            if rest:
                for part in rest.split(','):
                    part = part.strip()
                    if part.startswith('python3-'):
                        deps.append(part)
            continue

        # Continuation lines (start with space/tab).
        if in_depends and line and line[0] in (' ', '\t'):
            for part in line.split(','):
                part = part.strip()
                if part.startswith('python3-'):
                    # Strip trailing comma if present.
                    deps.append(part.rstrip(','))
            continue

        # Any non-continuation line ends the Depends block.
        if in_depends and line and line[0] not in (' ', '\t'):
            in_depends = False

    return sorted(deps)


def fix_debian_control(
    control_path: Path,
    deps: list[Dep],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Rewrite the ``Depends:`` block in a Debian/Ubuntu ``control`` file.

    Preserves the ``${python3:Depends}`` and ``${misc:Depends}``
    substitution variables and replaces only the ``python3-*`` entries.

    Args:
        control_path: Path to ``debian/control``.
        deps: Dependencies from :func:`parse_pyproject_deps`.
        dry_run: If ``True``, report changes without writing.

    Returns:
        List of human-readable change descriptions.
    """
    text = control_path.read_text(encoding='utf-8')
    expected = expected_debian_deps(deps)

    actual = _parse_debian_runtime_deps(text)
    if sorted(actual) == sorted(expected):
        return []

    # Rebuild the Depends: block.
    new_lines: list[str] = []
    in_binary = False
    in_depends = False

    for line in text.splitlines():
        if line.startswith('Package:'):
            in_binary = True
            in_depends = False
            new_lines.append(line)
            continue

        if not in_binary:
            new_lines.append(line)
            continue

        if line.startswith('Depends:'):
            in_depends = True
            new_lines.append('Depends:')
            # Write substitution variables first.
            new_lines.append(' ${python3:Depends},')
            new_lines.append(' ${misc:Depends},')
            # Write python3-* deps.
            for i, dep_str in enumerate(expected):
                suffix = ',' if i < len(expected) - 1 else ''
                new_lines.append(f' {dep_str}{suffix}')
            continue

        # Skip old continuation lines of Depends:.
        if in_depends and line and line[0] in (' ', '\t'):
            continue

        # End of Depends block.
        if in_depends:
            in_depends = False

        new_lines.append(line)

    new_text = '\n'.join(new_lines) + '\n'
    changes = [f'debian/control: updated Depends ({len(expected)} python3-* deps)']

    if not dry_run:
        control_path.write_text(new_text, encoding='utf-8')
        logger.info('fix_debian_control', path=str(control_path), deps=len(expected))

    return changes


def _strip_trailing_zeros(version: str) -> str:
    """Strip trailing ``.0`` segments from a version string.

    Fedora convention uses minimal version numbers:
    ``24.1.0`` → ``24.1``, ``3.0.0`` → ``3``, ``0.27.0`` → ``0.27``.
    """
    parts = version.split('.')
    while len(parts) > 1 and parts[-1] == '0':
        parts.pop()
    return '.'.join(parts)


def _fedora_dep_name(pypi_name: str) -> str:
    """Convert a PyPI package name to a Fedora ``python3dist()`` name.

    ``aiofiles`` → ``python3dist(aiofiles)``
    ``rich-argparse`` → ``python3dist(rich-argparse)``
    """
    return f'python3dist({pypi_name.lower()})'


def expected_fedora_requires(deps: list[Dep]) -> list[str]:
    """Generate expected Fedora ``Requires:`` lines.

    Each line is formatted as
    ``Requires:       python3dist({name}) >= X.Y`` or
    ``Requires:       python3dist({name})`` if unconstrained.

    Args:
        deps: Parsed dependencies from :func:`parse_pyproject_deps`.

    Returns:
        List of full ``Requires:`` lines.
    """
    lines: list[str] = []
    for dep in deps:
        pkg = _fedora_dep_name(dep.name)
        if dep.min_version:
            ver = _strip_trailing_zeros(dep.min_version)
            lines.append(f'Requires:       {pkg} >= {ver}')
        else:
            lines.append(f'Requires:       {pkg}')
    return lines


def _parse_fedora_requires(spec_text: str) -> list[str]:
    """Extract ``Requires: python3dist(...)`` lines from a spec file.

    Returns the full lines (normalised) for comparison.
    """
    requires: list[str] = []
    for line in spec_text.splitlines():
        stripped = line.strip()
        if stripped.startswith('Requires:') and 'python3dist(' in stripped:
            # Normalise whitespace.
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                requires.append(f'Requires:       {parts[1]}')
            else:
                requires.append(stripped)
    return sorted(requires)


def fix_fedora_spec(
    spec_path: Path,
    deps: list[Dep],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Rewrite the ``Requires:`` lines in a Fedora ``.spec`` file.

    Only touches ``Requires: python3dist(...)`` lines in the
    ``%package -n python3-*`` section.

    Args:
        spec_path: Path to the ``.spec`` file.
        deps: Dependencies from :func:`parse_pyproject_deps`.
        dry_run: If ``True``, report changes without writing.

    Returns:
        List of human-readable change descriptions.
    """
    text = spec_path.read_text(encoding='utf-8')
    expected = expected_fedora_requires(deps)

    actual = _parse_fedora_requires(text)
    if sorted(actual) == sorted(expected):
        return []

    # Rebuild: remove old Requires: python3dist(...) lines in the
    # %package section, then insert the new ones.
    new_lines: list[str] = []
    in_pkg_section = False
    requires_inserted = False

    for line in text.splitlines():
        stripped = line.strip()

        # Detect %package -n python3-* section.
        if stripped.startswith('%package') and 'python3-' in stripped:
            in_pkg_section = True
            requires_inserted = False
            new_lines.append(line)
            continue

        # Detect next section (any line starting with %).
        if in_pkg_section and stripped.startswith('%') and not stripped.startswith('%package'):
            # If we haven't inserted requires yet, do it before the section ends.
            if not requires_inserted:
                for req in expected:
                    new_lines.append(req)
                new_lines.append('')
                requires_inserted = True
            in_pkg_section = False
            new_lines.append(line)
            continue

        # Skip old Requires: python3dist(...) lines.
        if in_pkg_section and stripped.startswith('Requires:') and 'python3dist(' in stripped:
            continue

        # Insert new requires after Summary: line in %package section.
        if in_pkg_section and stripped.startswith('Summary:') and not requires_inserted:
            new_lines.append(line)
            for req in expected:
                new_lines.append(req)
            requires_inserted = True
            continue

        # Skip blank lines between old Requires and next section
        # (we'll add our own spacing).
        if in_pkg_section and requires_inserted and stripped == '':
            # Keep one blank line after our requires block.
            if new_lines and new_lines[-1] != '':
                new_lines.append('')
            continue

        new_lines.append(line)

    new_text = '\n'.join(new_lines) + '\n'
    changes = [f'{spec_path.name}: updated Requires ({len(expected)} python3dist deps)']

    if not dry_run:
        spec_path.write_text(new_text, encoding='utf-8')
        logger.info('fix_fedora_spec', path=str(spec_path), deps=len(expected))

    return changes


def _brew_resource_name(pypi_name: str) -> str:
    """Convert a PyPI package name to a Homebrew resource name.

    Homebrew resources use the PyPI name lowercased with underscores
    replaced by hyphens (matching the sdist convention).

    ``aiofiles`` → ``aiofiles``
    ``rich_argparse`` → ``rich-argparse``
    """
    return pypi_name.lower().replace('_', '-')


def expected_brew_resources(deps: list[Dep]) -> list[str]:
    """Generate expected Homebrew ``resource`` block names.

    Returns a sorted list of normalised resource names that should
    appear as ``resource "<name>" do`` blocks in the formula.

    Args:
        deps: Parsed dependencies from :func:`parse_pyproject_deps`.

    Returns:
        Sorted list of resource name strings.
    """
    return sorted(_brew_resource_name(dep.name) for dep in deps)


_BREW_RESOURCE_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+do\s*$')


def _parse_brew_resources(formula_text: str) -> list[str]:
    """Extract ``resource "..." do`` names from a Homebrew formula.

    Returns sorted list of resource names found in the formula.
    """
    resources: list[str] = []
    for line in formula_text.splitlines():
        m = _BREW_RESOURCE_RE.match(line)
        if m:
            resources.append(m.group(1))
    return sorted(resources)


def check_brew_deps(
    formula_path: Path,
    deps: list[Dep],
) -> DistroDepDiff:
    """Compare Homebrew formula resources against ``pyproject.toml``.

    Args:
        formula_path: Path to the ``.rb`` formula file.
        deps: Expected deps from :func:`parse_pyproject_deps`.

    Returns:
        A :class:`DistroDepDiff` with any mismatches.
    """
    text = formula_path.read_text(encoding='utf-8')
    actual = set(_parse_brew_resources(text))
    expected = set(expected_brew_resources(deps))

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    return DistroDepDiff(
        distro='homebrew',
        missing=missing,
        extra=extra,
        version_mismatch=[],
    )


def fix_brew_formula(
    formula_path: Path,
    deps: list[Dep],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Rewrite the ``resource`` blocks in a Homebrew formula.

    Removes existing ``resource ... do / url ... / sha256 ... / end``
    blocks and inserts new ones (with ``PLACEHOLDER`` sha256) for
    each dependency in ``deps``.

    Args:
        formula_path: Path to the ``.rb`` formula file.
        deps: Dependencies from :func:`parse_pyproject_deps`.
        dry_run: If ``True``, report changes without writing.

    Returns:
        List of human-readable change descriptions.
    """
    text = formula_path.read_text(encoding='utf-8')
    expected_names = set(expected_brew_resources(deps))
    actual_names = set(_parse_brew_resources(text))

    if actual_names == expected_names:
        return []

    # Strip existing resource blocks.
    new_lines: list[str] = []
    skip_until_end = False
    for line in text.splitlines():
        if _BREW_RESOURCE_RE.match(line):
            skip_until_end = True
            continue
        if skip_until_end:
            if line.strip() == 'end':
                skip_until_end = False
            continue
        new_lines.append(line)

    # Find insertion point: after the last ``depends_on`` line, or
    # after the ``license`` line, or before ``def install``.
    insert_idx: int | None = None
    for i, line in enumerate(new_lines):
        stripped = line.strip()
        if stripped.startswith('depends_on '):
            insert_idx = i + 1
        elif insert_idx is None and stripped.startswith('license '):
            insert_idx = i + 1
    if insert_idx is None:
        for i, line in enumerate(new_lines):
            if line.strip().startswith('def install'):
                insert_idx = i
                break
    if insert_idx is None:
        insert_idx = len(new_lines)

    # Build new resource blocks.
    resource_blocks: list[str] = []
    for dep in sorted(deps, key=lambda d: _brew_resource_name(d.name)):
        name = _brew_resource_name(dep.name)
        resource_blocks.append('')
        resource_blocks.append(f'  resource "{name}" do')
        ver = dep.min_version or '0.0.0'
        sdist_url = f'https://files.pythonhosted.org/packages/source/{name[0]}/{name}/{name}-{ver}.tar.gz'
        resource_blocks.append(f'    url "{sdist_url}"')
        resource_blocks.append('    sha256 "PLACEHOLDER"')
        resource_blocks.append('  end')

    new_lines[insert_idx:insert_idx] = resource_blocks

    new_text = '\n'.join(new_lines) + '\n'
    changes = [f'{formula_path.name}: updated resources ({len(deps)} deps)']

    if not dry_run:
        formula_path.write_text(new_text, encoding='utf-8')
        logger.info('fix_brew_formula', path=str(formula_path), deps=len(deps))

    return changes


@dataclass(frozen=True)
class DistroDepDiff:
    """Result of comparing expected vs actual distro deps."""

    distro: str  # "debian", "fedora", or "homebrew"
    missing: list[str]  # deps in pyproject.toml but not in distro file
    extra: list[str]  # deps in distro file but not in pyproject.toml
    version_mismatch: list[str]  # deps with different version constraints

    @property
    def ok(self) -> bool:
        """True if no differences found."""
        return not self.missing and not self.extra and not self.version_mismatch


def check_debian_deps(
    control_path: Path,
    deps: list[Dep],
) -> DistroDepDiff:
    """Compare Debian/Ubuntu ``control`` deps against ``pyproject.toml``.

    Args:
        control_path: Path to ``debian/control``.
        deps: Expected deps from :func:`parse_pyproject_deps`.

    Returns:
        A :class:`DistroDepDiff` with any mismatches.
    """
    text = control_path.read_text(encoding='utf-8')
    actual_lines = _parse_debian_runtime_deps(text)
    expected_lines = expected_debian_deps(deps)

    actual_set = {line.strip() for line in actual_lines}
    expected_set = {line.strip() for line in expected_lines}

    # Build name → full-line maps for version comparison.
    def _name(line: str) -> str:
        return line.split('(')[0].strip().split()[0] if '(' in line else line.strip()

    actual_by_name = {_name(entry): entry for entry in actual_set}
    expected_by_name = {_name(entry): entry for entry in expected_set}

    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)

    # Separate version mismatches from true missing/extra.
    version_mismatch: list[str] = []
    real_missing: list[str] = []
    real_extra: list[str] = []

    for line in missing:
        name = _name(line)
        if name in actual_by_name:
            version_mismatch.append(f'{name}: expected {line}, got {actual_by_name[name]}')
        else:
            real_missing.append(line)

    for line in extra:
        name = _name(line)
        if name not in expected_by_name:
            real_extra.append(line)

    return DistroDepDiff(
        distro='debian',
        missing=real_missing,
        extra=real_extra,
        version_mismatch=version_mismatch,
    )


def check_fedora_deps(
    spec_path: Path,
    deps: list[Dep],
) -> DistroDepDiff:
    """Compare Fedora ``.spec`` Requires against ``pyproject.toml``.

    Args:
        spec_path: Path to the ``.spec`` file.
        deps: Expected deps from :func:`parse_pyproject_deps`.

    Returns:
        A :class:`DistroDepDiff` with any mismatches.
    """
    text = spec_path.read_text(encoding='utf-8')
    actual_lines = _parse_fedora_requires(text)
    expected_lines = expected_fedora_requires(deps)

    actual_set = {line.strip() for line in actual_lines}
    expected_set = {line.strip() for line in expected_lines}

    def _name(line: str) -> str:
        m = re.search(r'python3dist\(([^)]+)\)', line)
        return m.group(1) if m else line

    actual_by_name = {_name(entry): entry for entry in actual_set}
    expected_by_name = {_name(entry): entry for entry in expected_set}

    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)

    version_mismatch: list[str] = []
    real_missing: list[str] = []
    real_extra: list[str] = []

    for line in missing:
        name = _name(line)
        if name in actual_by_name:
            version_mismatch.append(f'{name}: expected {line}, got {actual_by_name[name]}')
        else:
            real_missing.append(line)

    for line in extra:
        name = _name(line)
        if name not in expected_by_name:
            real_extra.append(line)

    return DistroDepDiff(
        distro='fedora',
        missing=real_missing,
        extra=real_extra,
        version_mismatch=version_mismatch,
    )


def check_distro_deps(
    packaging_dir: Path,
    pyproject_path: Path,
) -> list[DistroDepDiff]:
    """Check all distro packaging files against ``pyproject.toml``.

    Looks for ``packaging/debian/control``,
    ``packaging/fedora/*.spec``, and ``packaging/homebrew/*.rb``
    relative to the package root.

    Args:
        packaging_dir: Path to the ``packaging/`` directory.
        pyproject_path: Path to the ``pyproject.toml`` file.

    Returns:
        List of :class:`DistroDepDiff` results (one per distro found).
    """
    deps = parse_pyproject_deps(pyproject_path)
    if not deps:
        return []

    results: list[DistroDepDiff] = []

    # Debian/Ubuntu.
    control = packaging_dir / 'debian' / 'control'
    if control.is_file():
        results.append(check_debian_deps(control, deps))

    # Fedora/RHEL.
    spec_files = list((packaging_dir / 'fedora').glob('*.spec')) if (packaging_dir / 'fedora').is_dir() else []
    for spec in spec_files:
        results.append(check_fedora_deps(spec, deps))

    # Homebrew.
    brew_files = list((packaging_dir / 'homebrew').glob('*.rb')) if (packaging_dir / 'homebrew').is_dir() else []
    for formula in brew_files:
        results.append(check_brew_deps(formula, deps))

    return results


def fix_distro_deps(
    packaging_dir: Path,
    pyproject_path: Path,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Fix all distro packaging files to match ``pyproject.toml``.

    Args:
        packaging_dir: Path to the ``packaging/`` directory.
        pyproject_path: Path to the ``pyproject.toml`` file.
        dry_run: If ``True``, report changes without writing.

    Returns:
        List of human-readable change descriptions.
    """
    deps = parse_pyproject_deps(pyproject_path)
    if not deps:
        return []

    changes: list[str] = []

    # Debian/Ubuntu.
    control = packaging_dir / 'debian' / 'control'
    if control.is_file():
        changes.extend(fix_debian_control(control, deps, dry_run=dry_run))

    # Fedora/RHEL.
    spec_files = list((packaging_dir / 'fedora').glob('*.spec')) if (packaging_dir / 'fedora').is_dir() else []
    for spec in spec_files:
        changes.extend(fix_fedora_spec(spec, deps, dry_run=dry_run))

    # Homebrew.
    brew_files = list((packaging_dir / 'homebrew').glob('*.rb')) if (packaging_dir / 'homebrew').is_dir() else []
    for formula in brew_files:
        changes.extend(fix_brew_formula(formula, deps, dry_run=dry_run))

    return changes


__all__ = [
    'Dep',
    'DistroDepDiff',
    'check_brew_deps',
    'check_debian_deps',
    'check_distro_deps',
    'check_fedora_deps',
    'expected_brew_resources',
    'expected_debian_deps',
    'expected_fedora_requires',
    'fix_brew_formula',
    'fix_debian_control',
    'fix_distro_deps',
    'fix_fedora_spec',
    'parse_pyproject_deps',
]
