---
title: OpenSSF Scorecard
description: Run local security best-practice checks aligned with OpenSSF Scorecard.
---

# OpenSSF Scorecard Checks

ReleaseKit implements a subset of [OpenSSF Scorecard](https://securityscorecards.dev/)
checks that run **locally** without the Scorecard API. These
file-existence and configuration-pattern checks verify that your
repository follows security best practices.

---

## Checks

| Check | What It Verifies |
|-------|-----------------|
| **SECURITY.md** | `SECURITY.md` exists at the repo root |
| **Dependency-Update-Tool** | Dependabot or Renovate is configured |
| **CI-Tests** | CI workflow files exist (`.github/workflows/`) |
| **Pinned-Dependencies** | CI workflows pin actions by SHA, not tag |
| **Token-Permissions** | Workflows avoid `permissions: write-all` |
| **Signed-Releases** | `.sigstore.json` bundles exist for artifacts |

---

## CLI Usage

```bash
# Run all Scorecard checks.
releasekit check --scorecard

# Output:
# ✅ SECURITY.md: Found at /repo/SECURITY.md
# ✅ Dependency-Update-Tool: dependabot.yml found
# ⚠️  Pinned-Dependencies: 2 workflow files use tag-based action refs
#    hint: Pin actions by SHA: uses: actions/checkout@abc123...
# ✅ CI-Tests: 3 workflow files found
# ✅ Token-Permissions: No overly permissive top-level permissions
# ⚠️  Signed-Releases: No .sigstore.json bundles found
#    hint: Enable signing with: releasekit publish --sign
```

---

## Fixing Issues

### Pin Actions by SHA

```yaml
# ❌ Tag-based (vulnerable to tag mutation).
uses: actions/checkout@v4

# ✅ SHA-pinned (immutable).
uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
```

### Add SECURITY.md

```bash
# ReleaseKit can generate one for you.
releasekit init --security-md
```

### Least-Privilege Permissions

```yaml
# ❌ Overly permissive.
permissions: write-all

# ✅ Least-privilege.
permissions:
  contents: read
  packages: write
```

---

## Integration with Preflight

Scorecard checks run when you pass `--scorecard` to `releasekit check`.
They also run automatically as part of the publish preflight validation.
Failures produce warnings (not blocking), encouraging gradual adoption.
