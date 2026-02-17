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

r"""License compatibility graph — loads TOML data and answers queries.

The graph is a directed adjacency-set structure where each node is a
canonical SPDX license identifier and an edge ``A → B`` means "code
licensed under A **can** depend on code licensed under B".

Key Concepts (ELI5)::

    ┌─────────────────────┬──────────────────────────────────────────────┐
    │ Concept              │ Plain-English                                │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ Node                 │ A canonical SPDX license identifier.        │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ Edge A → B           │ Code under A can depend on code under B.    │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ Category             │ permissive, weak-copyleft, strong-copyleft, │
    │                      │ network-copyleft, source-available,         │
    │                      │ proprietary.                                │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ or_later (+)         │ "This version or any later version."        │
    │                      │ Expands the set of compatible licenses.     │
    └─────────────────────┴──────────────────────────────────────────────┘

Usage::

    from releasekit.checks._license_graph import LicenseGraph

    graph = LicenseGraph.load()  # built-in data
    graph = LicenseGraph.load(user_toml=Path(...))  # + user overrides

    graph.is_compatible('Apache-2.0', LicenseId('MIT'))  # True
    graph.is_compatible('GPL-2.0-only', LicenseId('Apache-2.0'))  # False
    graph.is_compatible('GPL-2.0-only', LicenseId('GPL-2.0', or_later=True))  # True

    graph.category('MIT')  # "permissive"
    graph.known('MIT')  # True
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from releasekit.spdx_expr import LicenseId, LicenseRef

__all__ = [
    'LicenseDataError',
    'LicenseGraph',
    'LicenseInfo',
]

_VALID_CATEGORIES = frozenset({
    'permissive',
    'weak-copyleft',
    'strong-copyleft',
    'network-copyleft',
    'source-available',
    'proprietary',
})

# Google licenseclassifier categories.
# See: https://github.com/google/licenseclassifier/blob/main/license_type.go
_VALID_GOOGLE_CATEGORIES = frozenset({
    'restricted',
    'reciprocal',
    'notice',
    'permissive',
    'unencumbered',
    'by_exception_only',
    'forbidden',
})


class LicenseDataError(Exception):
    """Raised when license TOML data fails validation.

    Attributes:
        errors: List of human-readable error strings.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        bullet_list = '\n'.join(f'  - {e}' for e in errors)
        super().__init__(f'License database has {len(errors)} validation error(s):\n{bullet_list}')


_DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
_LICENSES_TOML = _DATA_DIR / 'licenses.toml'
_COMPAT_TOML = _DATA_DIR / 'license_compatibility.toml'


@dataclass(frozen=True)
class LicenseInfo:
    """Metadata for a single license node.

    Attributes:
        spdx_id: Canonical SPDX identifier (the graph node key).
        name: Human-readable full name.
        category: License category string.
        osi_approved: Whether OSI has approved this license.
        aliases: Case-insensitive strings that resolve to this ID.
        google_category: Google licenseclassifier category.
        or_later_chain: SPDX IDs for the "or later" version chain.
        patent_grant: Whether this license contains an explicit
            patent grant clause (e.g. Apache-2.0 §3).
        patent_retaliation: Whether this license terminates rights
            upon patent litigation (e.g. Apache-2.0 §3, EPL §7).
    """

    spdx_id: str
    name: str
    category: str
    osi_approved: bool
    aliases: tuple[str, ...]
    google_category: str = ''
    or_later_chain: tuple[str, ...] = ()
    patent_grant: bool = False
    patent_retaliation: bool = False


