---
title: CI/CD Integration
description: Automate releases with GitHub Actions, GitLab CI, and more.
---

# CI/CD Integration

ReleaseKit ships as both a CLI tool and a **GitHub Action** for
seamless CI integration.

## Release Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Main as main branch
    participant RK as ReleaseKit
    participant PR as Release PR
    participant PyPI as Registry

    Dev->>Main: Push conventional commits
    Main->>RK: trigger: releasekit prepare
    RK->>RK: compute_bumps()
    RK->>RK: bump pyproject.toml
    RK->>RK: generate changelogs
    RK->>PR: Open Release PR

    Dev->>PR: Review & Merge
    PR->>Main: Merge

    Main->>RK: trigger: releasekit release
    RK->>RK: Extract manifest from PR body
    RK->>RK: Create git tags
    RK->>RK: Create GitHub Release

    Note over RK,PyPI: If publish_from = "ci"
    RK->>PyPI: releasekit publish
    PyPI-->>RK: Verify checksums
```

## GitHub Action

### Basic Usage

```yaml
name: Release
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write  # For OIDC trusted publishing
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for version computation

      - uses: ./py/tools/releasekit
        with:
          command: prepare
          working-directory: py
```

### Two-Step Release (Prepare + Publish)

```yaml
name: Release
on:
  push:
    branches: [main]
  pull_request:
    types: [closed]

jobs:
  # Step 1: On push to main, prepare a Release PR
  prepare:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: ./py/tools/releasekit
        with:
          command: prepare
          working-directory: py
          forge-backend: api

  # Step 2: On Release PR merge, tag + publish
  publish:
    if: >-
      github.event.pull_request.merged == true &&
      contains(github.event.pull_request.labels.*.name, 'autorelease: pending')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Preview execution plan
        run: |
          cd py
          uv run releasekit plan --format full

      - uses: ./py/tools/releasekit
        with:
          command: release
          working-directory: py
          forge-backend: api

      - name: Preview execution plan
        run: |
          cd py
          uv run releasekit plan --format full

      - uses: ./py/tools/releasekit
        with:
          command: publish
          working-directory: py
          concurrency: "5"
          max-retries: "2"
```

### Action Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `command` | `plan` | Subcommand: `publish`, `plan`, `prepare`, `release`, `check`, `discover`, `version`, `rollback` |
| `group` | `""` | Release group name (from `releasekit.toml` groups) |
| `dry-run` | `"false"` | Preview mode |
| `force` | `"false"` | Skip confirmations and preflight checks |
| `forge-backend` | `"api"` | `cli` (needs `gh`) or `api` (REST, needs `GITHUB_TOKEN`) |
| `check-url` | `""` | URL for `uv publish --check-url` |
| `index-url` | `""` | Custom registry URL (e.g., Test PyPI) |
| `concurrency` | `"5"` | Max packages publishing simultaneously |
| `max-retries` | `"2"` | Retry count with exponential backoff |
| `python-version` | `"3.12"` | Python version to install |
| `uv-version` | `"latest"` | uv version to install |
| `working-directory` | `"."` | Path to workspace root |
| `extra-args` | `""` | Additional CLI arguments |

### Action Outputs

| Output | Description |
|--------|-------------|
| `exit-code` | Exit code from the releasekit command |
| `plan-json` | JSON output (only when `command=plan`) |

## OIDC Trusted Publishing

For PyPI trusted publishing (no tokens needed):

```yaml
permissions:
  id-token: write  # Required for OIDC

steps:
  - uses: ./py/tools/releasekit
    with:
      command: publish
```

ReleaseKit's preflight checks will warn if trusted publishing is not
configured.

## GitLab CI

```yaml
release:
  stage: deploy
  image: python:3.12
  before_script:
    - pip install uv
    - uv sync --active
  script:
    - uv run releasekit prepare --forge-backend cli
  only:
    - main
```

## Testing Releases

### Test PyPI

```bash
releasekit publish \
  --index-url https://test.pypi.org/simple/ \
  --check-url https://test.pypi.org/simple/ \
  --dry-run
```

### Local Dry Run

```bash
# Preview the full plan
releasekit plan --format json

# Dry-run publish (no uploads)
releasekit publish --dry-run
```

## Scheduled / Cadence Releases *(planned)*

ReleaseKit will support scheduled releases via the `should-release`
command and `[schedule]` config. This enables daily, weekly, or
custom-cadence releases driven by CI cron triggers.

### Daily Release (GitHub Actions)

```yaml
name: Daily Release
on:
  schedule:
    - cron: '0 14 * * *'  # 2 PM UTC daily

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check if release needed
        id: check
        run: |
          uv run releasekit should-release || echo "skip=true" >> "$GITHUB_OUTPUT"

      - uses: ./py/tools/releasekit
        if: steps.check.outputs.skip != 'true'
        with:
          command: prepare
          working-directory: py
```

### Configuration

```toml
# releasekit.toml — scheduled release settings (planned)
[schedule]
cadence          = "daily"          # daily | weekly:monday | biweekly | on-push
release_window   = "14:00-16:00"   # UTC time range
cooldown_minutes = 60               # min time between releases
min_bump         = "patch"          # skip if only chore/docs commits
```

## Continuous Deploy Mode *(planned)*

For projects that want a release on every push to `main` (like
semantic-release's default behavior), ReleaseKit will support a
`release_mode = "continuous"` config that skips PR creation and
goes directly to tag + publish.

### Per-Commit Release (GitHub Actions)

```yaml
name: Continuous Deploy
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: ./py/tools/releasekit
        with:
          command: publish
          extra-args: "--if-needed"
          working-directory: py
```

### Configuration

```toml
# releasekit.toml — continuous deploy settings (planned)
release_mode = "continuous"   # skip PR, tag + publish directly
```

## Lifecycle Hooks *(planned)*

ReleaseKit will support lifecycle hooks that run custom scripts at
key points in the release pipeline. Unlike semantic-release's plugin
system, hooks are simple shell commands configured in TOML — no
JavaScript plugins required.

### Configuration

```toml
# releasekit.toml — lifecycle hooks (planned)
[hooks]
before_prepare = ["./scripts/pre-release-checks.sh"]
after_tag      = ["./scripts/notify-slack.sh ${version}"]
before_publish = ["./scripts/build-docs.sh"]
after_publish  = [
  "./scripts/update-homebrew-formula.sh ${version}",
  "./scripts/announce-release.sh ${name} ${version}",
]
```

Template variables available in hooks:

| Variable | Description |
|----------|-------------|
| `${version}` | The new version being released |
| `${name}` | Package name |
| `${tag}` | Git tag (e.g. `genkit-v0.6.0`) |
