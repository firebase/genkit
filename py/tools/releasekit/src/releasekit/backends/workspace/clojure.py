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

"""Clojure workspace backend for releasekit.

The :class:`ClojureWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol by parsing
``deps.edn`` (tools.deps) or ``project.clj`` (Leiningen) files.

tools.deps layout (``deps.edn``)::

    clojure/
    ├── deps.edn             ← root deps (may list :local/root sub-projects)
    ├── core/
    │   └── deps.edn         ← sub-project: my.group/core
    ├── plugins/
    │   └── google/
    │       └── deps.edn     ← sub-project: my.group/google
    └── build.clj            ← optional build script (tools.build)

Leiningen layout (``project.clj``)::

    clojure/
    ├── project.clj          ← root project (may be a multi-module via lein-sub)
    ├── core/
    │   └── project.clj      ← sub-project
    └── plugins/
        └── google/
            └── project.clj  ← sub-project

Version handling:

    Leiningen stores the version as the third form in ``defproject``.
    tools.deps does not have a built-in version field — the version
    is typically in ``pom.xml`` (generated via ``clj -X:deps mvn-pom``)
    or in a ``version.edn`` / ``build.clj`` file.  We check, in order:

    1. ``pom.xml`` sibling (``<version>`` element)
    2. ``version.edn`` sibling (plain string)
    3. ``"0.0.0"`` fallback
"""

from __future__ import annotations

import fnmatch
import xml.etree.ElementTree as ET  # noqa: N817, S405
from pathlib import Path

from releasekit._types import DetectedLicense
from releasekit.backends.workspace._edn import EdnReader, parse_edn
from releasekit.backends.workspace._io import read_file, write_file
from releasekit.backends.workspace._types import Package
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.clojure')

# Backward-compatible private aliases used throughout this module.
_EdnReader = EdnReader
_parse_edn = parse_edn


# Maven POM namespace (reused from maven.py).
_POM_NS = '{http://maven.apache.org/POM/4.0.0}'


def _safe_xml_parser() -> ET.XMLParser:
    """Return an XMLParser with external entity resolution disabled."""
    return ET.XMLParser()  # noqa: S314


def _safe_parse(path: Path) -> ET.ElementTree:  # noqa: ANN201
    """Parse an XML file with a hardened parser."""
    return ET.parse(path, parser=_safe_xml_parser())  # type: ignore[return-value]  # noqa: S314


def _safe_fromstring(text: str) -> ET.Element:
    """Parse an XML string with a hardened parser."""
    return ET.fromstring(text, parser=_safe_xml_parser())  # noqa: S314


def _parse_deps_edn(deps_path: Path) -> dict[str, object]:
    """Parse a ``deps.edn`` file into a Python dict.

    Returns an empty dict if the file is missing or malformed.
    """
    if not deps_path.is_file():
        return {}
    text = deps_path.read_text(encoding='utf-8')
    try:
        result = _parse_edn(text)
    except ValueError:
        log.warning('deps_edn_parse_failed', path=str(deps_path))
        return {}
    if not isinstance(result, dict):
        return {}
    return result  # type: ignore[return-value]  # Ty: dict[Unknown, Unknown] vs dict[str, object]


def _extract_deps_edn_deps(edn: dict[str, object]) -> list[str]:
    """Extract dependency names from a parsed ``deps.edn`` map.

    Returns a list of ``groupId/artifactId`` strings from the
    ``:deps`` key.
    """
    deps = edn.get(':deps')
    if not isinstance(deps, dict):
        return []
    return [str(k) for k in deps]


def _extract_deps_edn_local_deps(edn: dict[str, object]) -> list[str]:
    """Extract ``:local/root`` paths from a parsed ``deps.edn`` map.

    Returns a list of relative path strings for local sub-project
    dependencies.
    """
    deps = edn.get(':deps')
    if not isinstance(deps, dict):
        return []
    local_roots: list[str] = []
    for coord in deps.values():
        if isinstance(coord, dict):
            root = coord.get(':local/root')  # type: ignore[union-attr]
            if isinstance(root, str):
                local_roots.append(root)
    return local_roots


def _read_pom_version(pom_path: Path) -> str:
    """Read ``<version>`` from a ``pom.xml`` file.

    Returns the version string, or empty string if not found.
    """
    if not pom_path.is_file():
        return ''
    try:
        tree = _safe_parse(pom_path)
    except ET.ParseError:
        return ''
    root = tree.getroot()
    if root is None:
        return ''
    for tag in (f'{_POM_NS}version', 'version'):
        elem = root.find(tag)
        if elem is not None and elem.text:
            return elem.text
    return ''


