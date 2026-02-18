---
title: SLSA Provenance
description: Generate and verify SLSA Provenance for your release artifacts.
---

# SLSA Provenance

ReleaseKit can generate **SLSA Provenance v1** attestations for your
published artifacts — machine-readable proof of *what* was built, *how*,
and *from which source*.

## ELI5: What Is SLSA Provenance?

```
┌─────────────────────────────────────────────────────────────────┐
│                   Why Provenance?                                │
│                                                                 │
│  Without provenance:                                            │
│    "Here's genkit-0.6.0.whl. I built it... somewhere."          │
│                                                                 │
│  With provenance (L1):                                          │
│    "Here's genkit-0.6.0.whl + a receipt listing the builder,   │
│     source commit, and SHA-256 digest."                         │
│                                                                 │
│  With signed provenance (L2):                                   │
│    "Same receipt, but cryptographically signed by the CI        │
│     platform so you know it wasn't forged."                     │
│                                                                 │
│  With hardened builds (L3):                                     │
│    "Signed receipt, AND the build ran on an ephemeral VM that   │
│     the CI platform controls — so even the build steps can't    │
│     tamper with the provenance."                                │
└─────────────────────────────────────────────────────────────────┘
```

| SLSA Level | When It Activates | What Happens |
|------------|-------------------|---------------|
| **L0** | Local builds without flags | No provenance |
| **L1** | Any CI pipeline (`CI=true`) | Provenance auto-generated |
| **L2** | CI + OIDC + self-hosted runners | Provenance auto-generated **and signed** |
| **L3** | CI + OIDC + hosted runners (default) | Signed provenance + hardened, isolated builds |

!!! success "L3 by default — zero configuration"
    When you publish from GitHub Actions hosted runners with
    `id-token: write`, ReleaseKit **automatically** achieves SLSA
    Build L3 — signed provenance with hardened, isolated builds.
    No flags needed.

## L3 by Default

ReleaseKit auto-detects your CI environment and enables the highest
SLSA level your pipeline supports:

```
┌───────────────────────────────────────────────────────────────────┐
│  Environment Detection → SLSA Level                               │
│                                                                   │
│  Local machine                        → L0  (no provenance)       │
│  CI without OIDC                      → L1  (provenance exists)   │
│  CI + OIDC + self-hosted runners      → L2  (signed provenance)   │
│  CI + OIDC + github-hosted runners    → L3  (hardened + signed)   │
│  GitLab CI + OIDC + gitlab.com shared → L3  (hardened + signed)   │
│  CircleCI + OIDC                      → L2  (no ephemeral VMs)    │
└───────────────────────────────────────────────────────────────────┘
```

**How it works:**

1. ReleaseKit checks for `CI=true` → enables provenance generation (L1)
2. ReleaseKit checks for OIDC tokens → enables Sigstore signing (L2)
3. ReleaseKit checks runner isolation → upgrades to L3 on hosted runners
4. No config changes needed — just ensure your CI has OIDC permissions

### One-line setup for GitHub Actions

Add `id-token: write` to your workflow permissions. That's it.

```yaml
permissions:
  contents: write
  id-token: write   # ← This single line enables SLSA L3 on hosted runners
```

### One-line setup for GitLab CI

Add an `id_tokens` block to your job:

```yaml
release:
  id_tokens:
    SIGSTORE_ID_TOKEN:
      aud: sigstore   # ← This enables SLSA L3 on gitlab.com shared runners
  script:
    - releasekit publish
```

### Opting out

To disable auto-provenance (e.g. for local testing), set in
`releasekit.toml`:

```toml
[workspace.py]
slsa_provenance = false
sign_provenance = false
```

Or use environment variables:

```bash
CI= releasekit publish   # Unset CI to disable auto-detection
```

## Quick Start

### Generate provenance

```bash
# In CI: provenance is auto-generated (no flags needed)
releasekit publish

# Locally: opt-in with explicit flags
releasekit publish --slsa-provenance

# Locally: generate AND sign (implies --slsa-provenance)
releasekit publish --sign-provenance
```

### Verify provenance

```bash
# Verify artifact digests against provenance
releasekit verify dist/ --provenance provenance.intoto.jsonl

# Verify both provenance and Sigstore signatures
releasekit verify dist/ --provenance provenance.intoto.jsonl \
  --cert-identity https://github.com/firebase/genkit/.github/workflows/release.yml@refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com
```

## Configuration

### CLI flags

