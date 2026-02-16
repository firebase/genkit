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

"""Go workspace backend for releasekit.

The :class:`GoWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol by parsing
``go.work`` and ``go.mod`` files.

Go workspace layout (directory name is arbitrary)::

    Multi-module workspace (go.work):

    go/
    ├── go.work          ← workspace root (lists module dirs)
    ├── genkit/
    │   └── go.mod       ← module: github.com/firebase/genkit/go/genkit
    ├── plugins/
    │   ├── googleai/
    │   │   └── go.mod   ← module: github.com/firebase/genkit/go/plugins/googleai
    │   └── vertexai/
    │       └── go.mod   ← module: github.com/firebase/genkit/go/plugins/vertexai
    └── samples/
        └── ...

    Single-module repo (go.mod only, no go.work):

    go/
    ├── go.mod           ← module root: github.com/firebase/genkit/go
    ├── ai/
    ├── core/
    ├── plugins/
    └── samples/
        └── mcp-git-pr-explainer/
            └── go.mod   ← sub-module (discovered separately)

Version handling:

    Go modules don't store versions in ``go.mod``. The version is derived
    from the VCS tag (e.g. ``go/genkit/v0.5.0``). The ``rewrite_version``
    method is a no-op — version bumps happen via VCS tags.

    Dependencies between workspace modules are declared in ``go.mod``
    with ``require`` directives and resolved via ``go.work``'s ``use``
    directives during development.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from releasekit.backends.workspace._io import read_file, write_file
from releasekit.backends.workspace._types import Package
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.go')

# Regex to parse ``use`` directives from go.work.
# Matches both single-line ``use ./foo`` and block ``use ( ./foo \n ./bar )``.
_USE_RE = re.compile(r'^\s*(?:use\s+)?(\./\S+)', re.MULTILINE)

# Regex to parse the module path from go.mod.
_MODULE_RE = re.compile(r'^module\s+(\S+)', re.MULTILINE)

# Regex to parse Go version from go.mod (informational only).
_GO_VERSION_RE = re.compile(r'^go\s+(\S+)', re.MULTILINE)

# Regex to parse require directives from go.mod.
_REQUIRE_RE = re.compile(r'^\s*(\S+)\s+v[\d.]+', re.MULTILINE)


class GoWorkspace:
    """Go :class:`~releasekit.backends.workspace.Workspace` implementation.

    Parses ``go.work`` (multi-module) or ``go.mod`` (single-module) to
    discover workspace modules and their dependencies.

    When ``go.work`` is present, modules are discovered from its ``use``
    directives. When only ``go.mod`` is present, the root module is
    discovered along with any sub-modules found by walking the tree.

    Args:
        workspace_root: Path to the directory containing ``go.work``
            or ``go.mod``.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the Go workspace root."""
        self._root = workspace_root.resolve()

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all Go modules in the workspace.

        When ``go.work`` exists, modules are discovered from its ``use``
        directives. Otherwise, the root ``go.mod`` is used as the primary
        module and any sub-module ``go.mod`` files found by walking the
        directory tree are discovered as additional modules.

        Args:
            exclude_patterns: Glob patterns to exclude modules by name.

        Returns:
            Sorted list of discovered Go module packages.
        """
        go_work = self._root / 'go.work'
        if go_work.is_file():
            return self._discover_from_go_work(go_work, exclude_patterns)
        return self._discover_from_go_mod(exclude_patterns)

    def _discover_from_go_work(
        self,
        go_work: Path,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover modules from ``go.work`` ``use`` directives."""
        text = go_work.read_text(encoding='utf-8')
        use_dirs = _USE_RE.findall(text)

        # Collect all module paths first for internal dep classification.
        all_module_paths: dict[str, Path] = {}
        for use_dir in use_dirs:
            mod_dir = (self._root / use_dir).resolve()
            go_mod = mod_dir / 'go.mod'
            if go_mod.is_file():
                mod_text = go_mod.read_text(encoding='utf-8')
                m = _MODULE_RE.search(mod_text)
                if m:
                    all_module_paths[m.group(1)] = mod_dir

        return self._build_packages(all_module_paths, exclude_patterns)

    def _discover_from_go_mod(
        self,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover modules from a standalone ``go.mod`` (no ``go.work``).

        Discovers the root module and any sub-modules found by walking
        the directory tree for additional ``go.mod`` files.
        """
        root_go_mod = self._root / 'go.mod'
        if not root_go_mod.is_file():
            log.warning('go_mod_not_found', root=str(self._root))
            return []

        all_module_paths: dict[str, Path] = {}

        # Root module.
        root_text = root_go_mod.read_text(encoding='utf-8')
        m = _MODULE_RE.search(root_text)
        if m:
            all_module_paths[m.group(1)] = self._root

        # Walk for sub-modules (nested go.mod files).
        for go_mod in sorted(self._root.rglob('go.mod')):
            if go_mod == root_go_mod:
                continue
            mod_dir = go_mod.parent.resolve()
            mod_text = go_mod.read_text(encoding='utf-8')
            sub_m = _MODULE_RE.search(mod_text)
            if sub_m:
                all_module_paths[sub_m.group(1)] = mod_dir

        return self._build_packages(all_module_paths, exclude_patterns)

    def _build_packages(
        self,
        all_module_paths: dict[str, Path],
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Build :class:`Package` list from a module-path-to-dir mapping."""
        packages: list[Package] = []
        exclude = exclude_patterns or []

        for module_path, mod_dir in sorted(all_module_paths.items()):
            # Use the last path component as the short name.
            name = module_path.rsplit('/', 1)[-1]

            if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                log.debug('excluded', module=module_path, pattern=exclude)
                continue

            go_mod = mod_dir / 'go.mod'
            mod_text = go_mod.read_text(encoding='utf-8')

            # Parse Go version (informational — not a package version).
            go_ver_match = _GO_VERSION_RE.search(mod_text)
            go_version = go_ver_match.group(1) if go_ver_match else '0.0.0'

            # Parse require directives.
            requires = _REQUIRE_RE.findall(mod_text)
            internal_deps = [r for r in requires if r in all_module_paths]
            external_deps = [r for r in requires if r not in all_module_paths]

            # Go modules are always publishable (no private marker).
            packages.append(
                Package(
                    name=name,
                    version=go_version,
                    path=mod_dir,
                    manifest_path=go_mod,
                    internal_deps=[all_module_paths[dep].name for dep in internal_deps],
                    external_deps=external_deps,
                    all_deps=requires,
                    is_publishable=True,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info(
            'discovered',
            count=len(packages),
            modules=[p.name for p in packages],
        )
        return packages

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """No-op: Go module versions are set by VCS tags, not go.mod.

        Returns the Go toolchain version from go.mod as a placeholder.
        """
        text = await read_file(manifest_path)
        m = _GO_VERSION_RE.search(text)
        old_version = m.group(1) if m else '0.0.0'
        log.info(
            'rewrite_version_noop',
            manifest=str(manifest_path),
            reason='Go versions are set by VCS tags.',
        )
        return old_version

    async def rewrite_dependency_version(
        self,
        manifest_path: Path,
        dep_name: str,
        new_version: str,
    ) -> None:
        """Rewrite a dependency version in ``go.mod``.

        Updates the ``require`` directive for ``dep_name`` to use
        ``new_version``. This is used for pinning workspace dependencies
        before a release build.
        """
        text = await read_file(manifest_path)

        # Match: dep_name vX.Y.Z
        pattern = re.compile(
            rf'(\s+{re.escape(dep_name)}\s+)v[\d.]+[-\w.]*',
        )
        new_text = pattern.sub(rf'\g<1>v{new_version}', text)

        if new_text != text:
            await write_file(manifest_path, new_text)
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


__all__ = [
    'GoWorkspace',
]