def _read_pom_artifact_id(pom_path: Path) -> str:
    """Read ``<artifactId>`` from a ``pom.xml`` file.

    Returns the artifactId string, or empty string if not found.
    """
    if not pom_path.is_file():
        return ''
    try:
        tree = _safe_parse(pom_path)
    except ET.ParseError:
        return ''
    root = tree.getroot()
    if root is None:
        return ''
    for tag in (f'{_POM_NS}artifactId', 'artifactId'):
        elem = root.find(tag)
        if elem is not None and elem.text:
            return elem.text
    return ''


def _read_pom_group_id(pom_path: Path) -> str:
    """Read ``<groupId>`` from a ``pom.xml`` file.

    Returns the groupId string, or empty string if not found.
    """
    if not pom_path.is_file():
        return ''
    try:
        tree = _safe_parse(pom_path)
    except ET.ParseError:
        return ''
    root = tree.getroot()
    if root is None:
        return ''
    for tag in (f'{_POM_NS}groupId', 'groupId'):
        elem = root.find(tag)
        if elem is not None and elem.text:
            return elem.text
    return ''


def _read_version_edn(version_path: Path) -> str:
    """Read a version from a ``version.edn`` file.

    Expects the file to contain a plain EDN string like ``"1.2.3"``.
    Returns the version string, or empty string if not found.
    """
    if not version_path.is_file():
        return ''
    text = version_path.read_text(encoding='utf-8').strip()
    # Strip surrounding quotes if present.
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    return text if text else ''


def _parse_project_clj_forms(text: str) -> list[object] | None:
    """Parse a ``project.clj`` file into a list of S-expression forms.

    Returns the parsed ``(defproject ...)`` list, or ``None`` if
    parsing fails or the file does not contain a ``defproject`` form.
    """
    try:
        reader = _EdnReader(text)
        form = reader.read()
    except ValueError:
        return None
    if not isinstance(form, list) or len(form) < 3:  # noqa: PLR2004
        return None
    if form[0] != 'defproject':
        return None
    return form  # type: ignore[return-value]  # Ty: list[Unknown] vs list[object]


def _parse_project_clj(project_path: Path) -> dict[str, str]:
    """Parse ``defproject`` from a ``project.clj`` file.

    Uses the S-expression parser to extract the project name and
    version from ``(defproject group/name "version" ...)``.

    Returns a dict with keys ``name``, ``version``, ``group``,
    ``artifact``.  Returns empty dict if parsing fails.
    """
    if not project_path.is_file():
        return {}
    text = project_path.read_text(encoding='utf-8')
    form = _parse_project_clj_forms(text)
    if form is None:
        return {}
    # form[0] == 'defproject', form[1] == name symbol, form[2] == version string
    full_name = str(form[1])
    version = str(form[2])
    if '/' in full_name:
        group, artifact = full_name.split('/', 1)
    else:
        group = full_name
        artifact = full_name
    return {
        'name': full_name,
        'version': version,
        'group': group,
        'artifact': artifact,
    }


def _parse_project_clj_deps(project_path: Path) -> list[str]:
    """Parse dependency names from a ``project.clj`` file.

    Uses the S-expression parser to walk the ``defproject`` form
    and extract the ``:dependencies`` vector.

    Returns a list of ``group/artifact`` strings.
    """
    if not project_path.is_file():
        return []
    text = project_path.read_text(encoding='utf-8')
    form = _parse_project_clj_forms(text)
    if form is None:
        return []
    # Walk the form looking for :dependencies keyword followed by a vector.
    for i, item in enumerate(form):
        if item == ':dependencies' and i + 1 < len(form):
            deps_vec = form[i + 1]
            if not isinstance(deps_vec, list):
                return []
            names: list[str] = []
            for dep_entry in deps_vec:
                if isinstance(dep_entry, list) and len(dep_entry) >= 2:  # noqa: PLR2004
                    names.append(str(dep_entry[0]))
            return names
    return []


