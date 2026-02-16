---
title: Skipping Checks Per-Package
description: How to bypass specific health checks for individual packages.
---

# Skipping Checks Per-Package

Sometimes a package legitimately doesn't need a particular health check.
For example, an internal CLI tool doesn't need `requires_python`, or a
sample app doesn't need `publish_classifier_consistency`.

Rather than disabling the check globally, releasekit lets you skip
checks on a per-package basis.

## ELI5: What Is This?

```text
Your workspace has 20 packages. All of them get checked for
33 different things (like "does it have a LICENSE?").

But one package — "my-internal-tool" — is never published.
It doesn't need the "requires_python" check.

Instead of turning off that check for EVERYONE, you can say:
"Skip requires_python for my-internal-tool only."

Everyone else still gets checked. Only the gym teacher
skips the tie check. 🏋️
```

## Configuration

### Workspace-Level Skips

Skip checks for ALL packages in a workspace:

```toml
[workspace.py]
ecosystem = "python"
root = "py"

# These checks are skipped for every package in this workspace
skip_checks = ["stale_artifacts", "lockfile_staleness"]
```

### Per-Package Skips

Skip checks for ONE specific package:

```toml
[workspace.py.packages."my-internal-tool"]
skip_checks = ["requires_python", "publish_classifier_consistency"]
```

### Combined Example

```toml
[workspace.py]
ecosystem = "python"
root = "py"
# Workspace-wide: skip stale_artifacts for all packages
skip_checks = ["stale_artifacts"]

[workspace.py.packages."my-internal-tool"]
# This package skips stale_artifacts (inherited) + requires_python
skip_checks = ["requires_python"]

[workspace.py.packages."my-sample-app"]
# This package skips stale_artifacts (inherited) + naming_convention
skip_checks = ["naming_convention"]
```

The effective skip set for each package is the **union** of
workspace-level and per-package skips:

```text
my-internal-tool → {"stale_artifacts", "requires_python"}
my-sample-app    → {"stale_artifacts", "naming_convention"}
everything-else  → {"stale_artifacts"}
```

## Available Check Names

### Universal Checks

| Check Name | What It Checks |
|------------|---------------|
| `cycles` | Circular dependency chains |
| `self_deps` | Package depends on itself |
| `orphan_deps` | Internal dep not in workspace |
| `missing_license` | No LICENSE file |
| `missing_readme` | No README.md |
| `stale_artifacts` | Leftover .bak or dist/ files |
| `ungrouped_packages` | Package not in any group |
| `lockfile_staleness` | Lockfile out of sync |

### Language-Specific Checks (Python)

| Check Name | What It Checks |
|------------|---------------|
| `type_markers` | py.typed PEP 561 marker |
| `version_consistency` | Plugin version matches core |
| `naming_convention` | Directory matches package name |
| `metadata_completeness` | pyproject.toml required fields |
| `python_version_consistency` | Consistent requires-python |
| `python_classifiers` | Python version classifiers |
| `dependency_resolution` | uv pip check passes |
| `namespace_init` | No \_\_init\_\_.py in namespace dirs |
| `readme_field` | readme declared in [project] |
| `changelog_url` | Changelog in [project.urls] |
| `publish_classifier_consistency` | Private classifier matches exclude_publish |
| `test_filename_collisions` | No duplicate test paths |
| `build_system` | [build-system] present |
| `version_field` | version present or dynamic |
| `duplicate_dependencies` | No duplicate deps |
| `pinned_deps_in_libraries` | Libraries don't pin with == |
| `requires_python` | requires-python declared |
| `readme_content_type` | Readme extension matches content-type |
| `version_pep440` | PEP 440 compliant version |
| `placeholder_urls` | No placeholder URLs |
| `legacy_setup_files` | No setup.py or setup.cfg |
| `deprecated_classifiers` | No deprecated classifiers |
| `license_classifier_mismatch` | License classifier matches LICENSE |
| `unreachable_extras` | Optional deps reference valid packages |
| `self_dependencies` | Package not in own deps |
| `distro_deps` | Distro packaging dep sync |

## How It Works Internally

```text
┌─────────────────────────────────────────────────────────────┐
│                     Check Runner                              │
│                                                             │
│  1. Build skip_map from config:                             │
│     {"my-tool": {"requires_python"}, ...}                   │
│                                                             │
│  2. For each check (e.g. "requires_python"):                │
│     a. Start with all packages: [A, B, C, D]               │
│     b. Filter out packages that skip this check             │
│     c. Run check on filtered list: [A, B, D]               │
│                                                             │
│  3. Skipped packages are NOT reported as pass or fail —     │
│     they simply don't participate in that check.            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

The filtering happens in the check runner (`_runner.py`), not in
individual check functions. This means:

- Check functions don't need to know about skipping
- The same mechanism works for all checks (universal + language-specific)
- Adding new checks automatically respects skip_checks

## CLI Flag: --skip-check

You can also skip checks per invocation without editing config:

```bash
# Skip a check for this run only
releasekit check --skip-check stale_artifacts

# Skip multiple checks
releasekit check --skip-check stale_artifacts --skip-check lockfile_staleness
```

CLI `--skip-check` flags are merged with config-based skips.

## Best Practices

1. **Be specific.** Skip the narrowest check possible, not a broad
   category.

2. **Document why.** Add a TOML comment explaining the skip:
   ```toml
   [workspace.py.packages."my-internal-tool"]
   # Internal tool, never published — doesn't need publish checks
   skip_checks = ["requires_python", "publish_classifier_consistency"]
   ```

3. **Prefer per-package over workspace-level.** Workspace-level skips
   affect every package. Use them only for checks that genuinely
   don't apply to the entire workspace.

4. **Review periodically.** A skip that made sense 6 months ago may
   no longer be needed. Audit your skip_checks when adding new packages.
