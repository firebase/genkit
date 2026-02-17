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

"""Python-specific auto-fixer functions for ``pyproject.toml`` and source trees."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import tomlkit

from releasekit.checks._constants import (
    _DEP_NAME_RE,
    _LICENSE_PATTERNS,
    _PLACEHOLDER_URL_PATTERNS,
    _PRIVATE_CLASSIFIER,
    DEPRECATED_CLASSIFIERS,
)
from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)


def fix_publish_classifiers(
    packages: list[Package],
    exclude_publish: list[str],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Fix ``Private :: Do Not Upload`` classifiers to match ``exclude_publish``.

    For each package:
    - If excluded but missing the classifier → add it.
    - If NOT excluded but has the classifier → remove it.

    Uses ``tomlkit`` to preserve formatting and comments.

    Args:
        packages: All discovered workspace packages.
        exclude_publish: Resolved glob patterns for excluded packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made (or that
        would be made in dry-run mode).
    """
    changes: list[str] = []

    for pkg in packages:
        is_excluded = any(fnmatch.fnmatch(pkg.name, pat) for pat in exclude_publish)
        has_private = not pkg.is_publishable

        if is_excluded and has_private:
            continue  # Already consistent.
        if not is_excluded and not has_private:
            continue  # Already consistent.

        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception as exc:
            logger.warning('fix_classifier_parse_error', path=str(pkg.manifest_path), error=str(exc))
            continue

        project = doc.get('project')
        if project is None:
            continue

        classifiers = project.get('classifiers')
        if classifiers is None:
            if is_excluded:
                # Need to add classifier but there's no classifiers list.
                project['classifiers'] = [_PRIVATE_CLASSIFIER]
                action = f'{pkg.name}: added classifiers with {_PRIVATE_CLASSIFIER}'
            else:
                continue
        elif is_excluded and not has_private:
            # Add the classifier.
            classifiers.append(_PRIVATE_CLASSIFIER)
            action = f'{pkg.name}: added {_PRIVATE_CLASSIFIER}'
        elif not is_excluded and has_private:
            # Remove the classifier.
            to_remove = [
                i for i, c in enumerate(classifiers) if isinstance(c, str) and 'Private' in c and 'Do Not Upload' in c
            ]
            for i in reversed(to_remove):
                del classifiers[i]
            action = f'{pkg.name}: removed {_PRIVATE_CLASSIFIER}'
        else:
            continue

        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_classifier', action=action, path=str(pkg.manifest_path))
        else:
            logger.info('fix_classifier_dry_run', action=action, path=str(pkg.manifest_path))

    return changes