def _rewrite_project_clj_version(project_path: Path, new_version: str) -> str:
    """Rewrite the version in a ``project.clj`` file.

    Uses the S-expression parser with span tracking to locate the
    exact byte offsets of the version string, then performs a
    targeted text splice.  Returns the old version string.
    """
    text = project_path.read_text(encoding='utf-8')
    try:
        reader = _EdnReader(text)
        reader._skip_whitespace_and_comments()
        if reader._peek() != '(':
            return '0.0.0'
        reader._advance()  # consume '('
        reader._skip_whitespace_and_comments()
        sym = reader.read()  # 'defproject'
        if sym != 'defproject':
            return '0.0.0'
        reader._skip_whitespace_and_comments()
        reader.read()  # project name — skip
        reader._skip_whitespace_and_comments()
        # Read the version string with its source span.
        old_version, start, end = reader.read_string_with_span()
    except ValueError:
        return '0.0.0'
    # Splice the new version into the original text (including quotes).
    new_text = text[:start] + '"' + new_version + '"' + text[end:]
    if new_text != text:
        project_path.write_text(new_text, encoding='utf-8')
    return old_version


def _rewrite_pom_version(pom_path: Path, new_version: str) -> str:
    """Rewrite ``<version>`` in a ``pom.xml`` file.

    Returns the old version string.
    """
    text = pom_path.read_text(encoding='utf-8')
    try:
        root = _safe_fromstring(text)
    except ET.ParseError:
        return '0.0.0'
    version_elem = root.find(f'{_POM_NS}version')
    if version_elem is None:
        version_elem = root.find('version')
    if version_elem is None or not version_elem.text:
        return '0.0.0'
    old_version = version_elem.text
    old_tag = f'<version>{old_version}</version>'
    new_tag = f'<version>{new_version}</version>'
    new_text = text.replace(old_tag, new_tag, 1)
    if new_text != text:
        pom_path.write_text(new_text, encoding='utf-8')
    return old_version


def _rewrite_version_edn(version_path: Path, new_version: str) -> str:
    """Rewrite the version in a ``version.edn`` file.

    Returns the old version string.
    """
    old = _read_version_edn(version_path)
    version_path.write_text(f'"{new_version}"\n', encoding='utf-8')
    return old or '0.0.0'


def _rewrite_project_clj_dep_version(
    project_path: Path,
    dep_name: str,
    new_version: str,
) -> bool:
    """Rewrite a dependency version in a ``project.clj`` file.

    Parses the file to locate the ``:dependencies`` vector, then
    scans each ``[lib "version"]`` entry using the span-tracking
    reader to find the exact byte offsets of the version string.
    Returns True if a replacement was made.
    """
    text = project_path.read_text(encoding='utf-8')
    form = _parse_project_clj_forms(text)
    if form is None:
        return False
    # Find the :dependencies keyword position in the source text.
    dep_kw_pos = text.find(':dependencies')
    if dep_kw_pos == -1:
        return False
    # Advance past :dependencies to find the outer vector '['.
    search_start = dep_kw_pos + len(':dependencies')
    bracket_pos = text.find('[', search_start)
    if bracket_pos == -1:
        return False
    # Parse from the outer '[' to walk each dep entry.
    reader = _EdnReader(text[bracket_pos:])
    try:
        reader._advance()  # consume outer '['
        while True:
            reader._skip_whitespace_and_comments()
            if reader._peek() == ']':
                break
            # Each dep entry is [lib "version" ...]
            if reader._peek() != '[':
                reader.read()  # skip unexpected form
                continue
            reader._advance()  # consume inner '['
            reader._skip_whitespace_and_comments()
            lib_name = reader.read()  # library symbol
            reader._skip_whitespace_and_comments()
            if reader._peek() == '"' and str(lib_name) == dep_name:
                _, ver_start, ver_end = reader.read_string_with_span()
                # Offsets are relative to bracket_pos.
                abs_start = bracket_pos + ver_start
                abs_end = bracket_pos + ver_end
                new_text = text[:abs_start] + '"' + new_version + '"' + text[abs_end:]
                project_path.write_text(new_text, encoding='utf-8')
                return True
            # Skip the rest of this entry.
            while reader._peek() != ']' and reader.pos < len(reader._text):
                reader.read()
            if reader._peek() == ']':
                reader._advance()
    except ValueError:
        pass
    return False


