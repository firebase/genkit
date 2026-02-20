---
title: Trust & Verification
description: Enforce trust for lifecycle hooks and backend plugins.
---

# Trust & Verification

ReleaseKit enforces a trust chain for lifecycle hooks and backend
plugins. In **strict mode** (default in CI), unsigned or untrusted
extensions are refused.

---

## Hook Allowlist

By default, only these executables are allowed in lifecycle hooks:

| Executable | Ecosystem |
|-----------|-----------|
| `uv` | Python |
| `pnpm`, `npm`, `npx` | JavaScript |
| `go` | Go |
| `cargo` | Rust |
| `dart`, `pub` | Dart |
| `mvn`, `gradle` | Java |
| `bazel` | Bazel |

Commands using unlisted executables are rejected in strict mode:

```text
error[RK-TRUST-HOOK-DENIED]: Hook command uses disallowed executable 'curl'.
  |
  = hint: Add 'curl' to hook_allowlist in [trust] config, or use a
    wrapper script pinned by SHA-256 digest.
```

---

## Configuration

```toml
[trust]
# Additional executables to allow in hooks.
hook_allowlist = ["curl", "jq"]

# Strict mode: refuse unpinned scripts (default: true in CI).
strict_hooks = true

# Pin scripts by SHA-256 digest for integrity verification.
[trust.pinned_scripts]
"scripts/custom-build.sh" = "e3b0c44298fc1c149afbf4c8996fb924..."
```

---

## Pinning Scripts

For custom scripts, pin them by SHA-256 digest:

```bash
# Compute the digest.
sha256sum scripts/custom-build.sh
# e3b0c44298fc1c149afbf4c8996fb924...  scripts/custom-build.sh

# Add to config.
[trust.pinned_scripts]
"scripts/custom-build.sh" = "e3b0c44298fc1c149afbf4c8996fb924..."
```

If the script's content changes, the digest won't match and the hook
will be refused — preventing supply chain attacks via modified scripts.

---

## Trusted Publishers

For backend plugin packages, verify that they come from a trusted
OIDC publisher:

```toml
[trust.trusted_publishers]
"releasekit-backend-go" = [
    "https://token.actions.githubusercontent.com",
]
```

---

## Strict vs. Permissive Mode

| | Strict (CI default) | Permissive (local default) |
|--|-----|------|
| Unknown executables | ❌ Refused | ⚠️ Warning |
| Unpinned scripts | ❌ Refused | ⚠️ Warning |
| Disallowed commands | ❌ Refused | ⚠️ Warning |

Override with:

```bash
# Force strict mode locally.
releasekit publish --strict

# Disable strict mode in CI (not recommended).
RELEASEKIT_STRICT=false releasekit publish
```
