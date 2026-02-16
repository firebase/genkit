---
title: Security Insights
description: Generate SECURITY-INSIGHTS.yml for communicating your project's security posture.
---

# Security Insights

ReleaseKit generates a machine-readable `SECURITY-INSIGHTS.yml` file
that communicates your project's security posture to consumers,
security researchers, and automated tools.

---

## What Is SECURITY-INSIGHTS.yml?

A standardized YAML file (schema v2.0.0) consumed by:

- [CLOMonitor](https://clomonitor.io/) — CNCF project health dashboard
- [LFX Insights](https://insights.lfx.linuxfoundation.org/) — Linux Foundation metrics
- [OSPS Baseline Scanner](https://github.com/ossf/osps-baseline) — OpenSSF compliance

It describes:

| Section | Content |
|---------|---------|
| **Header** | Schema version, last updated/reviewed dates |
| **Project** | Name, admins, repos, vulnerability reporting policy |
| **Repository** | License, security tools, assessment status, SBOM, signing |

---

## CLI Usage

```bash
# Generate SECURITY-INSIGHTS.yml during init.
releasekit init --security-insights

# It is also auto-updated as part of preflight during publish.
releasekit publish --dry-run
```

---

## Configuration

```toml
[security_insights]
project_name = "Genkit"
project_url = "https://github.com/firebase/genkit"
repo_url = "https://github.com/firebase/genkit"
license = "Apache-2.0"
vuln_reporting_url = "https://github.com/firebase/genkit/security/advisories"

[security_insights.contacts]
name = "Security Team"
email = "security@example.com"
primary = true
```

---

## Auto-Detected Security Tools

ReleaseKit auto-populates the security tools section based on what
it detects in your repository:

| Tool | Type | Detected By |
|------|------|------------|
| Dependabot | SCA | `.github/dependabot.yml` |
| Renovate | SCA | `renovate.json` |
| Ruff | SAST/linter | `pyproject.toml` config |
| pip-audit | SCA | CI workflow |
| Sigstore | Signing | Signing config |
| ReleaseKit | Release Management | `releasekit.toml` |
