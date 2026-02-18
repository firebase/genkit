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
structured inputs and parsed outputs. Supports `--build-only` and
`--upload-only` flags for SLSA L3 build/upload isolation.

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

### `compute-artifact-digests`

Compute SHA-256 digests of build artifacts for SLSA provenance.
Ecosystem-agnostic: works with any artifact type.

```yaml
- uses: ./.github/actions/compute-artifact-digests
  id: hash
  with:
    workspace-dir: py
    artifact-pattern: |                  # optional; default: "*"
      *.whl
      *.tar.gz
    search-dir: dist                    # optional; default: "dist"
```

### `upload-release-artifacts`

Upload distributions, manifest, provenance, and SBOMs to GitHub's
artifact store. Each artifact type can be independently toggled.

```yaml
- uses: ./.github/actions/upload-release-artifacts
  with:
    workspace-dir: py
    manifest-name: release-manifest     # unique per ecosystem
    upload-dist: "true"                 # for SLSA L3 build/upload split
    upload-provenance: "true"
    upload-sbom: "true"
```

### `attest-build-artifacts`

Generate GitHub-signed build provenance and SBOM attestations.
Requires the calling job to have `attestations: write` and
`id-token: write` permissions.

```yaml
- uses: ./.github/actions/attest-build-artifacts
  with:
    subject-path: |
      py/dist/**/*.whl
      py/dist/**/*.tar.gz
    sbom-path: py/sbom.cdx.json        # optional
    has-digests: "true"
```

### `verify-slsa-provenance`

Download and verify SLSA L3 provenance using `slsa-verifier`.
Ecosystem-agnostic: works with any artifact type.

```yaml
- uses: ./.github/actions/verify-slsa-provenance
  with:
    provenance-name: ${{ needs.provenance.outputs.provenance-name }}
    provenance-available: "true"
    artifact-pattern: |                  # optional; default: "*"
      *.whl
      *.tar.gz
```

## SLSA L3 Build/Upload Isolation

For SLSA Build Level 3 compliance, split the publish job into
four separate jobs:

```text
build --> provenance --> upload --> verify
```

1. **build**: Use `run-releasekit` with `build-only: "true"`, then
   `compute-artifact-digests` and `upload-release-artifacts`.
2. **provenance**: Call `slsa-github-generator` with the digests.
3. **upload**: Download artifacts, use `run-releasekit` with
   `upload-only: "true"` and `dist-dir` pointing to downloaded artifacts.
4. **verify**: Use `verify-slsa-provenance` to validate attestations.

See the `releasekit-uv.yml` template for a complete working example.

## Installation

```bash
# From your repo root:
cp -r path/to/releasekit/github/actions/setup-ollama             .github/actions/setup-ollama
cp -r path/to/releasekit/github/actions/setup-releasekit          .github/actions/setup-releasekit
cp -r path/to/releasekit/github/actions/run-releasekit            .github/actions/run-releasekit
cp -r path/to/releasekit/github/actions/compute-artifact-digests  .github/actions/compute-artifact-digests
cp -r path/to/releasekit/github/actions/upload-release-artifacts  .github/actions/upload-release-artifacts
cp -r path/to/releasekit/github/actions/attest-build-artifacts    .github/actions/attest-build-artifacts
cp -r path/to/releasekit/github/actions/verify-slsa-provenance    .github/actions/verify-slsa-provenance
```

Then reference them in your workflows as `./.github/actions/<name>`.