| Flag | Description |
|------|-------------|
| `--slsa-provenance` | Force-enable SLSA Provenance (auto-enabled in CI) |
| `--sign-provenance` | Force-enable signed provenance (auto-enabled in CI + OIDC) |

### `releasekit.toml`

```toml
[workspace.py]
slsa_provenance = true   # Always generate provenance (even locally)
sign_provenance = true   # Always sign provenance (even locally, if OIDC available)
```

Flags, config, and auto-detection are OR'd together — if **any** source
enables the feature, it activates.

## How It Works

### 1. Artifact checksums are collected

During the publish pipeline, ReleaseKit computes SHA-256 digests for
every distribution artifact (`.tar.gz`, `.whl`, `.tgz`, `.jar`).

### 2. Build context is detected

ReleaseKit auto-detects the CI environment:

| CI Platform | Detection | Builder ID |
|-------------|-----------|------------|
| **GitHub Actions** | `GITHUB_ACTIONS=true` | `https://github.com/actions/runner` |
| **GitLab CI** | `GITLAB_CI=true` | `https://gitlab.com/gitlab-runner` |
| **CircleCI** | `CIRCLECI=true` | `https://circleci.com/runner` |
| **Local** | (fallback) | `local://<hostname>` |

### 3. Provenance statement is generated

An [in-toto Statement v1](https://in-toto.io/Statement/v1) is created
with a [SLSA Provenance v1](https://slsa.dev/provenance/v1) predicate:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {
      "name": "genkit-0.6.0.tar.gz",
      "digest": { "sha256": "abc123..." }
    }
  ],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": {
    "buildDefinition": {
      "buildType": "https://firebase.google.com/releasekit/v1",
      "externalParameters": {
        "packageName": "genkit",
        "packageVersion": "0.6.0",
        "ecosystem": "python"
      },
      "resolvedDependencies": [
        {
          "uri": "https://github.com/firebase/genkit",
          "digest": { "gitCommit": "abc123def456..." }
        }
      ]
    },
    "runDetails": {
      "builder": { "id": "https://github.com/actions/runner" },
      "metadata": {
        "invocationId": "https://github.com/firebase/genkit/actions/runs/123/attempts/1",
        "startedOn": "2026-01-15T10:00:00Z",
        "finishedOn": "2026-01-15T10:05:00Z"
      }
    }
  }
}
```

### 4. Provenance is written

The file is saved as:

- `provenance.intoto.jsonl` (default)
- `provenance-<label>.intoto.jsonl` (when workspace has a label)

### 5. Provenance is attached to GitHub Release

When creating a GitHub Release (via `releasekit release`), the
provenance file is automatically attached as a release asset alongside
the release manifest.

### 6. (Optional) Provenance is signed

With `--sign-provenance`, the provenance file is signed using
[Sigstore](https://sigstore.dev) keyless signing. This produces a
companion `.sigstore.json` bundle. See the
[Signing & Verification](signing.md) guide for details.

## CI Integration

### GitHub Actions

```yaml
name: Release
on:
  push:
    branches: [main]

permissions:
  contents: write
  id-token: write  # Required for Sigstore OIDC signing

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: firebase/genkit/.github/actions/releasekit@main
        with:
          command: publish --sign-provenance
```

!!! tip "OIDC permissions"
    The `id-token: write` permission is required for Sigstore to obtain
    an OIDC token from GitHub Actions. Without it, signing will fail.

### GitLab CI

```yaml
release:
  stage: deploy
  id_tokens:
    SIGSTORE_ID_TOKEN:
      aud: sigstore
  script:
    - releasekit publish
```

!!! tip "No flags needed"
    With OIDC configured, `releasekit publish` auto-detects the
    environment and enables L3 provenance on hosted runners. The
    `--sign-provenance` flag is only needed for local builds.

## Verification

### Verify artifact digests

```bash
releasekit verify dist/genkit-0.6.0.tar.gz \
  --provenance provenance.intoto.jsonl
```

This checks that the artifact's SHA-256 digest matches a subject in the
provenance statement. Output:

```
  ✅ Provenance: genkit-0.6.0.tar.gz
```

### Verify Sigstore signature

```bash
releasekit verify dist/genkit-0.6.0.tar.gz \
  --provenance provenance.intoto.jsonl \
  --cert-identity https://github.com/firebase/genkit/.github/workflows/release.yml@refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com
```

This verifies both the provenance digest match AND the Sigstore bundle.

### What verification checks

| Check | What it verifies |
|-------|-----------------|
| **Digest match** | Artifact SHA-256 matches a provenance subject |
| **Statement type** | `_type` is `https://in-toto.io/Statement/v1` |
| **Predicate type** | `predicateType` is `https://slsa.dev/provenance/v1` |
| **Sigstore bundle** | (if `--cert-identity` provided) Signature is valid |