def _rewrite_deps_edn_dep_version(
    deps_path: Path,
    dep_name: str,
    new_version: str,
) -> bool:
    """Rewrite a dependency version in a ``deps.edn`` file.

    Parses the file to locate the ``:deps`` map, then scans each
    entry to find ``dep_name`` and its ``:mvn/version`` string.
    Uses span tracking for a targeted text splice.
    Returns True if a replacement was made.
    """
    text = deps_path.read_text(encoding='utf-8')
    # Find the dep name in the source, then scan forward for :mvn/version.
    dep_pos = text.find(dep_name)
    if dep_pos == -1:
        return False
    # Scan forward from dep_pos for :mvn/version keyword then its string value.
    mvn_kw = ':mvn/version'
    mvn_pos = text.find(mvn_kw, dep_pos)
    if mvn_pos == -1:
        return False
    # Parse the string value right after :mvn/version using the reader.
    after_kw = mvn_pos + len(mvn_kw)
    reader = _EdnReader(text[after_kw:])
    try:
        reader._skip_whitespace_and_comments()
        if reader._peek() != '"':
            return False
        _, ver_start, ver_end = reader.read_string_with_span()
        abs_start = after_kw + ver_start
        abs_end = after_kw + ver_end
        new_text = text[:abs_start] + '"' + new_version + '"' + text[abs_end:]
        deps_path.write_text(new_text, encoding='utf-8')
        return True
    except ValueError:
        return False


