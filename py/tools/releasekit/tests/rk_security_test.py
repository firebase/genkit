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

"""Automated security vulnerability checks for releasekit.

These tests scan the releasekit source tree for common vulnerability
patterns. They run as part of the normal test suite so regressions
are caught immediately in CI.

Checks:
    1. Shell injection: no subprocess calls with shell=True.
    2. Unsafe deserialization: no pickle, yaml.load, eval(), exec().
    3. Hardcoded secrets: no literal tokens/passwords in source.
    4. TLS verification: no verify=False or CERT_NONE.
    5. Temp file cleanup: NamedTemporaryFile(delete=False) always
       wrapped in try/finally for cleanup.
    6. Broad exception swallowing: no bare ``except:`` clauses.
    7. Credential repr safety: forge backends with tokens must
       define __repr__ that redacts credentials.
    8. Atomic file creation: lock files use O_EXCL to prevent TOCTOU.
    9. Log injection: no user-controlled data in structlog keys.
   10. Symlink safety: resolve() before trusting paths.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Root of the releasekit source tree.
_SRC_ROOT = Path(__file__).resolve().parent.parent / 'src' / 'releasekit'

# Collect all Python source files (excluding __pycache__).
_PY_FILES: list[Path] = sorted(_SRC_ROOT.rglob('*.py'))


def _read(path: Path) -> str:
    """Read a file as UTF-8 text."""
    return path.read_text(encoding='utf-8')


def _relpath(path: Path) -> str:
    """Return path relative to src/releasekit for readable output."""
    return str(path.relative_to(_SRC_ROOT))


# ── 1. Shell Injection ──────────────────────────────────────────────


class TestNoShellInjection:
    """Verify no subprocess calls use shell=True."""

    def test_no_shell_true(self) -> None:
        """No Python file passes shell=True to subprocess."""
        violations: list[str] = []
        pattern = re.compile(r'shell\s*=\s*True')
        for path in _PY_FILES:
            content = _read(path)
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line) and not line.strip().startswith('#'):
                    violations.append(f'{_relpath(path)}:{i}: {line.strip()}')
        assert not violations, 'shell=True found (command injection risk):\n' + '\n'.join(violations)


# ── 2. Unsafe Deserialization ───────────────────────────────────────


class TestNoUnsafeDeserialization:
    """Verify no unsafe deserialization functions are used."""

    _PATTERNS = [
        (re.compile(r'\bpickle\b'), 'pickle (arbitrary code execution)'),
        (re.compile(r'\byaml\.load\s*\('), 'yaml.load without SafeLoader'),
        (re.compile(r'\beval\s*\('), 'eval() (arbitrary code execution)'),
        (re.compile(r'\bexec\s*\('), 'exec() (arbitrary code execution)'),
        (re.compile(r'\bcompile\s*\('), 'compile() (code generation)'),
        (re.compile(r'\b__import__\s*\('), '__import__() (dynamic import)'),
    ]

    def test_no_unsafe_deserialize(self) -> None:
        """No Python file uses pickle, yaml.load, eval, or exec."""
        violations: list[str] = []
        for path in _PY_FILES:
            content = _read(path)
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('"""'):
                    continue
                for pattern, desc in self._PATTERNS:
                    if pattern.search(line):
                        # Allow re.compile — it's regex, not code compilation.
                        if desc.startswith('compile') and 're.compile' in line:
                            continue
                        violations.append(f'{_relpath(path)}:{i}: {desc}: {stripped}')
        assert not violations, 'Unsafe deserialization found:\n' + '\n'.join(violations)


# ── 3. Hardcoded Secrets ────────────────────────────────────────────


