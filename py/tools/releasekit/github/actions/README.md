# ReleaseKit GitHub Actions

Reusable composite actions for CI/CD pipelines. Copy these into your
repo's `.github/actions/` directory.

## Actions

### `setup-ollama`

Install Ollama, pull models, and cache them between CI runs.

```yaml
- uses: ./.github/actions/setup-ollama
  with:
    models: "gemma3:4b"
```

### `setup-releasekit`

All-in-one environment setup: checkout, uv, Python, releasekit,
Ollama (optional), and git identity.

```yaml
- uses: ./.github/actions/setup-releasekit
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    releasekit-dir: tools/releasekit    # adjust to your layout

# Skip Ollama for jobs that don't need AI (e.g. publish):
- uses: ./.github/actions/setup-releasekit
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    enable-ollama: "false"
```

### `run-releasekit`

Run a releasekit command (prepare, release, or publish) with
structured inputs and parsed outputs.

```yaml
- uses: ./.github/actions/run-releasekit
  id: prepare
  with:
    command: prepare
    workspace: py
    group: ${{ inputs.group }}
    force: ${{ inputs.force_prepare }}
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Installation

```bash
# From your repo root:
cp -r path/to/releasekit/github/actions/setup-ollama    .github/actions/setup-ollama
cp -r path/to/releasekit/github/actions/setup-releasekit .github/actions/setup-releasekit
cp -r path/to/releasekit/github/actions/run-releasekit   .github/actions/run-releasekit
```

Then reference them in your workflows as `./.github/actions/<name>`.
