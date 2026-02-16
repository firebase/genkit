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

"""Release announcement integrations.

Sends release notifications to external services (Slack, Discord, IRC,
Microsoft Teams, Twitter/X, LinkedIn, and custom webhooks) after a
successful publish or rollback. Announcements are fire-and-forget —
failures are logged as warnings but never block the release pipeline.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Announcement            │ A notification sent to Slack, Discord, IRC, │
    │                         │ Teams, Twitter/X, LinkedIn, or a custom     │
    │                         │ webhook after a release or rollback.        │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Webhook                 │ An HTTP POST endpoint that receives a JSON  │
    │                         │ payload with release details.               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Override                │ Per-group or per-package announcement       │
    │                         │ config that merges on top of the base.      │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Template                │ A message template with ``${version}``,     │
    │                         │ ``${packages}``, ``${url}`` placeholders.   │
    └─────────────────────────┴─────────────────────────────────────────────┘

Configuration in ``releasekit.toml``::

    [announcements]
    slack_webhook = "$SLACK_WEBHOOK_URL"
    discord_webhook = "$DISCORD_WEBHOOK_URL"
    teams_webhook = "$TEAMS_WEBHOOK_URL"
    irc_webhook = "$IRC_BRIDGE_URL"
    twitter_bearer_token = "$TWITTER_BEARER_TOKEN"
    linkedin_access_token = "$LINKEDIN_ACCESS_TOKEN"
    linkedin_org_id = "$LINKEDIN_ORG_ID"
    custom_webhooks = ["https://example.com/hook"]
    template = "Released ${version}: ${packages}"
    rollback_template = "⚠️ Rolled back ${version}: ${packages}"

    # Per-group override (group name from [workspace.<label>.groups])
    [announcements.overrides.plugins]
    slack_webhook = "$SLACK_PLUGINS_WEBHOOK"
    template = "Plugin ${version}: ${packages}"

    # Per-package override (exact package name)
    [announcements.overrides."genkit-core"]
    discord_webhook = "$DISCORD_CORE_WEBHOOK"

Usage::

    from releasekit.announce import send_announcements, AnnouncementConfig

    cfg = AnnouncementConfig(
        slack_webhook='https://hooks.slack.com/...',
        template='Released ${version} with ${count} packages',
    )
    await send_announcements(cfg, version='1.2.0', packages=['genkit'])

    # Rollback announcement
    await send_announcements(
        cfg,
        version='1.2.0',
        packages=['genkit'],
        event='rollback',
    )
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import os
import string
from dataclasses import dataclass, field

import httpx

from releasekit.config import AnnouncementConfig
from releasekit.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AnnouncementResult:
    """Result of sending announcements.

    Attributes:
        sent: Number of announcements successfully sent.
        failed: Number of announcements that failed.
        errors: List of error messages for failed sends.
    """

    sent: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether all announcements succeeded."""
        return self.failed == 0

    def summary(self) -> str:
        """Human-readable summary."""
        parts = [f'{self.sent} sent']
        if self.failed:
            parts.append(f'{self.failed} failed')
        return ', '.join(parts)


def _expand_env(value: str) -> str:
    """Expand environment variable references in a string.

    Supports ``$VAR_NAME`` format. Returns the original string if
    the variable is not set.
    """
    if value.startswith('$') and not value.startswith('${'):
        env_name = value[1:]
        return os.environ.get(env_name, value)
    return value


def _render_template(
    template: str,
    *,
    version: str = '',
    packages: list[str] | None = None,
    url: str = '',
) -> str:
    """Render an announcement template with variable substitution.

    Args:
        template: Template string with ``${var}`` placeholders.
        version: Release version.
        packages: List of released package names.
        url: Release URL.

    Returns:
        Rendered message string.
    """
    pkg_list = packages or []
    pkg_str = ', '.join(pkg_list) if len(pkg_list) <= 5 else f'{", ".join(pkg_list[:5])} and {len(pkg_list) - 5} more'

    mapping = {
        'version': version,
        'packages': pkg_str,
        'count': str(len(pkg_list)),
        'url': url,
    }

    # Use string.Template for ${var} substitution (safe_substitute
    # leaves unknown vars intact).
    tmpl = string.Template(template)
    return tmpl.safe_substitute(mapping)


async def _send_slack(
    webhook_url: str,
    message: str,
    *,
    client: httpx.AsyncClient,
) -> None:
    """Send a message to Slack via incoming webhook."""
    payload = {'text': message}
    resp = await client.post(webhook_url, json=payload, timeout=10.0)
    resp.raise_for_status()
    logger.info('announce_slack_sent', status=resp.status_code)


async def _send_discord(
    webhook_url: str,
    message: str,
    *,
    client: httpx.AsyncClient,
) -> None:
    """Send a message to Discord via webhook."""
    payload = {'content': message}
    resp = await client.post(webhook_url, json=payload, timeout=10.0)
    resp.raise_for_status()
    logger.info('announce_discord_sent', status=resp.status_code)