class TestNoHardcodedSecrets:
    """Verify no hardcoded secrets in source code."""

    _SECRET_PATTERNS = [
        re.compile(r"""(?:password|passwd|secret|token|api_key|apikey)\s*=\s*['"][^'"]{8,}['"]""", re.I),
        re.compile(r'ghp_[A-Za-z0-9]{36}'),  # GitHub PAT
        re.compile(r'gho_[A-Za-z0-9]{36}'),  # GitHub OAuth
        re.compile(r'github_pat_[A-Za-z0-9_]{82}'),  # GitHub fine-grained PAT
        re.compile(r'glpat-[A-Za-z0-9_-]{20,}'),  # GitLab PAT
        re.compile(r'sk-[A-Za-z0-9]{48}'),  # OpenAI-style key
        re.compile(r'AKIA[0-9A-Z]{16}'),  # AWS access key
        re.compile(r'pypi-[A-Za-z0-9_-]{50,}'),  # PyPI token
    ]

    def test_no_hardcoded_secrets(self) -> None:
        """No Python file contains hardcoded secrets or API keys."""
        violations: list[str] = []
        for path in _PY_FILES:
            content = _read(path)
            in_docstring = False
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Track triple-quote docstring regions.
                tq_count = line.count('"""') + line.count("'''")
                if tq_count % 2 == 1:
                    in_docstring = not in_docstring
                if in_docstring or stripped.startswith('#'):
                    continue
                for pattern in self._SECRET_PATTERNS:
                    if pattern.search(line):
                        # Ignore test doubles and empty-string defaults.
                        if "= ''" in line or '= ""' in line:
                            continue
                        # Ignore env var lookups.
                        if 'os.environ' in line or 'getenv' in line:
                            continue
                        violations.append(f'{_relpath(path)}:{i}: {stripped[:120]}')
        assert not violations, 'Possible hardcoded secrets found:\n' + '\n'.join(violations)


# ── 4. TLS Verification ────────────────────────────────────────────


class TestTLSVerification:
    """Verify TLS certificate verification is never disabled."""

    _PATTERNS = [
        (re.compile(r'verify\s*=\s*False'), 'verify=False disables TLS'),
        (re.compile(r'CERT_NONE'), 'CERT_NONE disables certificate checks'),
        (re.compile(r'verify_ssl\s*=\s*False'), 'verify_ssl=False disables TLS'),
    ]

    def test_no_tls_bypass(self) -> None:
        """No Python file disables TLS certificate verification."""
        violations: list[str] = []
        for path in _PY_FILES:
            content = _read(path)
            for i, line in enumerate(content.splitlines(), 1):
                if line.strip().startswith('#'):
                    continue
                for pattern, desc in self._PATTERNS:
                    if pattern.search(line):
                        violations.append(f'{_relpath(path)}:{i}: {desc}: {line.strip()}')
        assert not violations, 'TLS verification disabled:\n' + '\n'.join(violations)


# ── 5. Temp File Cleanup ───────────────────────────────────────────


class TestTempFileCleanup:
    """Verify NamedTemporaryFile(delete=False) is always cleaned up."""

    def test_named_temp_file_has_cleanup(self) -> None:
        """Every NamedTemporaryFile(delete=False) is inside try/finally."""
        violations: list[str] = []
        for path in _PY_FILES:
            content = _read(path)
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if 'NamedTemporaryFile' in line and 'delete=False' in line:
                    # Look for a wrapping try block within 5 lines before.
                    context = '\n'.join(lines[max(0, i - 5) : i + 1])
                    if 'try:' not in context:
                        violations.append(
                            f'{_relpath(path)}:{i + 1}: NamedTemporaryFile(delete=False) without try/finally cleanup'
                        )
        assert not violations, 'Temp file leak risk:\n' + '\n'.join(violations)


# ── 6. Bare Except Clauses ─────────────────────────────────────────


class TestNoBareExcept:
    """Verify no bare ``except:`` clauses that swallow all errors."""

    def test_no_bare_except(self) -> None:
        """No Python file uses bare ``except:`` (without exception type)."""
        violations: list[str] = []
        # Match "except:" but not "except SomeError:" or "except (A, B):"
        pattern = re.compile(r'^\s*except\s*:\s*$')
        for path in _PY_FILES:
            content = _read(path)
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.match(line):
                    violations.append(f'{_relpath(path)}:{i}: {line.strip()}')
        assert not violations, 'Bare except: found (swallows KeyboardInterrupt, SystemExit):\n' + '\n'.join(violations)


# ── 7. Credential Repr Safety ──────────────────────────────────────


