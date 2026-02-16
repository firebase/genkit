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

"""Tests for releasekit.announce — release announcement integrations."""

from __future__ import annotations

import pytest
from releasekit.announce import (
    AnnouncementConfig,
    AnnouncementResult,
    _expand_env,
    _render_template,
    resolve_announcement_config,
    send_announcements,
)
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# ---------------------------------------------------------------------------
# _expand_env
# ---------------------------------------------------------------------------


class TestExpandEnv:
    """Tests for _expand_env()."""

    def test_expands_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Expands $VAR_NAME from environment."""
        monkeypatch.setenv('MY_WEBHOOK', 'https://hooks.example.com/abc')
        assert _expand_env('$MY_WEBHOOK') == 'https://hooks.example.com/abc'

    def test_returns_original_if_not_set(self) -> None:
        """Returns original string if env var not set."""
        assert _expand_env('$NONEXISTENT_VAR_12345') == '$NONEXISTENT_VAR_12345'

    def test_plain_url_unchanged(self) -> None:
        """Plain URL is returned unchanged."""
        url = 'https://hooks.slack.com/services/T00/B00/xxx'
        assert _expand_env(url) == url

    def test_dollar_brace_not_expanded(self) -> None:
        """${VAR} format is not expanded (only $VAR)."""
        assert _expand_env('${MY_VAR}') == '${MY_VAR}'


# ---------------------------------------------------------------------------
# _render_template
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    """Tests for _render_template()."""

    def test_basic_template(self) -> None:
        """Basic template with version and packages."""
        result = _render_template(
            'Released ${version}: ${packages}',
            version='1.2.0',
            packages=['genkit', 'genkit-ai'],
        )
        assert result == 'Released 1.2.0: genkit, genkit-ai'

    def test_count_substitution(self) -> None:
        """Count placeholder is substituted."""
        result = _render_template(
            '${count} packages released',
            packages=['a', 'b', 'c'],
        )
        assert result == '3 packages released'

    def test_url_substitution(self) -> None:
        """URL placeholder is substituted."""
        result = _render_template(
            'See ${url}',
            url='https://github.com/example/releases/v1.0',
        )
        assert result == 'See https://github.com/example/releases/v1.0'

    def test_many_packages_truncated(self) -> None:
        """More than 5 packages are truncated."""
        pkgs = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        result = _render_template('${packages}', packages=pkgs)
        assert 'and 2 more' in result

    def test_unknown_placeholder_left_intact(self) -> None:
        """Unknown placeholders are left intact (safe_substitute)."""
        result = _render_template('${unknown} ${version}', version='1.0')
        assert '${unknown}' in result
        assert '1.0' in result

    def test_empty_packages(self) -> None:
        """Empty packages list renders empty string."""
        result = _render_template('${packages}', packages=[])
        assert result == ''


# ---------------------------------------------------------------------------
# AnnouncementResult
# ---------------------------------------------------------------------------


class TestAnnouncementResult:
    """Tests for AnnouncementResult dataclass."""

    def test_ok_when_no_failures(self) -> None:
        """Result is ok when no failures."""
        result = AnnouncementResult(sent=2)
        assert result.ok is True

    def test_not_ok_when_failures(self) -> None:
        """Result is not ok when there are failures."""
        result = AnnouncementResult(sent=1, failed=1, errors=['timeout'])
        assert result.ok is False

    def test_summary(self) -> None:
        """Summary includes sent and failed counts."""
        result = AnnouncementResult(sent=2, failed=1)
        assert '2 sent' in result.summary()
        assert '1 failed' in result.summary()


# ---------------------------------------------------------------------------
# send_announcements
# ---------------------------------------------------------------------------


class TestSendAnnouncements:
    """Tests for send_announcements()."""

    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self) -> None:
        """Disabled config returns empty result."""
        cfg = AnnouncementConfig(enabled=False, slack_webhook='https://example.com')
        result = await send_announcements(cfg, version='1.0.0')
        assert result.sent == 0
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_no_targets_returns_empty(self) -> None:
        """No configured targets returns empty result."""
        cfg = AnnouncementConfig()
        result = await send_announcements(cfg, version='1.0.0')
        assert result.sent == 0

    @pytest.mark.asyncio
    async def test_dry_run_does_not_send(self) -> None:
        """Dry run counts targets but doesn't send."""
        cfg = AnnouncementConfig(slack_webhook='https://hooks.slack.com/test')
        result = await send_announcements(cfg, version='1.0.0', dry_run=True)
        assert result.sent == 1
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_irc_target_counted_in_dry_run(self) -> None:
        """IRC webhook is counted as a target in dry run."""
        cfg = AnnouncementConfig(irc_webhook='https://irc-bridge.example.com/hook')
        result = await send_announcements(cfg, version='1.0.0', dry_run=True)
        assert result.sent == 1
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_all_targets_counted_in_dry_run(self) -> None:
        """All target types are counted in dry run."""
        cfg = AnnouncementConfig(
            slack_webhook='https://slack.example.com',
            discord_webhook='https://discord.example.com',
            irc_webhook='https://irc.example.com',
            custom_webhooks=['https://custom.example.com'],
        )
        result = await send_announcements(cfg, version='1.0.0', dry_run=True)
        assert result.sent == 4


