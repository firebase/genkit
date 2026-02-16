---
title: Announcements
description: Notify your team about releases via Slack, Discord, Teams, and more.
---

# Release Announcements

ReleaseKit can automatically send release (and rollback) notifications
to multiple channels after a successful publish. Announcements are
**fire-and-forget** — failures are logged as warnings but never block
the release pipeline.

---

## Supported Channels

| Channel | Config Key | Auth Method |
|---------|-----------|-------------|
| **Slack** | `slack_webhook` | [Incoming Webhook URL](https://api.slack.com/messaging/webhooks) |
| **Discord** | `discord_webhook` | [Webhook URL](https://discord.com/developers/docs/resources/webhook) |
| **Microsoft Teams** | `teams_webhook` | [Incoming Webhook](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook) |
| **IRC** | `irc_webhook` | HTTP bridge URL (e.g. [thelounge](https://github.com/thelounge/thelounge)) |
| **Twitter/X** | `twitter_bearer_token` | [OAuth 2.0 Bearer Token](https://developer.x.com/en/docs/authentication/oauth-2-0) |
| **LinkedIn** | `linkedin_access_token` + `linkedin_org_id` | [OAuth 2.0](https://learn.microsoft.com/en-us/linkedin/marketing/) |
| **Custom Webhook** | `custom_webhooks` | Any HTTP endpoint |

---

## Configuration

Add an `[announcements]` section to `releasekit.toml`:

```toml
[announcements]
# Webhook URLs — use environment variable references for secrets.
slack_webhook = "$SLACK_WEBHOOK_URL"
discord_webhook = "$DISCORD_WEBHOOK_URL"
teams_webhook = "$TEAMS_WEBHOOK_URL"
irc_webhook = "$IRC_BRIDGE_URL"

# Social media (optional).
twitter_bearer_token = "$TWITTER_BEARER_TOKEN"
linkedin_access_token = "$LINKEDIN_ACCESS_TOKEN"
linkedin_org_id = "$LINKEDIN_ORG_ID"

# Custom webhooks receive a JSON payload.
custom_webhooks = ["$CUSTOM_HOOK_1", "$CUSTOM_HOOK_2"]

# Template for the message body (all channels).
template = """
🚀 **${project}** ${version} released!

Packages: ${packages}
Release: ${url}
"""
```

!!! tip "Environment Variables"
    All webhook URLs and tokens support `$VAR_NAME` expansion from
    environment variables. **Never commit secrets directly** into
    `releasekit.toml`.

---

## Template Variables

Templates support these `${variable}` placeholders:

| Variable | Description | Example |
|----------|-------------|---------|
| `${version}` | The release version | `0.5.0` |
| `${packages}` | Comma-separated list of released packages | `genkit, genkit-plugin-google-genai` |
| `${url}` | URL to the GitHub Release | `https://github.com/firebase/genkit/releases/tag/v0.5.0` |
| `${project}` | Project name from config | `genkit` |

---

## Per-Group Overrides

Override templates or channels for specific release groups:

```toml
[announcements]
slack_webhook = "$SLACK_GENERAL"

[announcements.overrides.core]
slack_webhook = "$SLACK_CORE_TEAM"
template = "🎯 Core release ${version}: ${packages}"

[announcements.overrides.samples]
# Skip announcements for sample packages.
enabled = false
```

---

## Events

Announcements fire on two events:

| Event | When | Default |
|-------|------|---------|
| `release` | After successful publish + tagging | ✅ Enabled |
| `rollback` | After a rollback operation | ✅ Enabled |

---

## Custom Webhook Payload

Custom webhooks receive a JSON POST body:

```json
{
  "event": "release",
  "version": "0.5.0",
  "packages": ["genkit", "genkit-plugin-google-genai"],
  "message": "🚀 genkit 0.5.0 released!",
  "timestamp": "2026-02-15T12:00:00Z"
}
```

---

## CLI Usage

Announcements are sent automatically after a successful `releasekit publish`.
No separate command is needed — just configure the `[announcements]` section
in your `releasekit.toml` and they fire on publish and rollback events.

```bash
# Publish triggers announcements automatically.
releasekit publish

# Dry-run publish to preview announcements without sending.
releasekit publish --dry-run
```

---

## Troubleshooting

!!! warning "Slack 403 errors"
    Ensure the webhook URL is for an **Incoming Webhook** app, not a
    Bot token. Incoming webhooks use a URL like
    `https://hooks.slack.com/services/T.../B.../xxx`.

!!! warning "Teams message not appearing"
    Teams webhooks require the **Adaptive Card** format. ReleaseKit
    handles this automatically, but ensure your Teams channel has the
    Incoming Webhook connector enabled.