async def _send_irc(
    webhook_url: str,
    message: str,
    *,
    client: httpx.AsyncClient,
) -> None:
    """Send a message to an IRC bridge via HTTP webhook.

    Expects the bridge to accept a JSON payload with a ``message`` field.
    """
    payload = {'message': message}
    resp = await client.post(webhook_url, json=payload, timeout=10.0)
    resp.raise_for_status()
    logger.info('announce_irc_sent', status=resp.status_code)


async def _send_teams(
    webhook_url: str,
    message: str,
    *,
    client: httpx.AsyncClient,
) -> None:
    """Send a message to Microsoft Teams via incoming webhook.

    Uses the `Adaptive Card <https://adaptivecards.io/>`_ format
    wrapped in an O365 connector card, which is the format Teams
    incoming webhooks expect.
    """
    payload = {
        'type': 'message',
        'attachments': [
            {
                'contentType': 'application/vnd.microsoft.card.adaptive',
                'contentUrl': None,
                'content': {
                    '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
                    'type': 'AdaptiveCard',
                    'version': '1.4',
                    'body': [
                        {
                            'type': 'TextBlock',
                            'text': message,
                            'wrap': True,
                        },
                    ],
                },
            },
        ],
    }
    resp = await client.post(webhook_url, json=payload, timeout=10.0)
    resp.raise_for_status()
    logger.info('announce_teams_sent', status=resp.status_code)


async def _send_twitter(
    bearer_token: str,
    message: str,
    *,
    client: httpx.AsyncClient,
) -> None:
    """Post a tweet via the Twitter/X API v2.

    Requires an OAuth 2.0 Bearer token with ``tweet.write`` scope.
    See https://developer.x.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
    """
    url = 'https://api.x.com/2/tweets'
    payload = {'text': message}
    resp = await client.post(
        url,
        json=payload,
        headers={'Authorization': f'Bearer {bearer_token}'},
        timeout=10.0,
    )
    resp.raise_for_status()
    logger.info('announce_twitter_sent', status=resp.status_code)