def fix_readme_field(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add ``readme = "README.md"`` to publishable packages missing it.

    Only fixes packages that have a ``README.md`` file on disk but
    don't declare it in ``[project]``.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        readme_path = pkg.path / 'README.md'
        if not readme_path.exists():
            continue

        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception as exc:
            logger.warning('fix_readme_field_parse_error', path=str(pkg.manifest_path), error=str(exc))
            continue

        project = doc.get('project')
        if project is None:
            continue

        if 'readme' in project and project['readme']:
            continue

        project['readme'] = 'README.md'
        action = f'{pkg.name}: added readme = "README.md"'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_readme_field', action=action, path=str(pkg.manifest_path))

    return changes


def fix_changelog_url(
    packages: list[Package],
    *,
    repo_owner: str = '',
    repo_name: str = '',
    dry_run: bool = False,
) -> list[str]:
    """Add a ``Changelog`` entry to ``[project.urls]`` for publishable packages.

    Uses the repo coordinates to construct a URL pointing to the
    package's ``CHANGELOG.md`` on the default branch.

    Args:
        packages: All discovered workspace packages.
        repo_owner: Repository owner (e.g. ``"firebase"``).
        repo_name: Repository name (e.g. ``"genkit"``).
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue

        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception as exc:
            logger.warning('fix_changelog_url_parse_error', path=str(pkg.manifest_path), error=str(exc))
            continue

        project = doc.get('project')
        if project is None:
            continue

        urls = project.get('urls')
        if urls is not None:
            has_changelog = any(key.lower() == 'changelog' for key in urls)
            if has_changelog:
                continue

        if urls is None:
            urls = tomlkit.table()
            project['urls'] = urls

        if repo_owner and repo_name:
            changelog_url = f'https://github.com/{repo_owner}/{repo_name}/blob/main/{pkg.path.name}/CHANGELOG.md'
        else:
            changelog_url = 'CHANGELOG.md'

        urls['Changelog'] = changelog_url
        action = f'{pkg.name}: added Changelog URL to [project.urls]'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_changelog_url', action=action, path=str(pkg.manifest_path))

    return changes


def fix_namespace_init(
    packages: list[Package],
    namespace_dirs: list[str],
    *,
    plugin_dirs: list[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Delete accidental ``__init__.py`` files in PEP 420 namespace directories.

    Namespace packages must NOT have ``__init__.py`` in intermediate
    namespace directories. This fixer removes them.

    If ``plugin_dirs`` is provided, only packages whose parent directory
    name is in that set are checked. Otherwise all packages are checked.

    Args:
        packages: All discovered workspace packages.
        namespace_dirs: Relative paths (from ``src/``) of namespace
            directories that must not contain ``__init__.py``.
        plugin_dirs: Parent directory names to restrict the check to.
            If empty or ``None``, all packages are checked.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    if not namespace_dirs:
        return changes

    _plugin_dirs = frozenset(plugin_dirs) if plugin_dirs else frozenset()

    for pkg in packages:
        if _plugin_dirs and pkg.path.parent.name not in _plugin_dirs:
            continue
        src_dir = pkg.path / 'src'
        if not src_dir.exists():
            continue

        for ns_dir in namespace_dirs:
            init_file = src_dir / ns_dir / '__init__.py'
            if init_file.exists():
                relative = init_file.relative_to(pkg.path)
                action = f'{pkg.name}: deleted {relative}'
                changes.append(action)
                if not dry_run:
                    init_file.unlink()
                    logger.warning('fix_namespace_init', action=action, path=str(init_file))

    return changes


def fix_type_markers(
    packages: list[Package],
    *,
    library_dirs: list[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Create missing ``py.typed`` PEP 561 marker files.

    If ``library_dirs`` is provided, only creates markers for publishable
    packages whose parent directory name is in that set. Otherwise creates
    markers for all publishable packages with a ``src/`` directory.

    Args:
        packages: All discovered workspace packages.
        library_dirs: Parent directory names to restrict the check to.
            If empty or ``None``, all publishable packages are checked.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []
    _library_dirs = frozenset(library_dirs) if library_dirs else frozenset()

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        if _library_dirs and pkg.path.parent.name not in _library_dirs:
            continue
        src_dir = pkg.path / 'src'
        if not src_dir.exists():
            continue
        py_typed_files = list(src_dir.rglob('py.typed'))
        if py_typed_files:
            continue

        # Find the first top-level package directory under src/.
        top_level_dirs = [d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]
        if not top_level_dirs:
            continue

        marker_path = top_level_dirs[0] / 'py.typed'
        action = f'{pkg.name}: created {marker_path.relative_to(pkg.path)}'
        changes.append(action)
        if not dry_run:
            marker_path.write_text('', encoding='utf-8')
            logger.warning('fix_type_markers', action=action, path=str(marker_path))

    return changes


def fix_deprecated_classifiers(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Replace deprecated trove classifiers with their modern equivalents.

    Deprecated classifiers with a known replacement are swapped in-place.
    Deprecated classifiers with no replacement are removed.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        classifiers = project.get('classifiers')
        if not isinstance(classifiers, list):
            continue

        modified = False
        i = 0
        while i < len(classifiers):
            clf = classifiers[i]
            if not isinstance(clf, str):
                i += 1
                continue
            if clf in DEPRECATED_CLASSIFIERS:
                replacement = DEPRECATED_CLASSIFIERS[clf]
                if replacement:
                    action = f'{pkg.name}: replaced {clf!r} → {replacement!r}'
                    classifiers[i] = replacement
                else:
                    action = f'{pkg.name}: removed deprecated {clf!r}'
                    del classifiers[i]
                    i -= 1
                changes.append(action)
                modified = True
            i += 1

        if modified and not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_deprecated_classifiers', package=pkg.name)

    return changes


def fix_duplicate_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove duplicate entries from ``[project].dependencies``.

    When the same package name (after PEP 503 normalisation) appears more
    than once, only the **first** occurrence is kept.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        deps = project.get('dependencies')
        if not isinstance(deps, list):
            continue

        seen: set[str] = set()
        to_remove: list[int] = []
        for i, dep in enumerate(deps):
            if not isinstance(dep, str):
                continue
            match = _DEP_NAME_RE.match(dep.strip())
            if not match:
                continue
            name = match.group(1).lower().replace('-', '_').replace('.', '_')
            if name in seen:
                to_remove.append(i)
            else:
                seen.add(name)

        if not to_remove:
            continue

        removed_names = []
        for i in reversed(to_remove):
            removed_names.append(deps[i].strip())
            del deps[i]

        action = f'{pkg.name}: removed {len(to_remove)} duplicate dep(s): {", ".join(reversed(removed_names))}'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_duplicate_dependencies', package=pkg.name, removed=len(to_remove))

    return changes


def fix_requires_python(
    packages: list[Package],
    *,
    default: str = '>=3.10',
    dry_run: bool = False,
) -> list[str]:
    """Add ``requires-python`` to packages that are missing it.

    The value is inferred from existing Python version classifiers when
    possible, otherwise ``default`` is used.

    Args:
        packages: All discovered workspace packages.
        default: Fallback ``requires-python`` value when no classifiers
            provide a hint.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        if project.get('requires-python'):
            continue

        # Try to infer from classifiers.
        inferred = default
        classifiers = project.get('classifiers')
        if isinstance(classifiers, list):
            versions: list[str] = []
            for clf in classifiers:
                if isinstance(clf, str) and clf.startswith('Programming Language :: Python :: '):
                    ver = clf.rsplit(' :: ', 1)[-1]
                    # Only consider major.minor versions like "3.10".
                    if '.' in ver:
                        versions.append(ver)
            if versions:
                versions.sort(key=lambda v: tuple(int(x) for x in v.split('.')))
                inferred = f'>={versions[0]}'

        project['requires-python'] = inferred
        action = f'{pkg.name}: added requires-python = "{inferred}"'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_requires_python', package=pkg.name, value=inferred)

    return changes


def fix_build_system(
    packages: list[Package],
    *,
    build_backend: str = 'hatchling.build',
    requires: list[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Add a ``[build-system]`` table to packages that are missing one.

    Args:
        packages: All discovered workspace packages.
        build_backend: The ``build-backend`` value to insert.
        requires: The ``requires`` list.  Defaults to ``["hatchling"]`` when
            *build_backend* is ``"hatchling.build"``, otherwise ``[build_backend]``.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    if requires is None:
        if build_backend == 'hatchling.build':
            requires = ['hatchling']
        else:
            requires = [build_backend.split('.')[0]]

    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        build_system = doc.get('build-system')
        if isinstance(build_system, dict) and 'build-backend' in build_system:
            continue

        if not isinstance(build_system, dict):
            bs = tomlkit.table()
            bs['requires'] = requires
            bs['build-backend'] = build_backend
            doc['build-system'] = bs
            action = f'{pkg.name}: added [build-system] with {build_backend}'
        else:
            build_system['build-backend'] = build_backend
            if 'requires' not in build_system:
                build_system['requires'] = requires
            action = f'{pkg.name}: added build-backend = "{build_backend}"'

        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_build_system', package=pkg.name, backend=build_backend)

    return changes


def fix_version_field(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add ``"version"`` to the ``dynamic`` list for packages missing a version.

    Rather than guessing a version number, this adds ``"version"`` to
    ``[project].dynamic`` so the build backend can supply it.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue

        # Already has a version.
        if project.get('version'):
            continue

        # Already declared as dynamic.
        dynamic = project.get('dynamic')
        if isinstance(dynamic, list) and 'version' in dynamic:
            continue

        if isinstance(dynamic, list):
            dynamic.append('version')
            action = f'{pkg.name}: added "version" to dynamic list'
        else:
            project['dynamic'] = ['version']
            action = f'{pkg.name}: created dynamic = ["version"]'

        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_version_field', package=pkg.name)

    return changes


def fix_readme_content_type(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Fix ``content-type`` in ``[project.readme]`` to match the file extension.

    When the readme is specified as a table with ``file`` and ``content-type``,
    this corrects the content-type to match the actual file extension
    (``.md`` → ``text/markdown``, ``.rst`` → ``text/x-rst``,
    ``.txt`` → ``text/plain``).

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    ext_to_ct: dict[str, str] = {
        '.md': 'text/markdown',
        '.rst': 'text/x-rst',
        '.txt': 'text/plain',
    }

    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue

        readme = project.get('readme')
        if not isinstance(readme, dict):
            continue

        file_val = readme.get('file')
        ct_val = readme.get('content-type')
        if not isinstance(file_val, str) or not isinstance(ct_val, str):
            continue

        ext = Path(file_val).suffix.lower()
        expected_ct = ext_to_ct.get(ext)
        if expected_ct is None or ct_val == expected_ct:
            continue

        readme['content-type'] = expected_ct
        action = f'{pkg.name}: changed content-type from {ct_val!r} to {expected_ct!r}'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_readme_content_type', package=pkg.name, old=ct_val, new=expected_ct)

    return changes


def fix_placeholder_urls(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove placeholder URLs from ``[project.urls]``.

    Entries whose value is empty or contains a known placeholder pattern
    (e.g. ``example.com``, ``TODO``) are deleted from the table.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        urls = project.get('urls')
        if not isinstance(urls, dict):
            continue

        to_remove: list[str] = []
        for key, val in urls.items():
            if not isinstance(val, str):
                continue
            val_lower = val.lower().strip()
            if not val_lower:
                to_remove.append(key)
                continue
            for pattern in _PLACEHOLDER_URL_PATTERNS:
                if pattern.lower() in val_lower:
                    to_remove.append(key)
                    break

        if not to_remove:
            continue

        for key in to_remove:
            del urls[key]

        action = f'{pkg.name}: removed {len(to_remove)} placeholder URL(s): {", ".join(to_remove)}'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_placeholder_urls', package=pkg.name, removed=to_remove)

    return changes


def fix_license_classifier_mismatch(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Fix license classifier to match the detected LICENSE file content.

    When the LICENSE file content indicates a specific license (e.g. Apache,
    MIT) but the classifiers list contains a different license classifier,
    this replaces the mismatched classifier with the correct one.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        classifiers = project.get('classifiers')
        if not isinstance(classifiers, list):
            continue

        # Detect license from file.
        license_file = pkg.path / 'LICENSE'
        if not license_file.is_file():
            continue
        try:
            license_text = license_file.read_text(encoding='utf-8')
        except Exception:  # noqa: S112, BLE001 - best effort
            continue

        detected_classifier: str = ''
        for pattern, classifier in _LICENSE_PATTERNS.items():
            if pattern.lower() in license_text.lower():
                detected_classifier = classifier
                break

        if not detected_classifier:
            continue

        # Find existing license classifiers.
        modified = False
        for i, clf in enumerate(classifiers):
            if not isinstance(clf, str) or not clf.startswith('License ::'):
                continue
            if clf.startswith(detected_classifier):
                # Already correct.
                modified = False
                break
            # Mismatch — replace.
            old_clf = clf
            classifiers[i] = detected_classifier
            action = f'{pkg.name}: replaced {old_clf!r} → {detected_classifier!r}'
            changes.append(action)
            modified = True
            break

        if modified and not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_license_classifier_mismatch', package=pkg.name)

    return changes


def fix_self_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove self-dependencies from ``[project].dependencies``.

    A package that lists itself as a dependency will cause a circular
    install failure.  This fixer removes any such entries.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        deps = project.get('dependencies')
        if not isinstance(deps, list):
            continue

        pkg_norm = pkg.name.lower().replace('-', '_').replace('.', '_')
        to_remove: list[int] = []
        for i, dep in enumerate(deps):
            if not isinstance(dep, str):
                continue
            match = _DEP_NAME_RE.match(dep.strip())
            if not match:
                continue
            dep_name = match.group(1).lower().replace('-', '_').replace('.', '_')
            if dep_name == pkg_norm:
                to_remove.append(i)

        if not to_remove:
            continue

        removed = []
        for i in reversed(to_remove):
            removed.append(deps[i].strip())
            del deps[i]

        action = f'{pkg.name}: removed self-dep(s): {", ".join(reversed(removed))}'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_self_dependencies', package=pkg.name, removed=removed)

    return changes


def fix_typing_classifier(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add missing ``Typing :: Typed`` and ``License :: OSI Approved`` classifiers.

    For publishable packages that already have a ``classifiers`` list,
    this appends:

    - ``"Typing :: Typed"`` — signals PEP 561 inline type stubs.
    - ``"License :: OSI Approved :: Apache Software License"`` — the
      correct OSI classifier (detected from the LICENSE file when
      possible, otherwise defaults to Apache-2.0).

    Only classifiers whose *prefix* is entirely absent are added (e.g.
    if any ``License :: OSI Approved :: …`` classifier already exists,
    no license classifier is inserted).

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        classifiers = project.get('classifiers')
        if not isinstance(classifiers, list):
            continue

        added: list[str] = []

        # --- Typing :: Typed ---
        has_typing = any(isinstance(c, str) and c == 'Typing :: Typed' for c in classifiers)
        if not has_typing:
            classifiers.append('Typing :: Typed')
            added.append('Typing :: Typed')

        # --- License :: OSI Approved ---
        has_license_osi = any(isinstance(c, str) and c.startswith('License :: OSI Approved') for c in classifiers)
        if not has_license_osi:
            # Try to detect from LICENSE file.
            detected = 'License :: OSI Approved :: Apache Software License'
            license_file = pkg.path / 'LICENSE'
            if license_file.is_file():
                try:
                    license_text = license_file.read_text(encoding='utf-8')
                except Exception:  # noqa: S112, BLE001 - best effort
                    license_text = ''
                for pattern, classifier in _LICENSE_PATTERNS.items():
                    if pattern.lower() in license_text.lower():
                        detected = classifier
                        break
            classifiers.append(detected)
            added.append(detected)

        if not added:
            continue

        action = f'{pkg.name}: added {", ".join(added)}'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_typing_classifier', action=action, path=str(pkg.manifest_path))

    return changes


def fix_keywords_and_urls(
    packages: list[Package],
    *,
    repo_owner: str = '',
    repo_name: str = '',
    default_keywords: list[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Add missing ``keywords`` and ``[project.urls]`` to publishable packages.

    **Keywords**: If the ``keywords`` field is absent, inserts a default
    list.  The caller can supply ``default_keywords``; otherwise a
    minimal set (``["python"]``) is used.

    **URLs**: If ``[project.urls]`` is absent or missing standard keys
    (``Homepage``, ``Repository``, ``Bug Tracker``, ``Documentation``),
    the missing entries are added using *repo_owner* / *repo_name* to
    construct GitHub URLs.

    Args:
        packages: All discovered workspace packages.
        repo_owner: Repository owner (e.g. ``"firebase"``).
        repo_name: Repository name (e.g. ``"genkit"``).
        default_keywords: Fallback keywords when none are present.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    if default_keywords is None:
        default_keywords = ['python']

    _standard_url_keys = {
        'Homepage': f'https://github.com/{repo_owner}/{repo_name}' if repo_owner and repo_name else '',
        'Repository': f'https://github.com/{repo_owner}/{repo_name}' if repo_owner and repo_name else '',
        'Bug Tracker': f'https://github.com/{repo_owner}/{repo_name}/issues' if repo_owner and repo_name else '',
    }

    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.manifest_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:  # noqa: S112 - intentional skip on parse failure
            continue

        project = doc.get('project')
        if not isinstance(project, dict):
            continue

        parts: list[str] = []

        # --- keywords ---
        if 'keywords' not in project or not project['keywords']:
            project['keywords'] = default_keywords
            parts.append(f'added keywords {default_keywords}')

        # --- project.urls ---
        urls = project.get('urls')
        if urls is None:
            urls = tomlkit.table()
            project['urls'] = urls

        if isinstance(urls, dict):
            for key, default_url in _standard_url_keys.items():
                if not default_url:
                    continue
                # Case-insensitive check for existing key.
                has_key = any(k.lower() == key.lower() for k in urls)
                if not has_key:
                    urls[key] = default_url
                    parts.append(f'added urls.{key}')

        if not parts:
            continue

        action = f'{pkg.name}: {"; ".join(parts)}'
        changes.append(action)
        if not dry_run:
            pkg.manifest_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
            logger.warning('fix_keywords_and_urls', action=action, path=str(pkg.manifest_path))

    return changes
