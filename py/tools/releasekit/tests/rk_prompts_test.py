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

"""Tests for releasekit.prompts."""

from __future__ import annotations

from releasekit.prompts import SYSTEM_PROMPT, build_user_prompt


class TestSystemPrompt:
    """Tests for the system prompt constant."""

    def test_not_empty(self) -> None:
        """Test not empty."""
        assert len(SYSTEM_PROMPT) > 0

    def test_mentions_json(self) -> None:
        """Test mentions json."""
        assert 'JSON' in SYSTEM_PROMPT

    def test_mentions_breaking_changes(self) -> None:
        """Test mentions breaking changes."""
        assert 'breaking' in SYSTEM_PROMPT.lower()


class TestBuildUserPrompt:
    """Tests for build_user_prompt()."""

    def test_basic_prompt(self) -> None:
        """Test basic prompt."""
        prompt = build_user_prompt(changelog_text='feat: add new plugin')
        assert 'feat: add new plugin' in prompt
        assert 'Summarize' in prompt

    def test_with_context(self) -> None:
        """Test with context."""
        prompt = build_user_prompt(
            changelog_text='fix: resolve bug',
            package_count=5,
            commit_count=42,
            days_since_last=14,
        )
        assert '5 packages changed' in prompt
        assert '42 commits' in prompt
        assert '14 days since last release' in prompt

    def test_no_context(self) -> None:
        """Test no context."""
        prompt = build_user_prompt(changelog_text='chore: update deps')
        assert 'Release changelog' in prompt

    def test_partial_context(self) -> None:
        """Test partial context."""
        prompt = build_user_prompt(
            changelog_text='feat: new feature',
            package_count=3,
        )
        assert '3 packages changed' in prompt
        assert 'commits' not in prompt.split('Context:')[1].split('\n')[0]
