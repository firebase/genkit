---
title: Dependency Pinning
description: How ReleaseKit handles internal dependency versions during publishing.
---

# Dependency Pinning

When publishing packages from a monorepo, internal dependencies
(packages that depend on other packages in the same workspace) need
their version constraints updated to point to the **exact version**
being released — not the `workspace:*` or editable reference used
during development.

ReleaseKit handles this automatically with **ephemeral dependency
pinning**.

---

## How It Works

```text
Before publish:
  genkit-plugin-google-genai/pyproject.toml:
    dependencies = ["genkit"]  # workspace source reference

During publish (ephemeral pin):
  genkit-plugin-google-genai/pyproject.toml:
    dependencies = ["genkit==0.5.0"]  # exact pin

After publish (restored):
  genkit-plugin-google-genai/pyproject.toml:
    dependencies = ["genkit"]  # back to workspace reference
```

The pinning is **ephemeral** — `pyproject.toml` files are modified
in-place for the build step, then **restored** to their original
content immediately after, regardless of success or failure.

---

## Why Ephemeral?

- **Development stays ergonomic** — developers keep using workspace
  references (`genkit` resolved via `[tool.uv.sources]`).
- **Published packages are correct** — consumers get exact version
  pins that match the release.
- **No commit noise** — the pin/unpin cycle doesn't create permanent
  changes.

---

## Pin Format

| Ecosystem | Development | Pinned |
|-----------|------------|--------|
| Python (uv) | `"genkit"` (workspace source) | `"genkit==0.5.0"` |
| JavaScript (pnpm) | `"workspace:*"` | `"0.5.0"` |
| Go | `replace` directive | Removed for publish |

---

## Safety Guarantees

1. **Atomic restore** — `pyproject.toml` is restored in a `finally`
   block, so even if the build fails, the file is never left modified.
2. **Backup copy** — a `.bak` copy is created before modification.
3. **Verification** — after restore, a checksum is compared to ensure
   the file matches the original.

---

## Configuration

Pinning is enabled by default. To disable:

```toml
[workspace.py]
# Disable ephemeral pinning (not recommended).
pin_dependencies = false
```

---

## Debugging

```bash
# Show what would be pinned without modifying files.
releasekit plan --show-pins

# Output:
# genkit-plugin-google-genai:
#   genkit: workspace → ==0.5.0
# genkit-plugin-firebase:
#   genkit: workspace → ==0.5.0
#   genkit-plugin-google-genai: workspace → ==0.5.0
```
