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

"""Tests for releasekit.backends.registry.ChecksumResult and verify_checksum."""

from __future__ import annotations

from releasekit.backends.registry import ChecksumResult


class TestChecksumResult:
    """Tests for ChecksumResult dataclass."""

    def test_all_matched(self) -> None:
        """All files matched yields ok=True."""
        result = ChecksumResult(matched=['a.whl', 'b.tar.gz'])
        if not result.ok:
            raise AssertionError('Expected ok=True when all matched')
        if '2 matched' not in result.summary():
            raise AssertionError(f'Unexpected summary: {result.summary()}')

    def test_mismatch_not_ok(self) -> None:
        """Any mismatched file yields ok=False."""
        result = ChecksumResult(
            matched=['a.whl'],
            mismatched={'b.tar.gz': ('abc', 'def')},
        )
        if result.ok:
            raise AssertionError('Expected ok=False with mismatched files')
        if '1 mismatched' not in result.summary():
            raise AssertionError(f'Unexpected summary: {result.summary()}')

    def test_missing_not_ok(self) -> None:
        """Any missing file yields ok=False."""
        result = ChecksumResult(missing=['c.whl'])
        if result.ok:
            raise AssertionError('Expected ok=False with missing files')
        if '1 missing' not in result.summary():
            raise AssertionError(f'Unexpected summary: {result.summary()}')

    def test_empty_result(self) -> None:
        """Empty result (no files checked) is ok."""
        result = ChecksumResult()
        if not result.ok:
            raise AssertionError('Expected ok=True when empty')
        if result.summary() != 'no files checked':
            raise AssertionError(f'Unexpected summary: {result.summary()}')

    def test_combined_summary(self) -> None:
        """Summary includes matched, mismatched, and missing counts."""
        result = ChecksumResult(
            matched=['a.whl'],
            mismatched={'b.tar.gz': ('abc', 'def')},
            missing=['c.whl'],
        )
        summary = result.summary()
        if '1 matched' not in summary:
            raise AssertionError(f'Missing matched in: {summary}')
        if '1 mismatched' not in summary:
            raise AssertionError(f'Missing mismatched in: {summary}')
        if '1 missing' not in summary:
            raise AssertionError(f'Missing missing in: {summary}')