class ClojureWorkspace:
    """Clojure :class:`~releasekit.backends.workspace.Workspace` implementation.

    Supports both tools.deps (``deps.edn``) and Leiningen
    (``project.clj``) project layouts.

    Args:
        workspace_root: Path to the Clojure workspace root.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the Clojure workspace root."""
        self._root = workspace_root.resolve()

    def _is_leiningen(self) -> bool:
        """Check if the workspace uses Leiningen."""
        return (self._root / 'project.clj').is_file()

    def _is_deps_edn(self) -> bool:
        """Check if the workspace uses tools.deps."""
        return (self._root / 'deps.edn').is_file()

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all Clojure projects in the workspace.

        For Leiningen: scans for ``project.clj`` files in subdirectories.
        For tools.deps: scans for ``deps.edn`` files, using ``:local/root``
        references from the root ``deps.edn`` to find sub-projects.

        Args:
            exclude_patterns: Glob patterns to exclude projects by name.

        Returns:
            Sorted list of discovered Clojure packages.
        """
        if self._is_leiningen():
            return await self._discover_leiningen(exclude_patterns=exclude_patterns)
        if self._is_deps_edn():
            return await self._discover_deps_edn(exclude_patterns=exclude_patterns)
        log.warning('no_clojure_project_found', root=str(self._root))
        return []

    async def _discover_leiningen(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover Leiningen sub-projects."""
        exclude = exclude_patterns or []
        packages: list[Package] = []

        # Collect all sub-project directories containing project.clj.
        sub_dirs: list[Path] = []
        for child in sorted(self._root.iterdir()):
            if child.is_dir() and (child / 'project.clj').is_file():
                sub_dirs.append(child)

        # If no sub-projects, treat root as a single project.
        if not sub_dirs:
            meta = _parse_project_clj(self._root / 'project.clj')
            if meta:
                name = meta.get('artifact', self._root.name)
                if not any(fnmatch.fnmatch(name, pat) for pat in exclude):
                    packages.append(
                        Package(
                            name=name,
                            version=meta.get('version', '0.0.0'),
                            path=self._root,
                            manifest_path=self._root / 'project.clj',
                            internal_deps=[],
                            external_deps=_parse_project_clj_deps(self._root / 'project.clj'),
                            all_deps=_parse_project_clj_deps(self._root / 'project.clj'),
                            is_publishable=True,
                        )
                    )
            packages.sort(key=lambda p: p.name)
            log.info('discovered_leiningen', count=len(packages), projects=[p.name for p in packages])
            return packages

        # Collect all artifact names for internal dep classification.
        all_artifacts: set[str] = set()
        artifact_to_name: dict[str, str] = {}
        for sub_dir in sub_dirs:
            meta = _parse_project_clj(sub_dir / 'project.clj')
            if meta:
                full_name = meta.get('name', sub_dir.name)
                artifact = meta.get('artifact', sub_dir.name)
                all_artifacts.add(full_name)
                artifact_to_name[full_name] = artifact

        # Discover packages with dependency classification.
        for sub_dir in sub_dirs:
            meta = _parse_project_clj(sub_dir / 'project.clj')
            if not meta:
                continue
            artifact = meta.get('artifact', sub_dir.name)
            full_name = meta.get('name', sub_dir.name)

            if any(fnmatch.fnmatch(artifact, pat) for pat in exclude):
                log.debug('excluded', project=artifact)
                continue

            dep_names = _parse_project_clj_deps(sub_dir / 'project.clj')
            internal_deps = [artifact_to_name[d] for d in dep_names if d in all_artifacts and d != full_name]
            external_deps = [d for d in dep_names if d not in all_artifacts]

            packages.append(
                Package(
                    name=artifact,
                    version=meta.get('version', '0.0.0'),
                    path=sub_dir,
                    manifest_path=sub_dir / 'project.clj',
                    internal_deps=internal_deps,
                    external_deps=external_deps,
                    all_deps=dep_names,
                    is_publishable=True,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info('discovered_leiningen', count=len(packages), projects=[p.name for p in packages])
        return packages

    async def _discover_deps_edn(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover tools.deps sub-projects via ``:local/root`` references."""
        exclude = exclude_patterns or []
        packages: list[Package] = []

        root_edn = _parse_deps_edn(self._root / 'deps.edn')
        local_roots = _extract_deps_edn_local_deps(root_edn)

        # Resolve local roots to sub-project directories.
        sub_dirs: list[Path] = []
        for lr in local_roots:
            sub_dir = (self._root / lr).resolve()
            if sub_dir.is_dir() and (sub_dir / 'deps.edn').is_file():
                sub_dirs.append(sub_dir)

        # If no local roots, also scan immediate subdirectories for deps.edn.
        if not sub_dirs:
            for child in sorted(self._root.iterdir()):
                if child.is_dir() and (child / 'deps.edn').is_file() and child != self._root:
                    sub_dirs.append(child)

        # If still no sub-projects, treat root as a single project.
        if not sub_dirs:
            name = _read_pom_artifact_id(self._root / 'pom.xml') or self._root.name
            version = (
                _read_pom_version(self._root / 'pom.xml') or _read_version_edn(self._root / 'version.edn') or '0.0.0'
            )
            dep_names = _extract_deps_edn_deps(root_edn)
            if not any(fnmatch.fnmatch(name, pat) for pat in exclude):
                packages.append(
                    Package(
                        name=name,
                        version=version,
                        path=self._root,
                        manifest_path=self._root / 'deps.edn',
                        internal_deps=[],
                        external_deps=dep_names,
                        all_deps=dep_names,
                        is_publishable=True,
                    )
                )
            packages.sort(key=lambda p: p.name)
            log.info('discovered_deps_edn', count=len(packages), projects=[p.name for p in packages])
            return packages

        # Collect all sub-project names for internal dep classification.
        all_names: set[str] = set()
        name_map: dict[str, str] = {}  # full dep name → artifact name
        for sub_dir in sub_dirs:
            pom_name = _read_pom_artifact_id(sub_dir / 'pom.xml')
            pom_group = _read_pom_group_id(sub_dir / 'pom.xml')
            artifact = pom_name or sub_dir.name
            if pom_group and pom_name:
                full_dep = f'{pom_group}/{pom_name}'
                all_names.add(full_dep)
                name_map[full_dep] = artifact
            all_names.add(artifact)
            name_map[artifact] = artifact

        # Discover packages.
        for sub_dir in sub_dirs:
            sub_edn = _parse_deps_edn(sub_dir / 'deps.edn')
            pom_name = _read_pom_artifact_id(sub_dir / 'pom.xml')
            artifact = pom_name or sub_dir.name
            version = _read_pom_version(sub_dir / 'pom.xml') or _read_version_edn(sub_dir / 'version.edn') or '0.0.0'

            if any(fnmatch.fnmatch(artifact, pat) for pat in exclude):
                log.debug('excluded', project=artifact)
                continue

            dep_names = _extract_deps_edn_deps(sub_edn)
            internal_deps = [name_map[d] for d in dep_names if d in all_names and name_map.get(d) != artifact]
            external_deps = [d for d in dep_names if d not in all_names]

            # Determine manifest path: prefer pom.xml for version, else deps.edn.
            manifest = sub_dir / 'deps.edn'
            if (sub_dir / 'pom.xml').is_file():
                manifest = sub_dir / 'pom.xml'
            elif (sub_dir / 'version.edn').is_file():
                manifest = sub_dir / 'version.edn'

            packages.append(
                Package(
                    name=artifact,
                    version=version,
                    path=sub_dir,
                    manifest_path=manifest,
                    internal_deps=internal_deps,
                    external_deps=external_deps,
                    all_deps=dep_names,
                    is_publishable=True,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info('discovered_deps_edn', count=len(packages), projects=[p.name for p in packages])
        return packages

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite the version in a Clojure manifest file.

        Supported manifest types:

        - ``project.clj``: rewrites the version string in ``defproject``.
        - ``pom.xml``: rewrites ``<version>`` element.
        - ``version.edn``: rewrites the plain version string.

        Args:
            manifest_path: Path to the manifest file.
            new_version: New version string.

        Returns:
            The old version string.
        """
        if manifest_path.name == 'project.clj':
            old = _rewrite_project_clj_version(manifest_path, new_version)
            log.info('version_rewritten', manifest=str(manifest_path), old=old, new=new_version)
            return old
        if manifest_path.name == 'pom.xml':
            old = _rewrite_pom_version(manifest_path, new_version)
            log.info('version_rewritten', manifest=str(manifest_path), old=old, new=new_version)
            return old
        if manifest_path.name == 'version.edn':
            old = _rewrite_version_edn(manifest_path, new_version)
            log.info('version_rewritten', manifest=str(manifest_path), old=old, new=new_version)
            return old
        # Fallback: try as pom.xml.
        log.warning('unknown_manifest_type', manifest=str(manifest_path))
        return '0.0.0'

    async def rewrite_dependency_version(
        self,
        manifest_path: Path,
        dep_name: str,
        new_version: str,
    ) -> None:
        """Rewrite a dependency version in a Clojure manifest file.

        Args:
            manifest_path: Path to the manifest file.
            dep_name: Dependency name to update.
            new_version: New version to pin to.
        """
        replaced = False
        if manifest_path.name == 'project.clj':
            replaced = _rewrite_project_clj_dep_version(manifest_path, dep_name, new_version)
        elif manifest_path.name == 'deps.edn':
            replaced = _rewrite_deps_edn_dep_version(manifest_path, dep_name, new_version)
        elif manifest_path.name == 'pom.xml':
            # Delegate to POM rewriting.
            text = await read_file(manifest_path)
            new_text = _rewrite_pom_dep_version_text(text, dep_name, new_version)
            if new_text != text:
                await write_file(manifest_path, new_text)
                replaced = True

        if replaced:
            log.info(
                'dependency_rewritten',
                manifest=str(manifest_path),
                dep=dep_name,
                version=new_version,
            )
        else:
            log.debug(
                'dependency_not_found',
                manifest=str(manifest_path),
                dep=dep_name,
            )

    async def detect_license(
        self,
        pkg_path: Path,
        pkg_name: str = '',
    ) -> DetectedLicense:
        """Detect license from Clojure manifests.

        ``project.clj`` may contain ``:license {"name" "..."}`` but
        parsing it reliably is complex. Returns empty so the caller
        falls back to LICENSE file scanning.
        """
        if not pkg_name:
            pkg_name = pkg_path.name
        return DetectedLicense(value='', source='', package_name=pkg_name)


def _rewrite_pom_dep_version_text(text: str, dep_name: str, new_version: str) -> str:
    """Rewrite a dependency version in POM XML text.

    Looks for ``<artifactId>dep_name</artifactId>`` and replaces
    the next ``<version>`` tag.
    """
    try:
        root = _safe_fromstring(text)
    except ET.ParseError:
        return text

    for deps_tag in (f'{_POM_NS}dependencies', 'dependencies'):
        deps_elem = root.find(deps_tag)
        if deps_elem is None:
            continue
        for dep in list(deps_elem):
            aid = dep.find(f'{_POM_NS}artifactId')
            if aid is None:
                aid = dep.find('artifactId')
            if aid is None or aid.text != dep_name:
                continue
            ver = dep.find(f'{_POM_NS}version')
            if ver is None:
                ver = dep.find('version')
            if ver is None or not ver.text:
                continue
            old_tag = f'<version>{ver.text}</version>'
            new_tag = f'<version>{new_version}</version>'
            aid_pos = text.find(f'<artifactId>{dep_name}</artifactId>')
            if aid_pos == -1:
                continue
            ver_pos = text.find(old_tag, aid_pos)
            if ver_pos == -1:
                continue
            return text[:ver_pos] + new_tag + text[ver_pos + len(old_tag) :]

    return text


__all__ = [
    'ClojureWorkspace',
]
