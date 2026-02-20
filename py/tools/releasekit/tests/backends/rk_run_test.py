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

"""Tests for releasekit.backends._run module."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from releasekit.backends._run import (
    CalledProcessError,
    CommandResult,
    TimeoutExpired,
    run_command,
)
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_ok_on_zero_returncode(self) -> None:
        """Ok should be True when return_code is 0."""
        result = CommandResult(command=['echo'], return_code=0)
        assert result.ok is True

    def test_not_ok_on_nonzero_returncode(self) -> None:
        """Ok should be False when return_code is non-zero."""
        result = CommandResult(command=['false'], return_code=1)
        assert result.ok is False

    def test_ok_on_dry_run(self) -> None:
        """Ok should be True for dry-run results."""
        result = CommandResult(command=['rm', '-rf', '/'], return_code=0, dry_run=True)
        assert result.ok is True

    def test_command_str(self) -> None:
        """command_str should join command list with spaces."""
        result = CommandResult(command=['git', 'commit', '-m', 'test'], return_code=0)
        assert result.command_str == 'git commit -m test'

    def test_frozen(self) -> None:
        """CommandResult should be immutable."""
        assert dataclasses.is_dataclass(CommandResult)
        params = {f.name for f in dataclasses.fields(CommandResult)}
        assert 'return_code' in params
        # Verify assignment raises: frozen(True) means __setattr__ raises.
        result = CommandResult(command=['echo'], return_code=0)
        raised = False
        try:
            result.__setattr__('return_code', 1)
        except AttributeError:
            raised = True
        assert raised, 'CommandResult should be frozen'


class TestRunCommand:
    """Tests for run_command()."""

    def test_successful_command(self) -> None:
        """Should capture stdout from a successful command."""
        result = run_command(['echo', 'hello'])
        assert result.ok
        assert result.stdout.strip() == 'hello'
        assert result.duration > 0

    def test_failed_command(self) -> None:
        """Should capture non-zero return code without raising."""
        result = run_command(['false'])
        assert not result.ok
        assert result.return_code != 0

    def test_check_raises_on_failure(self) -> None:
        """check=True should raise CalledProcessError on failure."""
        with pytest.raises(CalledProcessError):
            run_command(['false'], check=True)

    def test_dry_run_does_not_execute(self) -> None:
        """dry_run should not actually execute the command."""
        result = run_command(['rm', '-rf', '/nonexistent'], dry_run=True)
        assert result.ok
        assert result.dry_run
        assert result.duration == 0.0

    def test_cwd(self, tmp_path: Path) -> None:
        """Should execute in the specified working directory."""
        result = run_command(['pwd'], cwd=tmp_path)
        assert result.ok
        assert str(tmp_path) in result.stdout

    def test_env_override(self) -> None:
        """Should merge env overrides with current environment."""
        result = run_command(
            ['printenv', 'RELEASEKIT_TEST_VAR'],
            env={'RELEASEKIT_TEST_VAR': 'hello'},
        )
        assert result.ok
        assert result.stdout.strip() == 'hello'

    def test_timeout(self) -> None:
        """Should raise TimeoutExpired for slow commands."""
        with pytest.raises(TimeoutExpired):
            run_command(['sleep', '10'], timeout=1)
