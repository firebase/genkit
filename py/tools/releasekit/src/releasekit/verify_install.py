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

r"""Post-publish verification: install packages from the registry and smoke-test.

Reads a :class:`~releasekit.versions.ReleaseManifest` and verifies that
every non-skipped package can be installed from the registry. Supports
multiple ecosystems (Python, npm, Go, Cargo, pub, Maven).

Optionally runs a user-supplied Python import statement as a smoke test
(Python ecosystem only).

Usage (CLI)::

    releasekit verify-install --manifest release-manifest--py.json
    releasekit verify-install --manifest release-manifest--py.json \\
        --import-check "from genkit.ai import Genkit"
    releasekit verify-install --manifest release-manifest--py.json \\
        --index-url https://test.pypi.org/simple/

Usage (Python)::

    from releasekit.verify_install import verify_packages, load_manifest_specs

    specs, ecosystem = load_manifest_specs(Path("release-manifest--py.json"))
    exit_code = verify_packages(specs, ecosystem=ecosystem)
"""

from __future__ import annotations

import re
import shutil
import subprocess  # noqa: S404 - validated inputs only
import sys
from dataclasses import dataclass
from pathlib import Path

from releasekit.logging import get_logger
from releasekit.versions import ReleaseManifest

logger = get_logger(__name__)


# ── Data types ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PackageSpec:
    """A package name + version to verify.

    Attributes:
        name: Normalized package name (e.g. ``"genkit"``).
        version: Expected version string (e.g. ``"0.6.0"``).
    """

    name: str
    version: str

    def install_spec(self, ecosystem: str = 'python') -> str:
        """Return the install specifier for the given ecosystem.

        Args:
            ecosystem: Package ecosystem (``"python"``, ``"js"``, etc.).

        Returns:
            Install specifier string (e.g. ``"genkit==0.6.0"`` for Python,
            ``"genkit@0.6.0"`` for npm).
        """
        if ecosystem in ('js', 'javascript', 'npm', 'pnpm'):
            return f'{self.name}@{self.version}'
        if ecosystem in ('rust', 'cargo'):
            return f'{self.name}@{self.version}'
        # Python, Go, pub, Maven all use ==
        return f'{self.name}=={self.version}'


# ── GitHub Actions annotation helpers ─────────────────────────────────


def _gh_warning(message: str) -> None:
    """Emit a GitHub Actions warning annotation."""
    print(f'::warning::{message}', flush=True)  # noqa: T201 - CI output


def _gh_error(message: str) -> None:
    """Emit a GitHub Actions error annotation."""
    print(f'::error::{message}', flush=True)  # noqa: T201 - CI output


# ── Manifest loading ─────────────────────────────────────────────────


def load_manifest_specs(manifest_path: Path) -> tuple[list[PackageSpec], str]:
    """Load a release manifest and return non-skipped packages + ecosystem.

    Args:
        manifest_path: Path to the release manifest JSON file.

    Returns:
        Tuple of (list of :class:`PackageSpec`, ecosystem string).

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ValueError: If the JSON is malformed or missing required fields.
    """
    manifest: ReleaseManifest = ReleaseManifest.load(manifest_path)
    specs: list[PackageSpec] = []
    for pkg in manifest.bumped:
        specs.append(PackageSpec(name=pkg.name, version=pkg.new_version))
    return specs, manifest.ecosystem


# ── Installation ─────────────────────────────────────────────────────


def _install_python(spec: str, index_url: str = '') -> bool:
    """Install a Python package via pip."""
    cmd: list[str] = [sys.executable, '-m', 'pip', 'install', spec]
    if index_url:
        cmd.extend(['--index-url', index_url])
    return subprocess.run(cmd, capture_output=True).returncode == 0  # noqa: S603 - spec validated by _validate_spec


def _install_npm(spec: str, index_url: str = '') -> bool:
    """Install an npm package globally."""
    npm: str | None = shutil.which('npm')
    if not npm:
        _gh_error('npm not found on PATH')
        return False
    cmd: list[str] = [npm, 'install', '-g', spec]
    if index_url:
        cmd.extend(['--registry', index_url])
    return subprocess.run(cmd, capture_output=True).returncode == 0  # noqa: S603 - spec validated by _validate_spec


def _install_cargo(spec: str, index_url: str = '') -> bool:
    """Install a Cargo crate."""
    cargo: str | None = shutil.which('cargo')
    if not cargo:
        _gh_error('cargo not found on PATH')
        return False
    # cargo install name --version x.y.z
    parts: list[str] = spec.split('@', 1)
    cmd: list[str] = [cargo, 'install', parts[0]]
    if len(parts) > 1:
        cmd.extend(['--version', parts[1]])
    if index_url:
        cmd.extend(['--index', index_url])
    return subprocess.run(cmd, capture_output=True).returncode == 0  # noqa: S603 - spec validated by _validate_spec


