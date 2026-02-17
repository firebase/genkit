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

"""Tests for releasekit.doctor — release state consistency checker."""

from __future__ import annotations

from pathlib import Path as FilePath

import pytest
from releasekit.config import ReleaseConfig, WorkspaceConfig
from releasekit.doctor import (
    DiagnosticResult,
    DoctorReport,
    Severity,
    run_doctor,
)
from releasekit.workspace import Package
from tests._fakes import FakeForge, FakeVCS


def _ws_config(
    label: str = 'py',
    ecosystem: str = 'python',
    tag_format: str = '{name}@{version}',
) -> WorkspaceConfig:
    """Ws config."""
    return WorkspaceConfig(label=label, ecosystem=ecosystem, tag_format=tag_format)


def _config(default_branch: str = 'main') -> ReleaseConfig:
    """Config."""
    return ReleaseConfig(default_branch=default_branch)


def _pkg(name: str, version: str) -> Package:
    """Pkg."""
    return Package(name=name, version=version, path=FilePath(name), manifest_path=FilePath(name) / 'pyproject.toml')


class TestDoctorReport:
    """Tests for DoctorReport dataclass."""

    def test_empty_report_is_ok(self) -> None:
        """Empty report is OK."""
        report = DoctorReport()
        assert report.ok
        assert report.passed == []
        assert report.warnings == []
        assert report.failures == []

    def test_add_pass(self) -> None:
        """Adding a PASS result."""
        report = DoctorReport()
        report.add('test', Severity.PASS, 'All good.')
        assert len(report.passed) == 1
        assert report.ok

    def test_add_warning(self) -> None:
        """Adding a WARN result."""
        report = DoctorReport()
        report.add('test', Severity.WARN, 'Something off.', hint='Fix it.')
        assert len(report.warnings) == 1
        assert report.ok  # warnings don't fail

    def test_add_failure(self) -> None:
        """Adding a FAIL result."""
        report = DoctorReport()
        report.add('test', Severity.FAIL, 'Broken.')
        assert len(report.failures) == 1
        assert not report.ok

    def test_mixed_results(self) -> None:
        """Mixed PASS/WARN/FAIL results."""
        report = DoctorReport()
        report.add('a', Severity.PASS, 'ok')
        report.add('b', Severity.WARN, 'meh')
        report.add('c', Severity.FAIL, 'bad')
        assert len(report.results) == 3
        assert len(report.passed) == 1
        assert len(report.warnings) == 1
        assert len(report.failures) == 1
        assert not report.ok


class TestDiagnosticResult:
    """Tests for DiagnosticResult dataclass."""

    def test_fields(self) -> None:
        """All fields are accessible."""
        r = DiagnosticResult(name='test', severity=Severity.PASS, message='ok', hint='none')
        assert r.name == 'test'
        assert r.severity == Severity.PASS
        assert r.message == 'ok'
        assert r.hint == 'none'

    def test_default_hint(self) -> None:
        """Default hint is empty string."""
        r = DiagnosticResult(name='test', severity=Severity.WARN, message='warn')
        assert r.hint == ''


class TestSeverity:
    """Tests for Severity enum."""

    def test_values(self) -> None:
        """Severity enum values."""
        assert Severity.PASS.value == 'pass'
        assert Severity.WARN.value == 'warn'
        assert Severity.FAIL.value == 'fail'


class TestCheckConfig:
    """Tests for _check_config via run_doctor."""

    @pytest.mark.asyncio
    async def test_valid_config(self) -> None:
        """Valid config passes."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        config_results = [r for r in report.results if r.name == 'config']
        assert any(r.severity == Severity.PASS for r in config_results)

    @pytest.mark.asyncio
    async def test_missing_label(self) -> None:
        """Missing label fails."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=None,
            config=_config(),
            ws_config=_ws_config(label=''),
        )
        config_results = [r for r in report.results if r.name == 'config']
        assert any(r.severity == Severity.FAIL for r in config_results)

    @pytest.mark.asyncio
    async def test_missing_ecosystem(self) -> None:
        """Missing ecosystem fails."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=None,
            config=_config(),
            ws_config=_ws_config(ecosystem=''),
        )
        config_results = [r for r in report.results if r.name == 'config']
        assert any(r.severity == Severity.FAIL for r in config_results)

    @pytest.mark.asyncio
    async def test_missing_tag_format(self) -> None:
        """Missing tag format warns."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=None,
            config=_config(),
            ws_config=_ws_config(tag_format=''),
        )
        config_results = [r for r in report.results if r.name == 'config']
        assert any(r.severity == Severity.WARN for r in config_results)


