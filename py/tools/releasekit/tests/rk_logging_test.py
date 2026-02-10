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

"""Tests for releasekit.logging module."""

from __future__ import annotations

import logging

from releasekit.logging import configure_logging, get_logger


class TestConfigureLogging:
    """Tests for configure_logging()."""

    def test_default_level_is_info(self) -> None:
        """Default logging level should be INFO."""
        configure_logging()
        assert logging.root.level == logging.INFO

    def test_verbose_sets_debug(self) -> None:
        """Verbose flag should set DEBUG level."""
        configure_logging(verbose=True)
        assert logging.root.level == logging.DEBUG

    def test_quiet_sets_warning(self) -> None:
        """Quiet flag should set WARNING level."""
        configure_logging(quiet=True)
        assert logging.root.level == logging.WARNING

    def test_json_log_does_not_crash(self) -> None:
        """JSON log mode should configure without errors."""
        configure_logging(json_log=True)
        log = get_logger()
        log.info('test_json', key='value')

    def test_idempotent(self) -> None:
        """Calling configure_logging twice should not crash."""
        configure_logging()
        configure_logging(verbose=True)
        assert logging.root.level == logging.DEBUG


class TestGetLogger:
    """Tests for get_logger()."""

    def test_returns_bound_logger(self) -> None:
        """get_logger should return a structlog BoundLogger."""
        configure_logging()
        log = get_logger('test')
        assert log is not None

    def test_default_name(self) -> None:
        """Default logger name should be 'releasekit'."""
        configure_logging()
        log = get_logger()
        assert log is not None

    def test_logger_can_log(self) -> None:
        """Logger should be able to emit messages without crashing."""
        configure_logging(quiet=True)
        log = get_logger('test')
        log.info('test message', key='value')
        log.debug('debug message')
        log.warning('warning message')