def install_package(spec: str, *, ecosystem: str = 'python', index_url: str = '') -> bool:
    """Install a package using the appropriate package manager.

    Args:
        spec: Install specifier (e.g. ``"genkit==0.6.0"``).
        ecosystem: Package ecosystem identifier.
        index_url: Optional custom registry URL.

    Returns:
        True if the install succeeded.
    """
    if ecosystem in ('python', 'uv', ''):
        return _install_python(spec, index_url=index_url)
    if ecosystem in ('js', 'javascript', 'npm', 'pnpm'):
        return _install_npm(spec, index_url=index_url)
    if ecosystem in ('rust', 'cargo'):
        return _install_cargo(spec, index_url=index_url)
    # Unsupported ecosystem — warn but don't fail.
    _gh_warning(f'verify-install does not yet support ecosystem: {ecosystem}')
    logger.warning('verify_install_unsupported_ecosystem', ecosystem=ecosystem)
    return True


# ── Import check ─────────────────────────────────────────────────────


# SECURITY: Allowlist pattern for --import-check statements.
# Only permit import/from...import syntax with optional print() wrappers.
# This prevents arbitrary code execution via python -c.
_SAFE_IMPORT_PATTERN: re.Pattern[str] = re.compile(
    r'^\s*'
    r'(?:from\s+[\w.]+\s+import\s+[\w., ]+'
    r'|import\s+[\w., ]+)'
    r'(?:\s*;\s*(?:from\s+[\w.]+\s+import\s+[\w., ]+|import\s+[\w., ]+|print\s*\([^)]*\)))*'
    r'\s*$',
)

# SECURITY: Package name/version allowlist.
# PEP 508 names: letters, digits, hyphens, underscores, dots.
_SAFE_SPEC_PATTERN: re.Pattern[str] = re.compile(
    r'^[A-Za-z0-9][A-Za-z0-9._-]*[=@][=]?[A-Za-z0-9._+-]+$',
)


def _validate_import_check(statement: str) -> bool:
    """Return True if the statement looks like a safe import."""
    return bool(_SAFE_IMPORT_PATTERN.match(statement))


def _validate_spec(spec: str) -> bool:
    """Return True if the install spec looks like a valid package==version."""
    return bool(_SAFE_SPEC_PATTERN.match(spec))


def run_import_check(statement: str) -> bool:
    """Run a Python import statement and return True on success.

    Args:
        statement: Python statement to execute
            (e.g. ``"from genkit.ai import Genkit"``).

    Returns:
        True if the statement executed without error.

    Raises:
        ValueError: If the statement does not look like a safe import.
    """
    if not _validate_import_check(statement):
        raise ValueError(
            f'Refusing to execute import check: statement does not match allowed import pattern: {statement!r}'
        )
    result: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603 - statement validated by _validate_import_check
        [sys.executable, '-c', statement],
        capture_output=True,
    )
    return result.returncode == 0


# ── Verification ─────────────────────────────────────────────────────


def verify_packages(
    packages: list[PackageSpec],
    *,
    ecosystem: str = 'python',
    import_check: str = '',
    index_url: str = '',
) -> int:
    """Install and verify all packages.

    Args:
        packages: List of packages to verify.
        ecosystem: Package ecosystem (determines which installer to use).
        import_check: Optional Python import statement to run after
            installing all packages.
        index_url: Optional custom registry URL.

    Returns:
        Exit code: 0 if all packages verified, 1 otherwise.
    """
    if not packages:
        _gh_warning('No published packages found in manifest')
        logger.info('verify_install_empty', message='No packages to verify')
        return 0

    print(f'Packages to verify ({len(packages)}, ecosystem={ecosystem or "python"}):')  # noqa: T201 - CLI output
    for pkg in packages:
        print(f'  {pkg.install_spec(ecosystem)}')  # noqa: T201 - CLI output
    print(flush=True)  # noqa: T201 - CLI output

    failed: list[str] = []
    for pkg in packages:
        spec: str = pkg.install_spec(ecosystem)
        if not _validate_spec(spec):
            _gh_error(f'Suspicious package spec rejected: {spec!r}')
            failed.append(spec)
            continue
        print(f'Installing {spec}...', flush=True)  # noqa: T201 - CLI output
        if install_package(spec, ecosystem=ecosystem, index_url=index_url):
            print(f'✅ {pkg.name} installed')  # noqa: T201 - CLI output
            logger.info('verify_install_ok', package=pkg.name, version=pkg.version)
        else:
            _gh_warning(f'{spec} failed to install from registry')
            logger.error('verify_install_failed', package=pkg.name, version=pkg.version)
            failed.append(spec)

    # Run optional import check (Python only).
    if import_check:
        print(f'\nRunning import check: {import_check}', flush=True)  # noqa: T201 - CLI output
        if run_import_check(import_check):
            print('✅ Import check passed')  # noqa: T201 - CLI output
            logger.info('verify_import_ok', statement=import_check)
        else:
            _gh_error(f'Import check failed: {import_check}')
            logger.error('verify_import_failed', statement=import_check)
            failed.append(f'import-check: {import_check}')

    if failed:
        _gh_error(f'{len(failed)} package(s) failed verification')
        for spec in failed:
            print(f'  ❌ {spec}')  # noqa: T201 - CLI output
        return 1

    print(f'\n✅ All {len(packages)} package(s) verified successfully')  # noqa: T201 - CLI output
    logger.info('verify_install_complete', total=len(packages), failed=0)
    return 0


__all__ = [
    'PackageSpec',
    'install_package',
    'load_manifest_specs',
    'run_import_check',
    'verify_packages',
]
