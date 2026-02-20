---
title: Guides
description: Practical guides for using ReleaseKit.
---

# Guides

Step-by-step guides for common workflows, organized by topic.

---

## :material-rocket-launch: Getting Started

| Guide | Description |
|-------|-------------|
| **[Quick Start](getting-started.md)** | Install, initialize, and publish your first release. |
| **[Configuration](configuration.md)** | All `releasekit.toml` options with examples. |
| **[Per-Package Config](per-package-config.md)** | Override workspace settings for individual packages or groups. |
| **[Multi-Ecosystem](multi-ecosystem.md)** | Managing Python + JavaScript + Go in one monorepo. |
| **[Release Groups](groups.md)** | Publish subsets of workspace packages independently. |
| **[Migration](migration.md)** | Migrate from release-please, semantic-release, changesets, or lerna. |

---

## :material-tag: Versioning

| Guide | Description |
|-------|-------------|
| **[Versioning Schemes](versioning-schemes.md)** | Understand semver, PEP 440, and CalVer — and when to use each. |
| **[Release Channels](channels.md)** | Map git branches to dist-tags and pre-release labels. |
| **[Changesets](changesets.md)** | Use changeset files for explicit version bump control. |
| **[Snapshots & Pre-Releases](snapshots.md)** | Snapshot builds, release candidates, and promoting to stable. |

---

## :material-publish: Publishing

| Guide | Description |
|-------|-------------|
| **[Publish Pipeline](publish-pipeline.md)** | The 6-stage pipeline: pin → build → publish → poll → verify → restore. |
| **[Dependency Pinning](dependency-pinning.md)** | How internal dependency versions are handled during publishing. |
| **[Lifecycle Hooks](hooks.md)** | Execute custom scripts at specific points in the release pipeline. |
| **[Commit-Back PRs](commitback.md)** | Automatically bump to dev versions after a release. |
| **[Hotfix & Maintenance](hotfix.md)** | Release patches from maintenance branches with cherry-pick support. |
| **[Rollback](rollback.md)** | Undo a release — delete tags, releases, and yank from registries. |
| **[Concurrency & Locking](concurrency.md)** | Prevent concurrent releases and understand parallel publishing. |
| **[Announcements](announcements.md)** | Notify your team via Slack, Discord, Teams, and more. |

---

## :material-shield-lock: Security & Compliance

| Guide | Description |
|-------|-------------|
| **[Overview](compliance.md)** | OSPS Baseline compliance evaluation across all ecosystems. |
| **[Signing & Verification](signing.md)** | Sign artifacts with Sigstore keyless signing and verify them. |
| **[SLSA Provenance](slsa-provenance.md)** | Generate and verify SLSA Provenance v1 attestations for artifacts. |
| **[SBOM Generation](sbom.md)** | Generate Software Bills of Materials (CycloneDX & SPDX). |
| **[Trust & Verification](trust.md)** | Enforce trust for lifecycle hooks and backend plugins. |
| **[Vulnerability Scanning](vulnerability-scanning.md)** | Scan dependencies for known vulnerabilities via OSV.dev. |
| **[OpenSSF Scorecard](scorecard.md)** | Run local security best-practice checks. |
| **[Security Insights](security-insights.md)** | Generate SECURITY-INSIGHTS.yml for your project. |

---

## :material-robot: CI/CD & Operations

| Guide | Description |
|-------|-------------|
| **[CI/CD Integration](ci-cd.md)** | GitHub Actions, GitLab CI, and Bitbucket Pipelines. |
| **[Workflow Templates](workflow-templates.md)** | Production-ready GitHub Actions workflows you can copy-paste. |
| **[Health Checks & Doctor](health-checks.md)** | Validate your workspace before releasing with `check` and `doctor`. |
| **[Observability](observability.md)** | OpenTelemetry tracing and pipeline profiling for releases. |
| **[Skipping Checks](skip-checks.md)** | Bypass specific health checks for individual packages. |

---

## :material-wrench: Troubleshooting

| Guide | Description |
|-------|-------------|
| **[Error Codes](error-codes.md)** | Every `RK-*` error code with causes and fixes. |
| **[FAQ](faq.md)** | Common questions for release managers — beginner to expert. |