## SLSA Levels Explained

### Level 0 — No provenance

Default for **local** builds. No attestation is generated unless
you pass `--slsa-provenance` explicitly.

### Level 1 — Provenance exists

**Auto-enabled in CI** (when `CI=true`). The provenance document:

- Lists all artifacts with SHA-256 digests
- Records the builder, source repo, and commit SHA
- Is distributed alongside artifacts and attached to GitHub Releases

### Level 2 — Signed provenance

**Auto-enabled in CI with OIDC on self-hosted runners** or CircleCI.
Everything from L1, plus:

- Provenance is signed by the CI platform via Sigstore OIDC
- Consumers can verify the signature to confirm authenticity
- Achieved on self-hosted GitHub Actions runners, self-managed GitLab
  runners, and CircleCI (which lacks ephemeral VM guarantees)

### Level 3 — Hardened builds (default on hosted runners)

**Auto-enabled on GitHub-hosted runners and gitlab.com shared runners
with OIDC.** Everything from L2, plus:

- Build isolation — ephemeral, single-use VMs
- Platform-controlled signing — build steps cannot access signing keys
- Non-falsifiable provenance generated by the control plane
- Runner environment, invocation ID, and build level recorded in provenance

ReleaseKit detects the runner environment automatically:

| CI Platform | Runner Type | Achieved Level |
|-------------|-------------|:--------------:|
| GitHub Actions | `ubuntu-latest` (hosted) | **L3** |
| GitHub Actions | self-hosted | L2 |
| GitLab CI | gitlab.com shared | **L3** |
| GitLab CI | self-managed | L2 |
| CircleCI | any | L2 |
| Google Cloud Build | any | **L3** |

!!! success "L3 is the default for most users"
    If you use `runs-on: ubuntu-latest` (or any GitHub-hosted runner)
    with `id-token: write`, you already have SLSA Build L3. No extra
    configuration needed.

## Build/Upload Isolation (SLSA L3)

SLSA Build L3 requires that the build and upload steps run in separate,
isolated environments so that a compromised build step cannot tamper
with the upload or forge provenance. ReleaseKit enforces this with
`--build-only` and `--upload-only` flags that split the publish
pipeline into separate CI jobs.

### ELI5: Why Separate Build and Upload?

```text
Without isolation (single job):

  build + upload in one step
  ┌─────────────────────────────────────────┐
  │  build artifacts  ──>  upload to PyPI   │  <-- if build is
  │  (same VM, same job, same permissions)  │      compromised,
  └─────────────────────────────────────────┘      upload is too

With isolation (separate jobs):

  Job 1: build          Job 2: provenance      Job 3: upload
  ┌──────────────┐      ┌──────────────┐       ┌──────────────┐
  │ build only   │ ---> │ attest build │ --->  │ upload only  │
  │ no registry  │      │ (SLSA gen)   │       │ no build     │
  │ access       │      │ signs digest │       │ access       │
  └──────────────┘      └──────────────┘       └──────────────┘
        |                      |                      |
    fresh VM #1           fresh VM #2            fresh VM #3
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--build-only` | Build artifacts and compute digests, but do NOT upload. Artifacts are written to `<workspace>/dist/`. |
| `--upload-only` | Upload pre-built artifacts from `--dist-dir` without rebuilding. Skips the build step. |
| `--dist-dir PATH` | Directory containing pre-built artifacts (used with `--upload-only`). Defaults to `<workspace>/dist/`. |

These flags are mutually exclusive: you cannot pass both `--build-only`
and `--upload-only` in the same invocation.

```bash
# Job 1: Build only (no registry access)
releasekit publish --build-only

# Job 2: (provenance generation happens here via slsa-github-generator)

# Job 3: Upload only (no build access)
releasekit publish --upload-only --dist-dir dist/
```

### 4-Job CI Pipeline

The recommended CI pipeline for SLSA L3 compliance uses four jobs:

```text
┌─────────┐     ┌─────────┐     ┌────────────┐     ┌────────┐
│ release │ --> │  build  │ --> │ provenance │ --> │ upload │
│         │     │         │     │            │     │        │
│ prepare │     │ --build │     │ slsa-gen   │     │--upload│
│ version │     │ -only   │     │ signs the  │     │ -only  │
│ bump    │     │         │     │ digest     │     │        │
└─────────┘     └─────────┘     └────────────┘     └────────┘
                     |                |                  |
                  artifacts       provenance         verified
                  + digests       attestation        artifacts
                                                        |
                                                   ┌────────┐
                                                   │ verify │
                                                   │        │
                                                   │ slsa-  │
                                                   │verifier│
                                                   └────────┘
```