async def _send_linkedin(
    access_token: str,
    org_id: str,
    message: str,
    *,
    client: httpx.AsyncClient,
) -> None:
    """Post to a LinkedIn organization page via the LinkedIn API.

    Requires an OAuth 2.0 access token with
    ``w_organization_social`` scope.
    See https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
    """
    url = 'https://api.linkedin.com/rest/posts'
    payload = {
        'author': f'urn:li:organization:{org_id}',
        'commentary': message,
        'visibility': 'PUBLIC',
        'distribution': {
            'feedDistribution': 'MAIN_FEED',
            'targetEntities': [],
            'thirdPartyDistributionChannels': [],
        },
        'lifecycleState': 'PUBLISHED',
    }
    resp = await client.post(
        url,
        json=payload,
        headers={
            'Authorization': f'Bearer {access_token}',
            'LinkedIn-Version': '202402',
            'X-Restli-Protocol-Version': '2.0.0',
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    logger.info('announce_linkedin_sent', status=resp.status_code)


async def _send_custom_webhook(
    webhook_url: str,
    message: str,
    *,
    version: str = '',
    packages: list[str] | None = None,
    event: str = 'release',
    client: httpx.AsyncClient,
) -> None:
    """Send a release payload to a custom webhook."""
    payload = {
        'event': event,
        'message': message,
        'version': version,
        'packages': packages or [],
    }
    resp = await client.post(
        webhook_url,
        content=json.dumps(payload),
        headers={'Content-Type': 'application/json'},
        timeout=10.0,
    )
    resp.raise_for_status()
    logger.info('announce_custom_sent', url=webhook_url, status=resp.status_code)


async def send_announcements(
    config: AnnouncementConfig,
    *,
    version: str = '',
    packages: list[str] | None = None,
    url: str = '',
    event: str = 'release',
    dry_run: bool = False,
) -> AnnouncementResult:
    """Send release announcements to all configured channels.

    Failures are logged as warnings but never raise exceptions.
    This function is fire-and-forget by design.

    Args:
        config: Announcement configuration.
        version: Release version string.
        packages: List of released package names.
        url: Release URL (e.g. GitHub Release page).
        event: Event type — ``'release'`` or ``'rollback'``.
            When ``'rollback'``, uses ``rollback_template`` if set.
        dry_run: If True, log what would be sent without sending.

    Returns:
        :class:`AnnouncementResult` with send statistics.
    """
    if not config.enabled:
        return AnnouncementResult()

    template = config.rollback_template if event == 'rollback' and config.rollback_template else config.template
    message = _render_template(
        template,
        version=version,
        packages=packages,
        url=url,
    )

    sent = 0
    failed = 0
    errors: list[str] = []

    # (type, credential_or_url)
    targets: list[tuple[str, str]] = []

    if config.slack_webhook:
        targets.append(('slack', _expand_env(config.slack_webhook)))
    if config.discord_webhook:
        targets.append(('discord', _expand_env(config.discord_webhook)))
    if config.teams_webhook:
        targets.append(('teams', _expand_env(config.teams_webhook)))
    if config.irc_webhook:
        targets.append(('irc', _expand_env(config.irc_webhook)))
    if config.twitter_bearer_token:
        targets.append(('twitter', _expand_env(config.twitter_bearer_token)))
    if config.linkedin_access_token and config.linkedin_org_id:
        targets.append(('linkedin', _expand_env(config.linkedin_access_token)))
    for webhook in config.custom_webhooks:
        targets.append(('custom', _expand_env(webhook)))

    if not targets:
        logger.debug('announce_no_targets')
        return AnnouncementResult()

    if dry_run:
        for target_type, _target_cred in targets:
            logger.info('announce_dry_run', target_type=target_type, event_type=event, message=message)
        return AnnouncementResult(sent=len(targets))

    async def _dispatch(
        target_type: str,
        target_cred: str,
        client: httpx.AsyncClient,
    ) -> tuple[bool, str]:
        """Send to a single target. Returns (ok, error_msg)."""
        try:
            if target_type == 'slack':
                await _send_slack(target_cred, message, client=client)
            elif target_type == 'discord':
                await _send_discord(target_cred, message, client=client)
            elif target_type == 'teams':
                await _send_teams(target_cred, message, client=client)
            elif target_type == 'irc':
                await _send_irc(target_cred, message, client=client)
            elif target_type == 'twitter':
                await _send_twitter(target_cred, message, client=client)
            elif target_type == 'linkedin':
                await _send_linkedin(
                    target_cred,
                    _expand_env(config.linkedin_org_id),
                    message,
                    client=client,
                )
            else:
                await _send_custom_webhook(
                    target_cred,
                    message,
                    version=version,
                    packages=packages,
                    event=event,
                    client=client,
                )
            return (True, '')
        except Exception as exc:  # noqa: BLE001
            logger.warning('announce_failed', target_type=target_type, error=str(exc))
            return (False, f'{target_type}: {exc}')

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(_dispatch(tt, tc, client) for tt, tc in targets),
        )
    for ok, err in results:
        if ok:
            sent += 1
        else:
            failed += 1
            errors.append(err)

    result = AnnouncementResult(sent=sent, failed=failed, errors=errors)
    logger.info('announce_result', event_type=event, summary=result.summary())
    return result


def resolve_announcement_config(
    base: AnnouncementConfig,
    package_name: str,
    groups: dict[str, list[str]] | None = None,
) -> AnnouncementConfig:
    """Resolve the effective announcement config for a package.

    Checks overrides in order: exact package name match first, then
    group membership. The first matching override is merged on top of
    the base config (non-empty override fields win).

    Args:
        base: Base announcement config (workspace or global level).
        package_name: The package being announced.
        groups: Workspace groups mapping (group name → package patterns).

    Returns:
        Merged :class:`AnnouncementConfig` for this package.
    """
    if not base.overrides:
        return base

    # 1. Exact package name match.
    if package_name in base.overrides:
        return _merge_configs(base, base.overrides[package_name])

    # 2. Group membership match (first group wins).
    if groups:
        for group_name, patterns in groups.items():
            if group_name in base.overrides:
                for pattern in patterns:
                    if fnmatch.fnmatch(package_name, pattern):
                        return _merge_configs(base, base.overrides[group_name])

    return base


def _merge_configs(
    base: AnnouncementConfig,
    override: AnnouncementConfig,
) -> AnnouncementConfig:
    """Merge an override config on top of a base config.

    Non-empty override fields replace the base. Empty override fields
    inherit from the base.
    """
    return AnnouncementConfig(
        slack_webhook=override.slack_webhook or base.slack_webhook,
        discord_webhook=override.discord_webhook or base.discord_webhook,
        teams_webhook=override.teams_webhook or base.teams_webhook,
        irc_webhook=override.irc_webhook or base.irc_webhook,
        twitter_bearer_token=override.twitter_bearer_token or base.twitter_bearer_token,
        linkedin_access_token=override.linkedin_access_token or base.linkedin_access_token,
        linkedin_org_id=override.linkedin_org_id or base.linkedin_org_id,
        custom_webhooks=override.custom_webhooks or base.custom_webhooks,
        template=override.template or base.template,
        rollback_template=override.rollback_template or base.rollback_template,
        enabled=override.enabled if override.enabled is not base.enabled else base.enabled,
    )


__all__ = [
    'AnnouncementConfig',
    'AnnouncementResult',
    'resolve_announcement_config',
    'send_announcements',
]