class TestCheckTagAlignment:
    """Tests for _check_tag_alignment via run_doctor."""

    @pytest.mark.asyncio
    async def test_all_tags_present(self) -> None:
        """All expected tags present passes."""
        pkgs = [_pkg('genkit', '0.5.0'), _pkg('plugin-a', '0.3.0')]
        vcs = FakeVCS(tags={'genkit@0.5.0', 'plugin-a@0.3.0'})
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        tag_results = [r for r in report.results if r.name == 'tag_alignment']
        assert any(r.severity == Severity.PASS for r in tag_results)

    @pytest.mark.asyncio
    async def test_missing_tags(self) -> None:
        """Missing tags warns."""
        pkgs = [_pkg('genkit', '0.5.0'), _pkg('plugin-a', '0.3.0')]
        vcs = FakeVCS(tags={'genkit@0.5.0'})  # plugin-a tag missing
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        tag_results = [r for r in report.results if r.name == 'tag_alignment']
        assert any(r.severity == Severity.WARN for r in tag_results)

    @pytest.mark.asyncio
    async def test_many_missing_tags_truncated(self) -> None:
        """Many missing tags are truncated in message."""
        pkgs = [_pkg(f'pkg-{i}', '1.0.0') for i in range(10)]
        vcs = FakeVCS(tags=set())
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        tag_results = [r for r in report.results if r.name == 'tag_alignment']
        warn = next(r for r in tag_results if r.severity == Severity.WARN)
        assert '+5 more' in warn.message


class TestCheckOrphanedTags:
    """Tests for _check_orphaned_tags via run_doctor."""

    @pytest.mark.asyncio
    async def test_no_orphans(self) -> None:
        """No orphaned tags passes."""
        pkgs = [_pkg('genkit', '0.5.0')]
        vcs = FakeVCS(tags={'genkit@0.5.0'})
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(label='py'),
        )
        orphan_results = [r for r in report.results if r.name == 'orphaned_tags']
        assert any(r.severity == Severity.PASS for r in orphan_results)

    @pytest.mark.asyncio
    async def test_orphaned_tags_detected(self) -> None:
        """Orphaned tags are detected."""
        pkgs = [_pkg('genkit', '0.5.0')]
        vcs = FakeVCS(tags={'genkit@0.5.0', 'py/v0.4.0'})
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(label='py'),
        )
        orphan_results = [r for r in report.results if r.name == 'orphaned_tags']
        assert any(r.severity == Severity.WARN for r in orphan_results)


