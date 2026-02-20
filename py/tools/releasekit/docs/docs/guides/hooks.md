---
title: Lifecycle Hooks
description: Execute custom scripts at specific points in the release pipeline.
---

# Lifecycle Hooks

Hooks let you execute shell commands at specific points in the release
pipeline. Use them for custom build steps, notifications, validation,
or cleanup.

---

## Hook Events

| Event | When | Use Case |
|-------|------|----------|
| `before_prepare` | Before version bumps and changelog generation | Pre-release validation |
| `before_publish` | Before publishing to registries | Build artifacts, run tests |
| `after_publish` | After all packages are published | Deploy docs, update CDN |
| `after_tag` | After git tags are created | Trigger downstream CI |

---

## Configuration

Define hooks in `releasekit.toml`:

```toml
[hooks]
before_prepare = [
    "uv run pytest tests/",
]
before_publish = [
    "uv run python -m build",
]
after_publish = [
    "uv run mkdocs gh-deploy --force",
]
after_tag = [
    "echo 'Release ${version} tagged as ${tag}'",
]
```

---

## Template Variables

Hook commands support placeholder expansion:

| Variable | Description | Example |
|----------|-------------|---------|
| `${version}` | The release version | `0.5.0` |
| `${name}` | Package name (per-package hooks) | `genkit` |
| `${tag}` | Git tag name | `genkit-v0.5.0` |

```toml
[hooks]
after_tag = ["curl -X POST https://api.example.com/deploy?version=${version}"]
```

---

## Hook Merge Semantics

Hooks can be defined at three levels, and by default they
**concatenate** (all three tiers run in order):

```text
Root hooks (releasekit.toml)
  + Workspace hooks ([workspace.py])
  + Package hooks ([packages.genkit])
  = Effective hooks (all three, in order)
```

To **replace** instead of concatenate, set `hooks_replace = true`:

```toml
[workspace.py]
hooks_replace = true  # Only workspace-level hooks run.

[workspace.py.hooks]
before_publish = ["uv build"]
```

---

## Failure Behavior

- Hooks execute **sequentially** within each event.
- If a hook **fails** (non-zero exit), execution **stops** — remaining
  hooks for that event are skipped.
- Hook failures in `before_*` events abort the release pipeline.
- Hook failures in `after_*` events are logged as errors but do not
  undo the release.

---

## Trust Verification

In CI (strict mode), ReleaseKit verifies that hook commands use
executables from a trusted allowlist. See
[Trust & Verification](trust.md) for details.

---

## Dry Run

With `--dry-run`, hooks are logged but not executed:

```bash
releasekit publish --dry-run
# [hook] before_publish: uv run python -m build (dry_run=True)
```
