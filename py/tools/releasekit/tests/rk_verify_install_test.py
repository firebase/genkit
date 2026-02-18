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

"""Tests for verify_install module.

Covers all public and internal functions in verify_install.py:
PackageSpec, install helpers, validation, import checks, and
the verify_packages orchestrator.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from releasekit.verify_install import (
    PackageSpec,
    _install_cargo,
    _install_npm,
    _install_python,
    _validate_import_check,
    _validate_spec,
    install_package,
    run_import_check,
    verify_packages,
)

# ── PackageSpec ──────────────────────────────────────────────────────


class TestPackageSpec:
    """Tests for PackageSpec dataclass and install_spec method."""

    def test_python_spec(self) -> None:
        """Python ecosystem uses == separator."""
        spec = PackageSpec(name='genkit', version='0.6.0')
        assert spec.install_spec('python') == 'genkit==0.6.0'

    def test_python_default(self) -> None:
        """Default ecosystem is python."""
        spec = PackageSpec(name='genkit', version='0.6.0')
        assert spec.install_spec() == 'genkit==0.6.0'

    @pytest.mark.parametrize('ecosystem', ['js', 'javascript', 'npm', 'pnpm'])
    def test_js_spec(self, ecosystem: str) -> None:
        """JS ecosystems use @ separator."""
        spec = PackageSpec(name='genkit', version='1.0.0')
        assert spec.install_spec(ecosystem) == 'genkit@1.0.0'

    @pytest.mark.parametrize('ecosystem', ['rust', 'cargo'])
    def test_cargo_spec(self, ecosystem: str) -> None:
        """Cargo ecosystems use @ separator."""
        spec = PackageSpec(name='genkit', version='0.6.0')
        assert spec.install_spec(ecosystem) == 'genkit@0.6.0'

    def test_go_spec(self) -> None:
        """Go ecosystem uses == separator (default branch)."""
        spec = PackageSpec(name='genkit', version='0.6.0')
        assert spec.install_spec('go') == 'genkit==0.6.0'

    def test_frozen(self) -> None:
        """PackageSpec is immutable."""
        spec = PackageSpec(name='genkit', version='0.6.0')
        with pytest.raises(AttributeError):
            spec.name = 'other'  # type: ignore[misc]


# ── _install_python ──────────────────────────────────────────────────


class TestInstallPython:
    """Tests for _install_python."""

    @patch('releasekit.verify_install.subprocess.run')
    def test_basic_spec(self, mock_run: MagicMock) -> None:
        """Basic spec without index_url."""
        mock_run.return_value.returncode = 0
        assert _install_python('genkit==0.6.0') is True
        cmd = mock_run.call_args[0][0]
        assert 'genkit==0.6.0' in cmd
        assert '--index-url' not in cmd

    @patch('releasekit.verify_install.subprocess.run')
    def test_with_index_url(self, mock_run: MagicMock) -> None:
        """Custom index URL is passed via --index-url."""
        mock_run.return_value.returncode = 0
        assert _install_python('genkit==0.6.0', index_url='https://test.pypi.org/simple/') is True
        cmd = mock_run.call_args[0][0]
        assert '--index-url' in cmd
        idx = cmd.index('--index-url')
        assert cmd[idx + 1] == 'https://test.pypi.org/simple/'

    @patch('releasekit.verify_install.subprocess.run')
    def test_failure_returns_false(self, mock_run: MagicMock) -> None:
        """Non-zero exit code returns False."""
        mock_run.return_value.returncode = 1
        assert _install_python('nonexistent==0.0.0') is False


# ── _install_npm ─────────────────────────────────────────────────────


class TestInstallNpm:
    """Tests for _install_npm."""

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/npm')
    @patch('releasekit.verify_install.subprocess.run')
    def test_basic_spec(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Basic spec without registry."""
        mock_run.return_value.returncode = 0
        assert _install_npm('genkit@1.0.0') is True
        cmd = mock_run.call_args[0][0]
        assert 'genkit@1.0.0' in cmd
        assert '--registry' not in cmd

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/npm')
    @patch('releasekit.verify_install.subprocess.run')
    def test_with_index_url(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Custom registry is passed via --registry."""
        mock_run.return_value.returncode = 0
        assert _install_npm('genkit@1.0.0', index_url='https://npm.pkg.github.com') is True
        cmd = mock_run.call_args[0][0]
        assert '--registry' in cmd
        idx = cmd.index('--registry')
        assert cmd[idx + 1] == 'https://npm.pkg.github.com'

    @patch('releasekit.verify_install.shutil.which', return_value=None)
    def test_npm_not_found(self, _mock_which: MagicMock) -> None:
        """Returns False when npm is not on PATH."""
        assert _install_npm('genkit@1.0.0') is False


# ── _install_cargo ───────────────────────────────────────────────────


class TestInstallCargo:
    """Tests for _install_cargo."""

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/cargo')
    @patch('releasekit.verify_install.subprocess.run')
    def test_basic_spec_no_version(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Spec without version."""
        mock_run.return_value.returncode = 0
        assert _install_cargo('genkit') is True
        cmd = mock_run.call_args[0][0]
        assert cmd == ['/usr/bin/cargo', 'install', 'genkit']

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/cargo')
    @patch('releasekit.verify_install.subprocess.run')
    def test_spec_with_version(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Spec with @version is split into --version flag."""
        mock_run.return_value.returncode = 0
        assert _install_cargo('genkit@0.6.0') is True
        cmd = mock_run.call_args[0][0]
        assert cmd == ['/usr/bin/cargo', 'install', 'genkit', '--version', '0.6.0']

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/cargo')
    @patch('releasekit.verify_install.subprocess.run')
    def test_with_index_url(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Custom index URL is passed via --index (regression test)."""
        mock_run.return_value.returncode = 0
        assert _install_cargo('genkit@0.6.0', index_url='https://my-registry.example.com/index') is True
        cmd = mock_run.call_args[0][0]
        assert '--index' in cmd
        idx = cmd.index('--index')
        assert cmd[idx + 1] == 'https://my-registry.example.com/index'
        assert cmd == [
            '/usr/bin/cargo',
            'install',
            'genkit',
            '--version',
            '0.6.0',
            '--index',
            'https://my-registry.example.com/index',
        ]

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/cargo')
    @patch('releasekit.verify_install.subprocess.run')
    def test_empty_index_url_not_added(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Empty index_url does not add --index flag."""
        mock_run.return_value.returncode = 0
        _install_cargo('genkit@0.6.0', index_url='')
        cmd = mock_run.call_args[0][0]
        assert '--index' not in cmd

    @patch('releasekit.verify_install.shutil.which', return_value=None)
    def test_cargo_not_found(self, _mock_which: MagicMock) -> None:
        """Returns False when cargo is not on PATH."""
        assert _install_cargo('genkit@0.6.0') is False

    @patch('releasekit.verify_install.shutil.which', return_value='/usr/bin/cargo')
    @patch('releasekit.verify_install.subprocess.run')
    def test_failure_returns_false(self, mock_run: MagicMock, _mock_which: MagicMock) -> None:
        """Non-zero exit code returns False."""
        mock_run.return_value.returncode = 1
        assert _install_cargo('genkit@0.6.0') is False


# ── install_package (dispatcher) ─────────────────────────────────────


class TestInstallPackage:
    """Tests for the install_package dispatcher."""

    @patch('releasekit.verify_install._install_python', return_value=True)
    def test_python_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes 'python' to _install_python."""
        assert install_package('genkit==0.6.0', ecosystem='python') is True
        mock_install.assert_called_once_with('genkit==0.6.0', index_url='')

    @patch('releasekit.verify_install._install_python', return_value=True)
    def test_uv_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes 'uv' to _install_python."""
        assert install_package('genkit==0.6.0', ecosystem='uv') is True
        mock_install.assert_called_once()

    @patch('releasekit.verify_install._install_python', return_value=True)
    def test_empty_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes '' (empty) to _install_python."""
        assert install_package('genkit==0.6.0', ecosystem='') is True
        mock_install.assert_called_once()

    @patch('releasekit.verify_install._install_npm', return_value=True)
    def test_js_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes 'js' to _install_npm."""
        assert install_package('genkit@1.0.0', ecosystem='js') is True
        mock_install.assert_called_once()

    @patch('releasekit.verify_install._install_npm', return_value=True)
    def test_pnpm_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes 'pnpm' to _install_npm."""
        assert install_package('genkit@1.0.0', ecosystem='pnpm') is True
        mock_install.assert_called_once()

    @patch('releasekit.verify_install._install_cargo', return_value=True)
    def test_rust_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes 'rust' to _install_cargo."""
        assert install_package('genkit@0.6.0', ecosystem='rust') is True
        mock_install.assert_called_once()

    @patch('releasekit.verify_install._install_cargo', return_value=True)
    def test_cargo_ecosystem(self, mock_install: MagicMock) -> None:
        """Routes 'cargo' to _install_cargo."""
        assert install_package('genkit@0.6.0', ecosystem='cargo') is True
        mock_install.assert_called_once()

    def test_unsupported_ecosystem_returns_true(self) -> None:
        """Unsupported ecosystem warns but returns True."""
        assert install_package('genkit==0.6.0', ecosystem='dart') is True

    @patch('releasekit.verify_install._install_python', return_value=True)
    def test_index_url_forwarded(self, mock_install: MagicMock) -> None:
        """index_url is forwarded to the installer."""
        install_package('genkit==0.6.0', ecosystem='python', index_url='https://test.pypi.org/simple/')
        mock_install.assert_called_once_with('genkit==0.6.0', index_url='https://test.pypi.org/simple/')


# ── Validation ───────────────────────────────────────────────────────


class TestValidateImportCheck:
    """Tests for _validate_import_check."""

    def test_simple_import(self) -> None:
        """Simple import statement is valid."""
        assert _validate_import_check('import genkit') is True

    def test_from_import(self) -> None:
        """from...import statement is valid."""
        assert _validate_import_check('from genkit.ai import Genkit') is True

    def test_multi_import_semicolon(self) -> None:
        """Semicolon-separated imports are valid."""
        assert _validate_import_check('import genkit; import os') is True

    def test_import_with_print(self) -> None:
        """Import followed by print() is valid."""
        assert _validate_import_check('from genkit import ai; print(ai)') is True

    def test_arbitrary_code_rejected(self) -> None:
        """Arbitrary code is rejected."""
        assert _validate_import_check('import os; os.system("rm -rf /")') is False

    def test_empty_string_rejected(self) -> None:
        """Empty string is rejected."""
        assert _validate_import_check('') is False

    def test_shell_command_rejected(self) -> None:
        """Shell commands are rejected."""
        assert _validate_import_check('__import__("os").system("id")') is False


class TestValidateSpec:
    """Tests for _validate_spec."""

    def test_python_spec(self) -> None:
        """Python spec with == is valid."""
        assert _validate_spec('genkit==0.6.0') is True

    def test_npm_spec(self) -> None:
        """Npm spec with @ is valid."""
        assert _validate_spec('genkit@1.0.0') is True

    def test_cargo_spec(self) -> None:
        """Cargo spec with @ is valid."""
        assert _validate_spec('genkit@0.6.0') is True

    def test_prerelease_spec(self) -> None:
        """Prerelease version is valid."""
        assert _validate_spec('genkit==0.6.0a1') is True

    def test_hyphenated_name(self) -> None:
        """Hyphenated package name is valid."""
        assert _validate_spec('my-package==1.0.0') is True

    def test_dotted_name(self) -> None:
        """Dotted package name is valid."""
        assert _validate_spec('my.package==1.0.0') is True

    def test_empty_rejected(self) -> None:
        """Empty string is rejected."""
        assert _validate_spec('') is False

    def test_no_version_rejected(self) -> None:
        """Bare name without version is rejected."""
        assert _validate_spec('genkit') is False

    def test_shell_injection_rejected(self) -> None:
        """Shell injection attempt is rejected."""
        assert _validate_spec('genkit==1.0; rm -rf /') is False


# ── run_import_check ─────────────────────────────────────────────────


class TestRunImportCheck:
    """Tests for run_import_check."""

    @patch('releasekit.verify_install.subprocess.run')
    def test_successful_import(self, mock_run: MagicMock) -> None:
        """Successful import returns True."""
        mock_run.return_value.returncode = 0
        assert run_import_check('import os') is True

    @patch('releasekit.verify_install.subprocess.run')
    def test_failed_import(self, mock_run: MagicMock) -> None:
        """Failed import returns False."""
        mock_run.return_value.returncode = 1
        assert run_import_check('import nonexistent_module') is False

    def test_unsafe_statement_raises(self) -> None:
        """Unsafe statement raises ValueError."""
        with pytest.raises(ValueError, match='Refusing to execute'):
            run_import_check('__import__("os").system("id")')

    @patch('releasekit.verify_install.subprocess.run')
    def test_from_import(self, mock_run: MagicMock) -> None:
        """from...import statement works."""
        mock_run.return_value.returncode = 0
        assert run_import_check('from os.path import join') is True
        cmd = mock_run.call_args[0][0]
        assert cmd[-1] == 'from os.path import join'


# ── verify_packages ──────────────────────────────────────────────────


class TestVerifyPackages:
    """Tests for the verify_packages orchestrator."""

    def test_empty_packages_returns_zero(self) -> None:
        """Empty package list returns 0."""
        assert verify_packages([]) == 0

    @patch('releasekit.verify_install.install_package', return_value=True)
    def test_all_succeed(self, mock_install: MagicMock) -> None:
        """All packages succeed returns 0."""
        pkgs = [
            PackageSpec(name='genkit', version='0.6.0'),
            PackageSpec(name='genkit-tools', version='0.6.0'),
        ]
        assert verify_packages(pkgs, ecosystem='python') == 0
        assert mock_install.call_count == 2

    @patch('releasekit.verify_install.install_package', return_value=False)
    def test_failure_returns_one(self, mock_install: MagicMock) -> None:
        """Failed install returns 1."""
        pkgs = [PackageSpec(name='genkit', version='0.6.0')]
        assert verify_packages(pkgs, ecosystem='python') == 1

    @patch('releasekit.verify_install.install_package', return_value=True)
    @patch('releasekit.verify_install.run_import_check', return_value=True)
    def test_import_check_pass(self, mock_import: MagicMock, mock_install: MagicMock) -> None:
        """Successful import check returns 0."""
        pkgs = [PackageSpec(name='genkit', version='0.6.0')]
        assert verify_packages(pkgs, ecosystem='python', import_check='import genkit') == 0
        mock_import.assert_called_once_with('import genkit')

    @patch('releasekit.verify_install.install_package', return_value=True)
    @patch('releasekit.verify_install.run_import_check', return_value=False)
    def test_import_check_fail(self, mock_import: MagicMock, mock_install: MagicMock) -> None:
        """Failed import check returns 1."""
        pkgs = [PackageSpec(name='genkit', version='0.6.0')]
        assert verify_packages(pkgs, ecosystem='python', import_check='import genkit') == 1

    @patch('releasekit.verify_install.install_package', return_value=True)
    def test_index_url_forwarded(self, mock_install: MagicMock) -> None:
        """index_url is forwarded to install_package."""
        pkgs = [PackageSpec(name='genkit', version='0.6.0')]
        verify_packages(pkgs, ecosystem='python', index_url='https://test.pypi.org/simple/')
        mock_install.assert_called_once_with(
            'genkit==0.6.0',
            ecosystem='python',
            index_url='https://test.pypi.org/simple/',
        )

    def test_invalid_spec_rejected(self) -> None:
        """Package with invalid spec is rejected."""
        pkgs = [PackageSpec(name='genkit; rm -rf /', version='0.6.0')]
        assert verify_packages(pkgs, ecosystem='python') == 1

    @patch('releasekit.verify_install.install_package', side_effect=[True, False])
    def test_partial_failure(self, mock_install: MagicMock) -> None:
        """Mixed results: one pass, one fail returns 1."""
        pkgs = [
            PackageSpec(name='genkit', version='0.6.0'),
            PackageSpec(name='genkit-tools', version='0.6.0'),
        ]
        assert verify_packages(pkgs, ecosystem='python') == 1

    @patch('releasekit.verify_install.install_package', return_value=True)
    def test_no_import_check_skipped(self, mock_install: MagicMock) -> None:
        """Empty import_check is not run."""
        pkgs = [PackageSpec(name='genkit', version='0.6.0')]
        with patch('releasekit.verify_install.run_import_check') as mock_import:
            verify_packages(pkgs, ecosystem='python', import_check='')
            mock_import.assert_not_called()


# ── load_manifest_specs ──────────────────────────────────────────────


class TestLoadManifestSpecs:
    """Tests for load_manifest_specs."""

    def test_loads_bumped_packages(self, tmp_path: Path) -> None:
        """Loads non-skipped packages from a manifest file."""
        from releasekit.verify_install import load_manifest_specs
        from releasekit.versions import PackageVersion, ReleaseManifest

        manifest = ReleaseManifest(
            git_sha='abc123',
            ecosystem='python',
            packages=[
                PackageVersion(
                    name='genkit',
                    old_version='0.5.0',
                    new_version='0.6.0',
                    bump='minor',
                ),
                PackageVersion(
                    name='genkit-tools',
                    old_version='0.5.0',
                    new_version='0.5.0',
                    skipped=True,
                ),
                PackageVersion(
                    name='genkit-plugin-foo',
                    old_version='0.5.0',
                    new_version='0.6.0',
                    bump='minor',
                ),
            ],
        )
        path = tmp_path / 'manifest.json'
        manifest.save(path)

        specs, ecosystem = load_manifest_specs(path)
        assert ecosystem == 'python'
        assert len(specs) == 2
        assert specs[0].name == 'genkit'
        assert specs[0].version == '0.6.0'
        assert specs[1].name == 'genkit-plugin-foo'
        assert specs[1].version == '0.6.0'

    def test_empty_manifest(self, tmp_path: Path) -> None:
        """Empty manifest returns empty list."""
        from releasekit.verify_install import load_manifest_specs
        from releasekit.versions import ReleaseManifest

        manifest = ReleaseManifest(git_sha='abc123', ecosystem='js')
        path = tmp_path / 'manifest.json'
        manifest.save(path)

        specs, ecosystem = load_manifest_specs(path)
        assert ecosystem == 'js'
        assert specs == []

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing manifest file raises OSError."""
        from releasekit.verify_install import load_manifest_specs

        with pytest.raises(OSError):
            load_manifest_specs(tmp_path / 'nonexistent.json')