# ---------------------------------------------------------------------------
# resolve_announcement_config
# ---------------------------------------------------------------------------


class TestResolveAnnouncementConfig:
    """Tests for resolve_announcement_config()."""

    def test_no_overrides_returns_base(self) -> None:
        """Base config returned when no overrides exist."""
        base = AnnouncementConfig(slack_webhook='https://slack.example.com')
        result = resolve_announcement_config(base, 'genkit')
        assert result.slack_webhook == 'https://slack.example.com'

    def test_exact_package_override(self) -> None:
        """Exact package name match overrides base fields."""
        override = AnnouncementConfig(
            discord_webhook='https://discord-core.example.com',
            template='Core: ${version}',
        )
        base = AnnouncementConfig(
            slack_webhook='https://slack.example.com',
            template='Default: ${version}',
            overrides={'genkit-core': override},
        )
        result = resolve_announcement_config(base, 'genkit-core')
        assert result.slack_webhook == 'https://slack.example.com'
        assert result.discord_webhook == 'https://discord-core.example.com'
        assert result.template == 'Core: ${version}'

    def test_group_override(self) -> None:
        """Group membership match overrides base fields."""
        override = AnnouncementConfig(
            slack_webhook='https://slack-plugins.example.com',
        )
        base = AnnouncementConfig(
            slack_webhook='https://slack.example.com',
            overrides={'plugins': override},
        )
        groups = {'plugins': ['genkit-plugin-*']}
        result = resolve_announcement_config(base, 'genkit-plugin-foo', groups)
        assert result.slack_webhook == 'https://slack-plugins.example.com'

    def test_package_override_takes_precedence_over_group(self) -> None:
        """Exact package match wins over group match."""
        pkg_override = AnnouncementConfig(irc_webhook='https://irc-pkg.example.com')
        grp_override = AnnouncementConfig(irc_webhook='https://irc-grp.example.com')
        base = AnnouncementConfig(
            overrides={
                'genkit-plugin-foo': pkg_override,
                'plugins': grp_override,
            },
        )
        groups = {'plugins': ['genkit-plugin-*']}
        result = resolve_announcement_config(base, 'genkit-plugin-foo', groups)
        assert result.irc_webhook == 'https://irc-pkg.example.com'

    def test_no_match_returns_base(self) -> None:
        """Unmatched package returns base config."""
        override = AnnouncementConfig(slack_webhook='https://override.example.com')
        base = AnnouncementConfig(
            slack_webhook='https://base.example.com',
            overrides={'other-pkg': override},
        )
        result = resolve_announcement_config(base, 'genkit')
        assert result.slack_webhook == 'https://base.example.com'

    def test_override_inherits_empty_fields_from_base(self) -> None:
        """Empty override fields inherit from base."""
        override = AnnouncementConfig(
            discord_webhook='https://discord.example.com',
            template='',
        )
        base = AnnouncementConfig(
            slack_webhook='https://slack.example.com',
            irc_webhook='https://irc.example.com',
            template='Base template',
            overrides={'genkit': override},
        )
        result = resolve_announcement_config(base, 'genkit')
        assert result.slack_webhook == 'https://slack.example.com'
        assert result.discord_webhook == 'https://discord.example.com'
        assert result.irc_webhook == 'https://irc.example.com'
        assert result.template == 'Base template'