class TestCredentialReprSafety:
    """Verify forge backends with tokens define safe __repr__."""

    def test_forge_backends_have_repr(self) -> None:
        """All forge backends that store tokens define __repr__."""
        forge_dir = _SRC_ROOT / 'backends' / 'forge'
        if not forge_dir.exists():
            pytest.skip('No forge backends directory')

        violations: list[str] = []
        for path in sorted(forge_dir.glob('*.py')):
            if path.name.startswith('_') or path.name == '__init__.py':
                continue
            content = _read(path)
            # Check if the file stores credentials.
            has_token = bool(re.search(r'Authorization.*Bearer|BasicAuth|_token|_password', content))
            if not has_token:
                continue
            # Must define __repr__.
            if '__repr__' not in content:
                violations.append(
                    f'{_relpath(path)}: stores credentials but has no __repr__ (token may leak in tracebacks/logs)'
                )
        assert not violations, 'Credential repr safety:\n' + '\n'.join(violations)


# ── 8. Atomic Lock File Creation ───────────────────────────────────


class TestAtomicLockCreation:
    """Verify lock file uses O_EXCL for atomic creation."""

    def test_lock_uses_o_excl(self) -> None:
        """lock.py uses O_CREAT|O_EXCL to prevent TOCTOU races."""
        lock_path = _SRC_ROOT / 'lock.py'
        if not lock_path.exists():
            pytest.skip('No lock.py')

        content = _read(lock_path)
        assert 'O_EXCL' in content, 'lock.py does not use O_EXCL for atomic lock creation (TOCTOU race condition)'
        assert 'O_CREAT' in content, 'lock.py does not use O_CREAT for lock creation'


# ── 9. No HTTP URLs in Runtime Code ────────────────────────────────


class TestNoPlaintextHTTP:
    """Verify no http:// URLs in runtime code (only https://)."""

    def test_no_http_urls(self) -> None:
        """No Python file uses http:// URLs (except license headers)."""
        violations: list[str] = []
        pattern = re.compile(r'http://(?!www\.apache\.org|maven\.apache\.org/POM/|localhost[:/]|adaptivecards\.io/)')
        for path in _PY_FILES:
            content = _read(path)
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                if pattern.search(line):
                    violations.append(f'{_relpath(path)}:{i}: {stripped[:120]}')
        assert not violations, 'Plaintext http:// URLs found (use https://):\n' + '\n'.join(violations)


# ── 10. Atomic State File Writes ───────────────────────────────────


class TestAtomicStateWrites:
    """Verify state files use atomic write (mkstemp + os.replace)."""

    def test_state_uses_atomic_write(self) -> None:
        """state.py uses mkstemp + os.replace for crash-safe writes."""
        state_path = _SRC_ROOT / 'state.py'
        if not state_path.exists():
            pytest.skip('No state.py')

        content = _read(state_path)
        assert 'mkstemp' in content, 'state.py does not use mkstemp for atomic temp file creation'
        assert 'os.replace' in content, 'state.py does not use os.replace for atomic rename'


# ── 11. No Symlink Following Without Resolve ───────────────────────


class TestPathResolution:
    """Verify path-sensitive code calls resolve() before trusting paths."""

    def test_workspace_resolves_paths(self) -> None:
        """workspace.py resolves discovered package paths."""
        ws_path = _SRC_ROOT / 'workspace.py'
        if not ws_path.exists():
            pytest.skip('No workspace.py')

        content = _read(ws_path)
        assert '.resolve()' in content, (
            'workspace.py does not call resolve() on discovered paths (symlink traversal risk)'
        )

    def test_pin_resolves_paths(self) -> None:
        """pin.py resolves pyproject paths before modification."""
        pin_path = _SRC_ROOT / 'pin.py'
        if not pin_path.exists():
            pytest.skip('No pin.py')

        content = _read(pin_path)
        assert '.resolve()' in content, 'pin.py does not call resolve() on pyproject paths (symlink traversal risk)'


# ── 12. CI Workflow Script Injection ──────────────────────────────


# Root of the repository (walk up from tests/ to find .github/).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# GitHub Actions workflow files.
_WORKFLOW_DIR = _REPO_ROOT / '.github' / 'workflows'
_WORKFLOW_FILES: list[Path] = sorted(_WORKFLOW_DIR.glob('releasekit*.yml')) if _WORKFLOW_DIR.exists() else []

