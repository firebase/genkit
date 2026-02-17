---
title: Security & Compliance
description: Understand and evaluate your project's security posture with OSPS Baseline controls.
---

# Security & Compliance Guide

releasekit includes a built-in compliance evaluator that checks your
repository against the [OpenSSF OSPS Baseline](https://best.openssf.org/Concise-Guide-for-Evaluating-Open-Source-Software)
framework and maps findings to NIST SSDF tasks.

## ELI5: What Is This About?

```text
When you publish a package, people trust you with their software.
Compliance = proving you take that trust seriously.

Think of it like food safety ratings for restaurants:

  ⭐ Level 1 = "We have a kitchen and a license"
    → You have a LICENSE, SECURITY.md, and an ingredient list (SBOM)

  ⭐⭐ Level 2 = "We also have health inspections"
    → Your packages are signed, dependencies are locked,
      and you scan for known vulnerabilities

  ⭐⭐⭐ Level 3 = "Independent lab-tested"
    → Your builds run in isolated environments with
      cryptographically signed provenance
```

## Quick Start

```bash
# See your compliance status as a table
releasekit compliance

# Get machine-readable JSON output
releasekit compliance --format json
```

Example output:

```text
ID             Control                             Level Status    Module                         Notes
--------------------------------------------------------------------------------------------------------------
OSPS-SCA-01    SBOM generation                     L1    ✅ met    sbom.py                        CycloneDX 1.5 + SPDX 2.3
OSPS-GOV-01    Security policy (SECURITY.md)       L1    ✅ met    scorecard.py
OSPS-LEG-01    License declared                    L1    ✅ met
OSPS-SCA-02    Signed release artifacts            L2    ✅ met    signing.py                     Sigstore keyless signing
OSPS-SCA-03    Provenance attestation              L2    ✅ met    provenance.py                  in-toto SLSA Provenance v1
OSPS-SCA-04    Vulnerability scanning              L2    ⚠️ partial preflight.py / osv.py         pip-audit + OSV (partial)
OSPS-SCA-05    Dependency pinning (lockfile)        L2    ✅ met    preflight.py                   uv.lock
ECO-PY-01      PEP 561 type markers (py.typed)     L1    ✅ met    checks/_python.py
ECO-PY-02      PEP 740 publish attestations        L2    ❌ gap    attestations.py

9/10 controls met.
```

## How Ecosystem Detection Works

releasekit automatically detects which ecosystems are present by
looking for canonical manifest files:

| Ecosystem | Detected By |
|-----------|-------------|
| Python | `pyproject.toml`, `setup.py`, `uv.lock`, `Pipfile` |
| Go | `go.mod`, `go.sum` |
| JavaScript | `package.json`, `pnpm-lock.yaml`, `yarn.lock` |
| Java | `pom.xml`, `build.gradle`, `build.gradle.kts` |
| Rust | `Cargo.toml`, `Cargo.lock` |
| Dart | `pubspec.yaml`, `pubspec.lock` |

Only controls relevant to detected ecosystems are evaluated.
You can also pass ecosystems explicitly via the Python API:

```python
from releasekit.compliance import evaluate_compliance

controls = evaluate_compliance(
    repo_root,
    ecosystems=frozenset({"python", "go"}),
)
```

## Universal Controls

These apply to every project regardless of language:

### Level 1 — Basics

- **SBOM generation** (`OSPS-SCA-01`): Do you generate a Software
  Bill of Materials? releasekit produces both CycloneDX 1.5 and
  SPDX 2.3 formats.

- **Security policy** (`OSPS-GOV-01`): Is there a `SECURITY.md`
  telling users how to report vulnerabilities?

- **License** (`OSPS-LEG-01`): Is there a `LICENSE` file?

### Level 2 — Hardened

- **Signed artifacts** (`OSPS-SCA-02`): Are release artifacts
  signed with Sigstore? This proves they came from your CI.

- **Provenance** (`OSPS-SCA-03`): Is there an in-toto SLSA
  provenance attestation? This proves *what* was built, *where*,
  and *from which source*.

- **Vulnerability scanning** (`OSPS-SCA-04`): Are dependencies
  scanned for known CVEs? releasekit checks for ecosystem-specific
  tools (pip-audit, govulncheck, npm audit, cargo-audit, etc.)
  plus the OSV database.

- **Lockfile** (`OSPS-SCA-05`): Is there a lockfile pinning
  exact dependency versions? (uv.lock, go.sum, Cargo.lock, etc.)

- **Dependency updates** (`OSPS-SCA-06`): Is Dependabot or
  Renovate configured for automated dependency updates?

### Level 3 — Isolated

- **Build isolation** (`OSPS-BLD-01`): Are builds running on
  hosted runners (SLSA Build L3)?

- **Signed provenance** (`OSPS-BLD-02`): Is the provenance
  itself signed with Sigstore?

## Ecosystem-Specific Controls

Each ecosystem has its own security requirements. These are only
evaluated when that ecosystem is detected in your repo.

### Python

| Control | Why It Matters |
|---------|---------------|
| **PEP 561 type markers** | `py.typed` enables downstream type checking, catching bugs before runtime |
| **PEP 740 attestations** | PyPI Trusted Publisher attestations prove packages came from your CI |
| **requires-python** | Prevents users from installing on incompatible Python versions |

### Go

| Control | Why It Matters |
|---------|---------------|
| **go.mod** | Required for reproducible builds and dependency management |
| **go.sum** | Cryptographic hashes verify no dependency was tampered with |
| **govulncheck** | Scans against the Go vulnerability database (more precise than CVE-based tools) |

### JavaScript

| Control | Why It Matters |
|---------|---------------|
| **package.json** | Required manifest for npm/pnpm packages |
| **npm provenance** | `--provenance` flag creates Sigstore-backed attestations on npm |
| **.npmrc** | Explicit registry pinning prevents dependency confusion attacks |

### Java

| Control | Why It Matters |
|---------|---------------|
| **Build manifest** | pom.xml or build.gradle required for builds |
| **Gradle dep verification** | `verification-metadata.xml` verifies checksums/signatures of all deps |
| **Maven Central signing** | Maven Central requires GPG-signed artifacts for publication |

### Rust

| Control | Why It Matters |
|---------|---------------|
| **Cargo.toml** | Required manifest for Rust crates |
| **Cargo.lock** | Must be committed for reproducible builds (especially binaries) |
| **cargo-audit** | Scans against the RustSec advisory database |
| **cargo-deny** | Enforces license allowlists and bans known-bad crates |

### Dart

| Control | Why It Matters |
|---------|---------------|
| **pubspec.yaml** | Required manifest for Dart/Flutter packages |
| **pubspec.lock** | Committed lockfile for reproducible builds |
| **analysis_options.yaml** | Strict static analysis catches type errors and security issues |

### Kotlin / KMP (planned)

| Control | Why It Matters |
|---------|---------------|
| **build.gradle.kts** | Required build manifest for Kotlin projects |
| **Gradle dep verification** | `verification-metadata.xml` verifies checksums/signatures |
| **Maven Central signing** | GPG-signed artifacts required for Maven Central publication |

### Swift (planned)

| Control | Why It Matters |
|---------|---------------|
| **Package.swift** | Required manifest for Swift packages |
| **Package.resolved** | Committed lockfile for reproducible builds |

### Ruby (planned)

| Control | Why It Matters |
|---------|---------------|
| ***.gemspec** | Required manifest for Ruby gems |
| **Gemfile.lock** | Committed lockfile for reproducible builds |
| **bundler-audit** | Scans against the Ruby Advisory Database |

### .NET (planned)

| Control | Why It Matters |
|---------|---------------|
| ***.csproj / *.fsproj** | Required project manifest |
| **NuGet signing** | Signed packages for NuGet Gallery publication |
| **dotnet list package --vulnerable** | Scans for known vulnerabilities |

### PHP (planned)

| Control | Why It Matters |
|---------|---------------|
| **composer.json** | Required manifest for PHP packages |
| **composer.lock** | Committed lockfile for reproducible builds |
| **local-php-security-checker** | Scans against the PHP Security Advisories Database |

## Improving Your Score

### From Gap to Met

1. **Missing SECURITY.md?** Create one:
   ```bash
   cat > SECURITY.md << 'EOF'
   # Security Policy

   ## Reporting a Vulnerability

   Please report security vulnerabilities to security@example.com.
   Do NOT open a public issue.
   EOF
   ```

2. **Missing lockfile?** Generate one:
   ```bash
   uv lock          # Python
   go mod tidy      # Go
   pnpm install     # JavaScript
   cargo generate-lockfile  # Rust
   ```

3. **No Dependabot?** Add `.github/dependabot.yml`:
   ```yaml
   version: 2
   updates:
     - package-ecosystem: pip
       directory: "/"
       schedule:
         interval: weekly
   ```

4. **No signing?** Enable in your workflow:
   ```yaml
   permissions:
     id-token: write  # Required for Sigstore OIDC
   ```

## Using in CI

Add a compliance gate to your CI pipeline:

```yaml
- name: Check compliance
  run: |
    releasekit compliance --format json > compliance.json
    # Fail if any L1 controls are gaps
    python -c "
    import json, sys
    controls = json.load(open('compliance.json'))
    l1_gaps = [c for c in controls if c['osps_level'] == 'L1' and c['status'] == 'gap']
    if l1_gaps:
        for g in l1_gaps:
            print(f'  ❌ {g[\"id\"]}: {g[\"control\"]}')
        sys.exit(1)
    print('✅ All L1 controls met')
    "
```