@dataclass
class LicenseGraph:
    """Directed graph of license compatibility relationships.

    Attributes:
        nodes: Mapping from SPDX ID → LicenseInfo.
        edges: Mapping from SPDX ID → set of SPDX IDs it can depend on.
    """

    nodes: dict[str, LicenseInfo] = field(default_factory=dict)
    edges: dict[str, set[str]] = field(default_factory=dict)

    # ── Loading ──────────────────────────────────────────────────────

    @classmethod
    def load(
        cls,
        *,
        licenses_toml: Path | None = None,
        compat_toml: Path | None = None,
        user_toml: Path | None = None,
    ) -> LicenseGraph:
        """Load the license graph from TOML data files.

        Args:
            licenses_toml: Path to the license registry TOML.
                Defaults to the built-in ``data/licenses.toml``.
            compat_toml: Path to the compatibility rules TOML.
                Defaults to the built-in ``data/license_compatibility.toml``.
            user_toml: Optional user-provided TOML with additional
                licenses and/or rules to merge on top of the built-in data.

        Returns:
            A fully constructed :class:`LicenseGraph`.
        """
        graph = cls()

        # 1. Load built-in license registry.
        lic_path = licenses_toml or _LICENSES_TOML
        graph._load_licenses(lic_path)  # noqa: SLF001

        # 2. Load built-in compatibility rules.
        compat_path = compat_toml or _COMPAT_TOML
        graph._load_rules(compat_path)  # noqa: SLF001

        # 3. Merge user overrides (if provided).
        if user_toml and user_toml.is_file():
            graph._load_user_overrides(user_toml)  # noqa: SLF001

        # 4. Validate the assembled graph.
        graph.validate()

        return graph

    def _load_licenses(self, path: Path) -> None:
        """Parse ``licenses.toml`` and populate :attr:`nodes`."""
        with path.open('rb') as f:
            data = tomllib.load(f)
        errors: list[str] = []
        for spdx_id, info in data.items():
            if not isinstance(info, dict):
                errors.append(f'[{spdx_id}]: expected a table, got {type(info).__name__}')
                continue
            # Validate required fields and types.
            if 'name' not in info:
                errors.append(f'[{spdx_id}]: missing required field "name"')
            elif not isinstance(info['name'], str):
                errors.append(f'[{spdx_id}].name: expected string, got {type(info["name"]).__name__}')
            cat = info.get('category', '')
            if not cat:
                errors.append(f'[{spdx_id}]: missing required field "category"')
            elif cat not in _VALID_CATEGORIES:
                errors.append(
                    f'[{spdx_id}].category: {cat!r} is not a valid category. '
                    f'Must be one of: {", ".join(sorted(_VALID_CATEGORIES))}'
                )
            if 'osi_approved' in info and not isinstance(info['osi_approved'], bool):
                errors.append(f'[{spdx_id}].osi_approved: expected bool, got {type(info["osi_approved"]).__name__}')
            aliases = info.get('aliases', [])
            if not isinstance(aliases, list):
                errors.append(f'[{spdx_id}].aliases: expected list, got {type(aliases).__name__}')
            elif not all(isinstance(a, str) for a in aliases):
                errors.append(f'[{spdx_id}].aliases: all entries must be strings')
            gcat = info.get('google_category', '')
            if gcat and gcat not in _VALID_GOOGLE_CATEGORIES:
                errors.append(
                    f'[{spdx_id}].google_category: {gcat!r} is not valid. '
                    f'Must be one of: {", ".join(sorted(_VALID_GOOGLE_CATEGORIES))}'
                )
            or_later = info.get('or_later_chain', [])
            if not isinstance(or_later, list):
                errors.append(f'[{spdx_id}].or_later_chain: expected list, got {type(or_later).__name__}')
                or_later = []
            elif not all(isinstance(v, str) for v in or_later):
                errors.append(f'[{spdx_id}].or_later_chain: all entries must be strings')
                or_later = []
            self.nodes[spdx_id] = LicenseInfo(
                spdx_id=spdx_id,
                name=info.get('name', spdx_id),
                category=info.get('category', 'unknown'),
                osi_approved=info.get('osi_approved', False),
                aliases=tuple(info.get('aliases', ())),
                google_category=gcat,
                or_later_chain=tuple(or_later),
                patent_grant=bool(info.get('patent_grant', False)),
                patent_retaliation=bool(info.get('patent_retaliation', False)),
            )
            self.edges.setdefault(spdx_id, set())
        if errors:
            raise LicenseDataError(errors)

    def _load_rules(self, path: Path) -> None:
        """Parse ``license_compatibility.toml`` and populate :attr:`edges`."""
        with path.open('rb') as f:
            data = tomllib.load(f)
        rules = data.get('rule', [])
        if not isinstance(rules, list):
            raise LicenseDataError(['"rule" must be an array of tables ([[rule]]).'])
        errors: list[str] = []
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f'rule[{i}]: expected a table, got {type(rule).__name__}')
                continue
            if 'from' not in rule:
                errors.append(f'rule[{i}]: missing required field "from"')
                continue
            if not isinstance(rule['from'], str):
                errors.append(f'rule[{i}].from: expected string, got {type(rule["from"]).__name__}')
                continue
            if 'to' not in rule:
                errors.append(f'rule[{i}]: missing required field "to"')
                continue
            if not isinstance(rule['to'], list):
                errors.append(f'rule[{i}].to: expected list, got {type(rule["to"]).__name__}')
                continue
            if not all(isinstance(t, str) for t in rule['to']):
                errors.append(f'rule[{i}].to: all entries must be strings')
                continue
            from_id: str = rule['from']
            to_ids: list[str] = rule['to']
            self.edges.setdefault(from_id, set()).update(to_ids)
        if errors:
            raise LicenseDataError(errors)

    def _load_user_overrides(self, path: Path) -> None:
        """Merge user-provided TOML on top of built-in data.

        Expected format::

            # Additional licenses.
            [licenses.MyCustom-1.0]
            name = "My Custom License"
            category = "permissive"
            osi_approved = false
            aliases = ["my custom license"]

            # Additional compatibility rules.
            [[rule]]
            from = "MyCustom-1.0"
            to = ["MIT", "Apache-2.0"]
        """
        with path.open('rb') as f:
            data = tomllib.load(f)

        # Merge licenses.
        for spdx_id, info in data.get('licenses', {}).items():
            existing = self.nodes.get(spdx_id)
            if existing:
                # Merge: user aliases extend built-in aliases.
                merged_aliases = set(existing.aliases)
                merged_aliases.update(info.get('aliases', ()))
                self.nodes[spdx_id] = LicenseInfo(
                    spdx_id=spdx_id,
                    name=info.get('name', existing.name),
                    category=info.get('category', existing.category),
                    osi_approved=info.get('osi_approved', existing.osi_approved),
                    aliases=tuple(sorted(merged_aliases)),
                )
            else:
                self.nodes[spdx_id] = LicenseInfo(
                    spdx_id=spdx_id,
                    name=info.get('name', spdx_id),
                    category=info.get('category', 'unknown'),
                    osi_approved=info.get('osi_approved', False),
                    aliases=tuple(info.get('aliases', ())),
                )
            self.edges.setdefault(spdx_id, set())

        # Merge rules (append).
        for rule in data.get('rule', []):
            from_id: str = rule['from']
            to_ids: list[str] = rule['to']
            self.edges.setdefault(from_id, set()).update(to_ids)

    # ── Queries ──────────────────────────────────────────────────────

    def known(self, spdx_id: str) -> bool:
        """Return ``True`` if *spdx_id* is a known node in the graph."""
        return spdx_id in self.nodes

    def category(self, spdx_id: str) -> str:
        """Return the category of *spdx_id*, or ``"unknown"``."""
        info = self.nodes.get(spdx_id)
        return info.category if info else 'unknown'

    def google_category(self, spdx_id: str) -> str:
        """Return the Google licenseclassifier category, or ``""``."""
        info = self.nodes.get(spdx_id)
        return info.google_category if info else ''

    def is_compatible(
        self,
        project_license: str,
        dep: LicenseId | LicenseRef | str,
    ) -> bool:
        """Check if a project can depend on code under *dep*.

        This method checks **single license IDs** (with optional
        ``or_later`` expansion).  Compound SPDX expressions (``OR``,
        ``AND``, ``WITH``) are handled at a higher level by
        :func:`releasekit.spdx_expr.is_compatible`, which walks the
        AST and calls this method for each leaf ``LicenseId`` node.

        ``WITH`` (linking exception) handling:
            Exceptions like ``Classpath-exception-2.0`` relax the base
            license's terms but are **not modeled in the graph**.
            The SPDX expression evaluator strips the exception and
            checks compat against the base license only (conservative
            approach).  See ``spdx_expr._eval_compat`` and
            ``docs/internals/license-data.md`` for the full rationale
            on why this is language-agnostic and intentional.

        Args:
            project_license: The SPDX ID of the project's own license.
            dep: The dependency's license — either a parsed AST node
                (preserving ``or_later``) or a plain SPDX ID string.

        Returns:
            ``True`` if the dependency is compatible.
        """
        # Normalize dep to (spdx_id, or_later).
        if isinstance(dep, LicenseId):
            dep_id = dep.id
            or_later = dep.or_later
        elif isinstance(dep, LicenseRef):
            # User-defined refs: unknown to the graph → incompatible.
            return False
        elif isinstance(dep, str):
            dep_id = dep
            or_later = False
        else:
            return False

        proj_edges = self.edges.get(project_license)
        if proj_edges is None:
            # Project license not in graph → can't determine.
            return False

        # Direct check.
        if dep_id in proj_edges:
            return True

        # or_later expansion: if the dep has +, try all later versions.
        if or_later:
            node = self.nodes.get(dep_id)
            chain = node.or_later_chain if node else ()
            return any(ver in proj_edges for ver in chain)

        return False

    def incompatible_deps(
        self,
        project_license: str,
        dep_licenses: dict[str, LicenseId | LicenseRef | str],
    ) -> dict[str, str]:
        """Find all incompatible dependencies.

        Args:
            project_license: The SPDX ID of the project's own license.
            dep_licenses: Mapping from package name → dependency license.

        Returns:
            Mapping from package name → dependency SPDX ID for each
            incompatible dependency.
        """
        violations: dict[str, str] = {}
        for pkg_name, dep in dep_licenses.items():
            if not self.is_compatible(project_license, dep):
                if isinstance(dep, LicenseId):
                    violations[pkg_name] = str(dep)
                elif isinstance(dep, LicenseRef):
                    violations[pkg_name] = str(dep)
                else:
                    violations[pkg_name] = dep
        return violations

    def patent_grant_licenses(self) -> frozenset[str]:
        """Return the set of SPDX IDs with explicit patent grant clauses."""
        return frozenset(spdx_id for spdx_id, info in self.nodes.items() if info.patent_grant)

    def patent_retaliation_licenses(self) -> frozenset[str]:
        """Return the set of SPDX IDs with patent retaliation clauses."""
        return frozenset(spdx_id for spdx_id, info in self.nodes.items() if info.patent_retaliation)

    def all_aliases(self) -> dict[str, str]:
        """Return a mapping from lowercase alias → canonical SPDX ID.

        Used by the fuzzy resolver for fast exact/alias lookups.
        """
        result: dict[str, str] = {}
        for spdx_id, info in self.nodes.items():
            # The SPDX ID itself (case-insensitive).
            result[spdx_id.lower()] = spdx_id
            for alias in info.aliases:
                result[alias.lower()] = spdx_id
        return result

    def validate(self) -> None:
        """Validate the assembled graph for consistency.

        Checks:
            1. Every ``from`` in a rule references a known license node.
            2. Every ``to`` target in a rule references a known license node.
            3. No two licenses share the same alias (case-insensitive).
            4. Every license has a valid category.

        Raises:
            LicenseDataError: If any validation errors are found.
        """
        errors: list[str] = []
        known = set(self.nodes.keys())

        # Check edge references.
        for from_id, to_ids in self.edges.items():
            if from_id not in known:
                errors.append(f'Compatibility rule "from" references unknown license: {from_id!r}')
            for to_id in to_ids:
                if to_id not in known:
                    errors.append(f'Compatibility rule from={from_id!r} references unknown "to" license: {to_id!r}')

        # Check for duplicate aliases across different licenses.
        seen_aliases: dict[str, str] = {}
        for spdx_id, info in self.nodes.items():
            for alias in info.aliases:
                lower = alias.lower()
                if lower in seen_aliases and seen_aliases[lower] != spdx_id:
                    errors.append(f'Duplicate alias {alias!r} claimed by both {seen_aliases[lower]!r} and {spdx_id!r}')
                seen_aliases[lower] = spdx_id

        # Check categories.
        for spdx_id, info in self.nodes.items():
            if info.category not in _VALID_CATEGORIES:
                errors.append(
                    f'[{spdx_id}].category: {info.category!r} is not valid. '
                    f'Must be one of: {", ".join(sorted(_VALID_CATEGORIES))}'
                )

        if errors:
            raise LicenseDataError(errors)