class TestCheckVCSState:
    """Tests for _check_vcs_state via run_doctor."""

    @pytest.mark.asyncio
    async def test_clean_full_clone(self) -> None:
        """Clean full clone passes both checks."""
        vcs = FakeVCS(clean=True, shallow=False)
        report = await run_doctor(
            packages=[],
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        wt = [r for r in report.results if r.name == 'worktree']
        assert any(r.severity == Severity.PASS for r in wt)
        sc = [r for r in report.results if r.name == 'shallow_clone']
        assert any(r.severity == Severity.PASS for r in sc)

    @pytest.mark.asyncio
    async def test_dirty_worktree(self) -> None:
        """Dirty worktree warns."""
        vcs = FakeVCS(clean=False)
        report = await run_doctor(
            packages=[],
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        wt = [r for r in report.results if r.name == 'worktree']
        assert any(r.severity == Severity.WARN for r in wt)

    @pytest.mark.asyncio
    async def test_shallow_clone(self) -> None:
        """Shallow clone warns."""
        vcs = FakeVCS(shallow=True)
        report = await run_doctor(
            packages=[],
            vcs=vcs,
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        sc = [r for r in report.results if r.name == 'shallow_clone']
        assert any(r.severity == Severity.WARN for r in sc)


class TestCheckForge:
    """Tests for _check_forge via run_doctor."""

    @pytest.mark.asyncio
    async def test_forge_available(self) -> None:
        """Available forge passes."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=FakeForge(available=True),
            config=_config(),
            ws_config=_ws_config(),
        )
        forge_results = [r for r in report.results if r.name == 'forge']
        assert any(r.severity == Severity.PASS for r in forge_results)

    @pytest.mark.asyncio
    async def test_forge_unavailable(self) -> None:
        """Unavailable forge warns."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=FakeForge(available=False),
            config=_config(),
            ws_config=_ws_config(),
        )
        forge_results = [r for r in report.results if r.name == 'forge']
        assert any(r.severity == Severity.WARN for r in forge_results)

    @pytest.mark.asyncio
    async def test_no_forge(self) -> None:
        """No forge backend warns."""
        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=None,
            config=_config(),
            ws_config=_ws_config(),
        )
        forge_results = [r for r in report.results if r.name == 'forge']
        assert any(r.severity == Severity.WARN for r in forge_results)
        assert any('No forge backend' in r.message for r in forge_results)

    @pytest.mark.asyncio
    async def test_forge_exception(self) -> None:
        """Forge exception is caught and reported."""

        class BrokenForge(FakeForge):
            async def is_available(self) -> bool:
                """Is available."""
                raise RuntimeError('connection failed')

        report = await run_doctor(
            packages=[],
            vcs=FakeVCS(),
            forge=BrokenForge(),
            config=_config(),
            ws_config=_ws_config(),
        )
        forge_results = [r for r in report.results if r.name == 'forge']
        assert any(r.severity == Severity.WARN for r in forge_results)
        assert any('connection failed' in r.message for r in forge_results)


class TestCheckDefaultBranch:
    """Tests for _check_default_branch via run_doctor."""

    @pytest.mark.asyncio
    async def test_on_default_branch(self) -> None:
        """On default branch passes."""
        vcs = FakeVCS(current_branch='main')
        report = await run_doctor(
            packages=[],
            vcs=vcs,
            forge=None,
            config=ReleaseConfig(),
            ws_config=_ws_config(),
        )
        assert report.ok

    @pytest.mark.asyncio
    async def test_not_on_default_branch(self) -> None:
        """Not on default branch warns."""
        vcs = FakeVCS(current_branch='feature/test')
        report = await run_doctor(
            packages=[],
            vcs=vcs,
            forge=None,
            config=ReleaseConfig(default_branch='main'),
            ws_config=_ws_config(),
        )
        db = [r for r in report.results if r.name == 'default_branch']
        assert any(r.severity == Severity.WARN for r in db)

    @pytest.mark.asyncio
    async def test_default_branch_fallback(self) -> None:
        """Empty config default_branch falls back to VCS."""
        vcs = FakeVCS(current_branch='main')
        report = await run_doctor(
            packages=[],
            vcs=vcs,
            forge=None,
            config=ReleaseConfig(default_branch=''),
            ws_config=_ws_config(),
        )
        db = [r for r in report.results if r.name == 'default_branch']
        assert any(r.severity == Severity.PASS for r in db)


class TestRunDoctor:
    """Integration tests for run_doctor."""

    @pytest.mark.asyncio
    async def test_full_healthy_workspace(self) -> None:
        """Fully healthy workspace has no failures."""
        pkgs = [_pkg('genkit', '0.5.0'), _pkg('plugin-a', '0.3.0')]
        vcs = FakeVCS(
            tags={'genkit@0.5.0', 'plugin-a@0.3.0'},
            clean=True,
            shallow=False,
            current_branch='main',
        )
        forge = FakeForge(available=True)
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=forge,
            config=_config(),
            ws_config=_ws_config(),
        )
        assert report.ok
        assert len(report.failures) == 0
        assert len(report.results) >= 6  # config, tag_alignment, orphaned_tags, worktree, shallow, forge, branch

    @pytest.mark.asyncio
    async def test_full_unhealthy_workspace(self) -> None:
        """Unhealthy workspace has multiple warnings."""
        pkgs = [_pkg('genkit', '0.5.0')]
        vcs = FakeVCS(
            tags=set(),
            clean=False,
            shallow=True,
            current_branch='feature/x',
        )
        report = await run_doctor(
            packages=pkgs,
            vcs=vcs,
            forge=FakeForge(available=False),
            config=_config(),
            ws_config=_ws_config(),
        )
        assert report.ok  # no FAIL results, only WARNs
        assert len(report.warnings) >= 4