| Job | What It Does | Key Properties |
|-----|-------------|----------------|
| **release** | Version bump, changelog, Release PR | No registry access |
| **build** | `releasekit publish --build-only` | No upload permissions, writes artifacts to `dist/` |
| **provenance** | `slsa-github-generator` signs artifact digests | Platform-controlled, non-falsifiable |
| **upload** | `releasekit publish --upload-only` | No build access, uploads pre-built artifacts |
| **verify** | `slsa-verifier` validates provenance | Independent verification |

### Composite Actions

ReleaseKit provides four reusable composite actions that encapsulate
the SLSA L3 pipeline steps. These are ecosystem-agnostic and work for
Python, JavaScript, Go, Rust, Dart, and Java/Gradle.

| Action | Purpose | Used In |
|--------|---------|---------|
| `compute-artifact-digests` | SHA-256 digests in base64 for `slsa-github-generator` | build job |
| `attest-build-artifacts` | GitHub artifact attestation via `actions/attest-build-provenance` | build job |
| `upload-release-artifacts` | Upload artifacts, manifest, SBOMs to GitHub Release | build/upload job |
| `verify-slsa-provenance` | Download provenance + run `slsa-verifier` | verify job |

Example usage in a workflow:

```yaml
# In the build job:
- uses: ./.github/actions/compute-artifact-digests
  id: hash
  with:
    workspace-dir: py

# In the verify job:
- uses: ./.github/actions/verify-slsa-provenance
  with:
    provenance-name: ${{ needs.provenance.outputs.provenance-name }}
    provenance-available: ${{ needs.provenance.result == 'success' && 'true' || 'false' }}
```

### Post-Publish Verification

After uploading, the `verify-install` command verifies that published
packages are actually installable from the registry:

```bash
# Verify all packages from a release manifest
releasekit verify-install --manifest release-manifest--py.json

# Verify with a smoke-test import
releasekit verify-install --manifest release-manifest--py.json \
  --import-check "from genkit.ai import Genkit"

# Verify against a staging registry
releasekit verify-install --manifest release-manifest--py.json \
  --index-url https://test.pypi.org/simple/

# Override ecosystem (CLI overrides manifest value)
releasekit verify-install --manifest release-manifest--js.json \
  --ecosystem js
```

The command reads the release manifest, extracts non-skipped packages,
and installs each one using the ecosystem-appropriate package manager
(pip, npm, cargo). It validates all package specs against a security
allowlist before executing any install commands.

### SLSA L3 Requirements Mapping

The table below maps each SLSA Build L3 requirement to the specific
mechanism used in the ReleaseKit workflow templates:

| Requirement | Mechanism | Job(s) |
|-------------|-----------|--------|
| Hardened build platform | GitHub-hosted `ubuntu-latest` | build |
| Build/upload isolation | Separate `--build-only` + `--upload-only` jobs | build, upload |
| Non-falsifiable provenance | `slsa-github-generator` (L3) | provenance |
| Hermetic build | `--build-only` (no registry I/O during build) | build |
| Pinned dependencies | All actions pinned to commit SHA | all |
| Ephemeral environment | Fresh VM per job run | all |
| OIDC identity | `id-token: write` (Sigstore) | build, upload |
| Provenance before upload | provenance job runs between build and upload | provenance |
| Verification | `slsa-verifier` + `verify-install` | verify |

## Troubleshooting

### Provenance not generated

- In CI: provenance is auto-generated. Check that `CI=true` is set.
- Locally: pass `--slsa-provenance` or set `slsa_provenance = true`
  in `releasekit.toml`
- Provenance is only generated when packages are actually published
  (not in `--dry-run` mode)

### Signing failed

- Ensure `id-token: write` permission is set in GitHub Actions
- Ensure the CI environment provides OIDC tokens
- Check that `sigstore` is installed: `pip install sigstore`

### Verification failed

- **"not found in provenance"**: The artifact's digest doesn't match
  any subject. The artifact may have been modified after publishing.
- **"Unexpected statement type"**: The provenance file is not a valid
  in-toto Statement v1.
- **"Bundle not found"**: No `.sigstore.json` file exists alongside
  the artifact. Was `--sign-provenance` used during publish?
