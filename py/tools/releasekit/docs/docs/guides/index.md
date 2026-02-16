---
title: Guides
description: Practical guides for using ReleaseKit.
---

# Guides

Step-by-step guides for common workflows.

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **[Getting Started](getting-started.md)**

    ---

    Install, initialize, and publish your first release.

-   :material-cog:{ .lg .middle } **[Configuration](configuration.md)**

    ---

    All `releasekit.toml` options with examples.

-   :material-tag:{ .lg .middle } **[Versioning Schemes](versioning-schemes.md)**

    ---

    Understand semver, PEP 440, and CalVer — and when to use each.

-   :material-package-variant:{ .lg .middle } **[Per-Package Config](per-package-config.md)**

    ---

    Override workspace settings for individual packages or groups.

-   :material-earth:{ .lg .middle } **[Multi-Ecosystem](multi-ecosystem.md)**

    ---

    Managing Python + JavaScript + Go in one monorepo.

-   :material-publish:{ .lg .middle } **[Publish Pipeline](publish-pipeline.md)**

    ---

    The 6-stage pipeline: pin → build → publish → poll → verify → restore.

-   :material-stethoscope:{ .lg .middle } **[Health Checks & Doctor](health-checks.md)**

    ---

    Validate your workspace before releasing with `check` and `doctor`.

-   :material-shield-check:{ .lg .middle } **[Security & Compliance](compliance.md)**

    ---

    OSPS Baseline compliance evaluation across all ecosystems.

-   :material-skip-next:{ .lg .middle } **[Skipping Checks](skip-checks.md)**

    ---

    Bypass specific health checks for individual packages.

-   :material-camera-burst:{ .lg .middle } **[Snapshots & Pre-Releases](snapshots.md)**

    ---

    Snapshot builds, release candidates, and promoting to stable.

-   :material-shield-lock:{ .lg .middle } **[Signing & Verification](signing.md)**

    ---

    Sign artifacts with Sigstore keyless signing and verify them.

-   :material-certificate:{ .lg .middle } **[SLSA Provenance](slsa-provenance.md)**

    ---

    Generate and verify SLSA Provenance v1 attestations for artifacts.

-   :material-robot:{ .lg .middle } **[CI/CD Integration](ci-cd.md)**

    ---

    GitHub Actions, GitLab CI, and Bitbucket Pipelines.

-   :material-file-document:{ .lg .middle } **[Workflow Templates](workflow-templates.md)**

    ---

    Production-ready GitHub Actions workflows you can copy-paste.

-   :material-undo:{ .lg .middle } **[Rollback](rollback.md)**

    ---

    Undo a release — delete tags, releases, and yank from registries.

-   :material-swap-horizontal:{ .lg .middle } **[Migration](migration.md)**

    ---

    Migrate from release-please, semantic-release, changesets, or lerna.

-   :material-alert-circle:{ .lg .middle } **[Error Codes](error-codes.md)**

    ---

    Every `RK-*` error code with causes and fixes.

-   :material-frequently-asked-questions:{ .lg .middle } **[FAQ](faq.md)**

    ---

    Common questions for release managers — beginner to expert.

</div>