# String-type inputs that are vulnerable to script injection when used
# directly in shell `run:` blocks via ${{ inputs.name }}.  Boolean and
# choice inputs are safe because their values are constrained by GitHub.
_STRING_INPUTS_RE = re.compile(
    r"""\$\{\{\s*inputs\.(group|prerelease|concurrency|max_retries)\s*\}\}""",
)


class TestCIWorkflowScriptInjection:
    """Verify CI workflows don't interpolate string inputs into shell scripts.

    GitHub Actions ``${{ inputs.name }}`` with string-type inputs is expanded
    *before* bash parses the script, allowing command injection.  String inputs
    must be passed via ``env:`` blocks and referenced as ``$ENV_VAR`` in shell.

    See: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections
    """

    def test_no_inline_string_inputs_in_run_blocks(self) -> None:
        """No workflow interpolates string-type inputs directly in run: blocks."""
        if not _WORKFLOW_FILES:
            pytest.skip('No releasekit workflow files found')

        violations: list[str] = []
        for wf_path in _WORKFLOW_FILES:
            content = _read(wf_path)
            # Only check inside `run: |` blocks — skip env: sections.
            in_run_block = False
            for line_no, line in enumerate(content.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith('run: |') or stripped.startswith('run: "'):
                    in_run_block = True
                    continue
                if in_run_block and (not stripped or not line.startswith(' ' * 10)):
                    # End of run block (de-indented or empty line at top level).
                    if not stripped.startswith('#') and not line.startswith(' ' * 10):
                        in_run_block = False
                if in_run_block:
                    match = _STRING_INPUTS_RE.search(line)
                    if match:
                        violations.append(
                            f'{wf_path.name}:{line_no}: '
                            f'${{{{ inputs.{match.group(1)} }}}} in run: block '
                            f'(use env var instead)'
                        )

        assert not violations, (
            'CI workflow uses inline ${{ inputs.* }} for string inputs in run: blocks '
            '(script injection risk):\n' + '\n'.join(violations)
        )


# ── 13. Hook Template Safety ──────────────────────────────────────


class TestHookTemplateSafety:
    """Verify hooks.py uses safe command parsing (shlex.split)."""

    def test_hooks_use_shlex_split(self) -> None:
        """hooks.py parses expanded commands with shlex.split (not raw shell)."""
        hooks_path = _SRC_ROOT / 'hooks.py'
        if not hooks_path.exists():
            pytest.skip('No hooks.py')

        content = _read(hooks_path)
        assert 'shlex.split' in content, (
            'hooks.py does not use shlex.split() for command parsing (shell interpretation risk)'
        )

    def test_hooks_use_run_command(self) -> None:
        """hooks.py uses the centralized run_command (not subprocess directly)."""
        hooks_path = _SRC_ROOT / 'hooks.py'
        if not hooks_path.exists():
            pytest.skip('No hooks.py')

        content = _read(hooks_path)
        assert 'run_command' in content, (
            'hooks.py does not use centralized run_command() (bypasses security controls in _run.py)'
        )
        assert 'subprocess.run' not in content, (
            'hooks.py calls subprocess.run() directly instead of run_command() (bypasses security controls in _run.py)'
        )


# ── 14. No os.system() ────────────────────────────────────────────


class TestNoOsSystem:
    """Verify no code uses os.system() (shell=True equivalent)."""

    _OS_SYSTEM_RE = re.compile(r'\bos\.system\s*\(')

    def test_no_os_system(self) -> None:
        """No Python file uses os.system() (implicit shell=True)."""
        violations: list[str] = []
        for pyfile in _PY_FILES:
            content = _read(pyfile)
            for line_no, line in enumerate(content.splitlines(), start=1):
                if self._OS_SYSTEM_RE.search(line):
                    violations.append(f'{_relpath(pyfile)}:{line_no}: {line.strip()}')

        assert not violations, 'os.system() found (uses shell=True internally, command injection risk):\n' + '\n'.join(
            violations
        )
