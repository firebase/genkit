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

r"""Extract license strings from package manifests per ecosystem.

Supports:
    - **Python** — ``pyproject.toml`` (PEP 639 ``license`` field,
      ``license.text``, classifiers).
    - **JavaScript/TypeScript** — ``package.json`` (``license`` field).
    - **Rust** — ``Cargo.toml`` (``package.license`` field).
    - **Go** — ``LICENSE`` file content (no manifest field).
    - **Dart** — ``pubspec.yaml`` (no standard license field; uses
      ``LICENSE`` file).
    - **Java** — ``pom.xml`` (``<licenses><license><name>``).
    - **Fallback** — ``LICENSE`` file content pattern matching.

Each extractor returns a raw license string (which may be an SPDX
expression, a human-readable name, or a PyPI classifier). The caller
should feed the result through :class:`LicenseResolver` to get a
canonical SPDX ID.

Usage::

    from releasekit.checks._license_detect import detect_license

    raw = detect_license(pkg)
    # raw.source == "pyproject.toml"
    # raw.value  == "Apache-2.0"
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from releasekit._types import DetectedLicense as DetectedLicense

__all__ = [
    'DetectedLicense',
    'detect_license',
    'detect_license_from_path',
    'detect_license_with_lookup',
]

# Patterns in LICENSE file content → likely SPDX ID.
# Compiled once at module load for performance (avoids re.compile per call).
_LICENSE_FILE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'Apache License', re.IGNORECASE), 'Apache-2.0'),
    (re.compile(r'MIT License', re.IGNORECASE), 'MIT'),
    (re.compile(r'Permission is hereby granted, free of charge', re.IGNORECASE), 'MIT'),
    (re.compile(r'BSD 3-Clause', re.IGNORECASE), 'BSD-3-Clause'),
    (re.compile(r'BSD 2-Clause', re.IGNORECASE), 'BSD-2-Clause'),
    (re.compile(r'Redistribution and use in source and binary forms', re.IGNORECASE), 'BSD-3-Clause'),
    (re.compile(r'GNU GENERAL PUBLIC LICENSE[\s\S]*?Version 3', re.IGNORECASE), 'GPL-3.0-only'),
    (re.compile(r'GNU GENERAL PUBLIC LICENSE[\s\S]*?Version 2', re.IGNORECASE), 'GPL-2.0-only'),
    (re.compile(r'GNU LESSER GENERAL PUBLIC LICENSE[\s\S]*?Version 3', re.IGNORECASE), 'LGPL-3.0-only'),
    (re.compile(r'GNU LESSER GENERAL PUBLIC LICENSE[\s\S]*?Version 2\.1', re.IGNORECASE), 'LGPL-2.1-only'),
    (re.compile(r'GNU AFFERO GENERAL PUBLIC LICENSE[\s\S]*?Version 3', re.IGNORECASE), 'AGPL-3.0-only'),
    (re.compile(r'Mozilla Public License[\s\S]*?2\.0', re.IGNORECASE), 'MPL-2.0'),
    (re.compile(r'Eclipse Public License[\s\S]*?2\.0', re.IGNORECASE), 'EPL-2.0'),
    (re.compile(r'Eclipse Public License[\s\S]*?1\.0', re.IGNORECASE), 'EPL-1.0'),
    (re.compile(r'ISC License', re.IGNORECASE), 'ISC'),
    (re.compile(r'The Unlicense', re.IGNORECASE), 'Unlicense'),
    (re.compile(r'Boost Software License', re.IGNORECASE), 'BSL-1.0'),
    (re.compile(r'Creative Commons.*CC0', re.IGNORECASE), 'CC0-1.0'),
    (re.compile(r'zlib License', re.IGNORECASE), 'Zlib'),
]


# ── Per-ecosystem extractors ─────────────────────────────────────────


def _detect_python(pkg_path: Path, pkg_name: str) -> DetectedLicense | None:
    """Extract license from ``pyproject.toml``.

    Checks (in order):
        1. ``project.license`` as a string (PEP 639 SPDX expression).
        2. ``project.license.text`` (legacy table form).
        3. ``project.classifiers`` containing ``License ::`` entries.
    """
    pyproject = pkg_path / 'pyproject.toml'
    if not pyproject.is_file():
        return None
    try:
        import sys  # noqa: PLC0415

        if sys.version_info >= (3, 11):
            import tomllib  # noqa: PLC0415
        else:
            import tomli as tomllib  # noqa: PLC0415

        with pyproject.open('rb') as f:
            data = tomllib.load(f)
    except Exception:  # noqa: BLE001
        return None

    project: dict[str, Any] = data.get('project', {})

    # PEP 639: project.license as a plain SPDX string.
    lic = project.get('license')
    if isinstance(lic, str) and lic.strip():
        return DetectedLicense(
            value=lic.strip(),
            source='pyproject.toml [project].license',
            package_name=pkg_name,
        )

    # Legacy: project.license = { text = "..." }
    if isinstance(lic, dict):
        text = lic.get('text', '')
        if isinstance(text, str) and text.strip():
            return DetectedLicense(
                value=text.strip(),
                source='pyproject.toml [project].license.text',
                package_name=pkg_name,
            )

    # Fallback: classifiers.
    classifiers: list[str] = project.get('classifiers', [])
    if isinstance(classifiers, list):
        lic_classifiers = [c for c in classifiers if isinstance(c, str) and c.startswith('License ::')]
        if lic_classifiers:
            return DetectedLicense(
                value=lic_classifiers[0],
                source='pyproject.toml classifier',
                package_name=pkg_name,
            )

    return None


def _detect_js(pkg_path: Path, pkg_name: str) -> DetectedLicense | None:
    """Extract license from ``package.json``."""
    pj = pkg_path / 'package.json'
    if not pj.is_file():
        return None
    try:
        data = json.loads(pj.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None

    # Standard: "license": "MIT" or "license": "MIT OR Apache-2.0"
    lic = data.get('license')
    if isinstance(lic, str) and lic.strip():
        return DetectedLicense(
            value=lic.strip(),
            source='package.json',
            package_name=pkg_name,
        )

    # Legacy: "license": { "type": "MIT" }
    if isinstance(lic, dict):
        lic_type = lic.get('type', '')
        if isinstance(lic_type, str) and lic_type.strip():
            return DetectedLicense(
                value=lic_type.strip(),
                source='package.json license.type',
                package_name=pkg_name,
            )

    # Array form (deprecated): "licenses": [{"type": "MIT"}]
    licenses = data.get('licenses')
    if isinstance(licenses, list) and licenses:
        first = licenses[0]
        if isinstance(first, dict):
            lic_type = first.get('type', '')
            if isinstance(lic_type, str) and lic_type.strip():
                return DetectedLicense(
                    value=lic_type.strip(),
                    source='package.json licenses[0].type',
                    package_name=pkg_name,
                )

    return None


def _detect_rust(pkg_path: Path, pkg_name: str) -> DetectedLicense | None:
    """Extract license from ``Cargo.toml``."""
    cargo = pkg_path / 'Cargo.toml'
    if not cargo.is_file():
        return None
    try:
        import sys  # noqa: PLC0415

        if sys.version_info >= (3, 11):
            import tomllib  # noqa: PLC0415
        else:
            import tomli as tomllib  # noqa: PLC0415

        with cargo.open('rb') as f:
            data = tomllib.load(f)
    except Exception:  # noqa: BLE001
        return None

    package: dict[str, Any] = data.get('package', {})
    lic = package.get('license')
    if isinstance(lic, str) and lic.strip():
        return DetectedLicense(
            value=lic.strip(),
            source='Cargo.toml [package].license',
            package_name=pkg_name,
        )

    return None


def _detect_java(pkg_path: Path, pkg_name: str) -> DetectedLicense | None:
    """Extract license from ``pom.xml``."""
    pom = pkg_path / 'pom.xml'
    if not pom.is_file():
        return None
    try:
        text = pom.read_text(encoding='utf-8')
    except OSError:
        return None

    import xml.etree.ElementTree as ET  # noqa: N817, PLC0415, S405

    try:
        root = ET.fromstring(text)  # noqa: S314
    except ET.ParseError:
        return None

    # Handle Maven namespace if present.
    pom_ns = '{http://maven.apache.org/POM/4.0.0}'
    for ns in (pom_ns, ''):
        licenses_elem = root.find(f'{ns}licenses')
        if licenses_elem is None:
            continue
        license_elem = licenses_elem.find(f'{ns}license')
        if license_elem is None:
            continue
        name_elem = license_elem.find(f'{ns}name')
        if name_elem is not None and name_elem.text:
            return DetectedLicense(
                value=name_elem.text.strip(),
                source='pom.xml',
                package_name=pkg_name,
            )

    return None


def _detect_dart(pkg_path: Path, pkg_name: str) -> DetectedLicense | None:
    """Extract license from ``pubspec.yaml``.

    Dart/Flutter doesn't have a standard license field in pubspec.yaml,
    so we fall through to LICENSE file detection.
    """
    return None


def _detect_license_file(pkg_path: Path, pkg_name: str) -> DetectedLicense | None:
    """Detect license from LICENSE file content via pattern matching."""
    for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE', 'COPYING'):
        lic_file = pkg_path / name
        if not lic_file.is_file():
            continue
        try:
            text = lic_file.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue

        # Only check the first 2000 chars for performance.
        head = text[:2000]
        for compiled_re, spdx_id in _LICENSE_FILE_PATTERNS:
            if compiled_re.search(head):
                return DetectedLicense(
                    value=spdx_id,
                    source=name,
                    package_name=pkg_name,
                )

    return None


# ── Ordered detection pipeline ───────────────────────────────────────

_DETECTORS = [
    _detect_python,
    _detect_js,
    _detect_rust,
    _detect_java,
    _detect_dart,
    _detect_license_file,
]


def detect_license_from_path(
    pkg_path: Path,
    pkg_name: str = '',
) -> DetectedLicense:
    """Detect the license of a package at *pkg_path*.

    Tries each ecosystem extractor in order, falling back to LICENSE
    file content matching.

    Args:
        pkg_path: Path to the package root directory.
        pkg_name: Package name (for diagnostics).

    Returns:
        A :class:`DetectedLicense`. Check ``.found`` to see if
        detection succeeded.
    """
    if not pkg_name:
        pkg_name = pkg_path.name

    for detector in _DETECTORS:
        result = detector(pkg_path, pkg_name)
        if result is not None:
            return result

    return DetectedLicense(value='', source='', package_name=pkg_name)


def detect_license(pkg: object) -> DetectedLicense:
    """Detect the license of a :class:`Package`-like object.

    Expects *pkg* to have ``path`` (:class:`Path`) and ``name``
    (``str``) attributes.

    Args:
        pkg: A package object with ``path`` and ``name``.

    Returns:
        A :class:`DetectedLicense`.
    """
    pkg_path: Path = pkg.path  # type: ignore[attr-defined]  # duck-typed Package
    pkg_name: str = getattr(pkg, 'name', pkg_path.name)
    return detect_license_from_path(pkg_path, pkg_name)


# ── Async detection with registry fallback ───────────────────────────


async def detect_license_with_lookup(
    packages: list[object],
    ecosystem: str,
    *,
    cache_path: Path | None = None,
    concurrency: int = 8,
    max_retries: int = 3,
) -> dict[str, DetectedLicense]:
    """Detect licenses locally, then look up missing ones from registries.

    For each package, tries local manifest/LICENSE detection first.
    Packages that still have no license are batched into async registry
    lookups (npm, PyPI, crates.io, Maven Central, pub.dev, pkg.go.dev)
    with disk-backed caching, retries, and jitter.

    Args:
        packages: List of package-like objects with ``path``, ``name``,
            and ``version`` attributes.
        ecosystem: Ecosystem key (e.g. ``"pnpm"``, ``"cargo"``, ``"uv"``).
        cache_path: Path to the disk cache JSON file. If ``None``, a
            default path under the first package's parent is used.
        concurrency: Maximum concurrent registry requests.
        max_retries: Maximum retry attempts per request (exponential
            backoff + jitter).

    Returns:
        Mapping from package name to :class:`DetectedLicense`.
    """
    from releasekit.checks._license_lookup import (
        LicenseLookupCache,
        LookupRequest,
        lookup_licenses,
    )

    results: dict[str, DetectedLicense] = {}
    needs_lookup: list[object] = []

    # Phase 1: local detection.
    for pkg in packages:
        local = detect_license(pkg)
        pkg_name: str = getattr(pkg, 'name', getattr(pkg, 'path', Path()).name)
        if local.found:
            results[pkg_name] = local
        else:
            needs_lookup.append(pkg)

    if not needs_lookup:
        return results

    # Phase 2: async registry lookup for unresolved packages.
    cache = None
    if cache_path is not None:
        cache = LicenseLookupCache(cache_path)
    elif packages:
        first_path = getattr(packages[0], 'path', None)
        if first_path is not None:
            default_cache = Path(first_path).parent / '.releasekit' / 'license_cache.json'
            cache = LicenseLookupCache(default_cache)

    lookup_reqs: list[LookupRequest] = []
    for pkg in needs_lookup:
        pkg_name = getattr(pkg, 'name', getattr(pkg, 'path', Path()).name)
        pkg_version = getattr(pkg, 'version', '')
        if pkg_version:
            lookup_reqs.append(
                LookupRequest(
                    package=pkg_name,
                    version=str(pkg_version),
                    ecosystem=ecosystem,
                )
            )
        else:
            results[pkg_name] = DetectedLicense(
                value='',
                source='',
                package_name=pkg_name,
            )

    if lookup_reqs:
        looked_up = await lookup_licenses(
            lookup_reqs,
            cache=cache,
            concurrency=concurrency,
            max_retries=max_retries,
        )
        for req in lookup_reqs:
            key = f'{req.package}@{req.version}'
            if key in looked_up:
                results[req.package] = looked_up[key]

    return results
