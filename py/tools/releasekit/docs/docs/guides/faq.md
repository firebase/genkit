---
title: FAQ
description: Frequently asked questions for release managers using ReleaseKit.
---

# FAQ

Common questions a release manager would want answers to.

---

## Rollbacks & Recovery

### How do I rollback a release?

Use the `rollback` command to delete a tag and its associated GitHub Release:

```bash
# Delete a tag locally and on the remote
releasekit rollback --tag genkit-v1.2.3

# Delete only the local tag (keep the remote)
releasekit rollback --tag genkit-v1.2.3 --no-remote
```

This removes the git tag and the GitHub/GitLab release entry. It does **not**
yank the package from the registry — see the next question.

### Can I unpublish a package from PyPI/npm?

**PyPI:** You cannot delete a published version. You can
[yank](https://pypi.org/help/#yanked) it via the PyPI web UI, which hides it
from default installs but still allows pinned installs. For security issues,
contact PyPI support.

**npm:** You can `npm unpublish <pkg>@<version>` within 72 hours of
publishing. After that, you must contact npm support.

ReleaseKit does not automate yanking or unpublishing because these are
destructive, irreversible operations that should require human judgment.

### A publish failed halfway through. What now?

ReleaseKit tracks publish state in a crash-safe state file
(`releasekit--state--<label>.json`). If a publish is interrupted:

```bash
# Resume exactly where it left off
releasekit publish
```

Packages that already published successfully are skipped. Only pending and
failed packages are retried. The state file is cleaned up automatically
after a successful run.

### The Release PR was merged but `release` failed. Can I re-run it?

Yes. The `release` command is idempotent for tag creation — if a tag already
exists, it skips it. Re-run:

```bash
releasekit release
```

Or in CI, simply re-trigger the workflow.

---

## Version Bumps

### How are version bumps computed?

ReleaseKit parses [Conventional Commits](https://www.conventionalcommits.org/)
since the last tag for each package:

| Commit prefix                                     | Bump      |
| ------------------------------------------------- | --------- |
| `fix:`, `perf:`, `revert:`                         | **PATCH** |
| `feat:`                                            | **MINOR** |
| `feat!:`, `fix!:`, any `BREAKING CHANGE:` footer   | **MAJOR** |

Only commits that touch files within a package's directory are counted.
The highest bump wins (e.g., one `feat!:` + ten `fix:` = MAJOR).

### What if I want to force a specific version?

ReleaseKit does not support arbitrary version overrides — versions are
always derived from commit history. If you need to force a bump:

1. Add an empty commit with the desired prefix:

   ```bash
   git commit --allow-empty -m "feat!: force major bump for API redesign"
   ```

2. Run `releasekit plan` to verify.

### A package has no changes but I want to release it anyway

Use `--force-unchanged`:

```bash
releasekit plan --force-unchanged
releasekit publish --force-unchanged
```

This includes packages with zero commits since their last tag, bumping
them by PATCH.

### How does dependency-triggered bumping work?

When package A depends on package B, and B gets a version bump, A is
automatically bumped too (at least PATCH). This propagates transitively
through the dependency graph using BFS on reverse edges.

Example: if `genkit-plugin-firebase` depends on `genkit` and `genkit` gets
a MINOR bump, `genkit-plugin-firebase` gets at least a PATCH bump even if
it has no new commits.

### What happens with `revert:` commits?

ReleaseKit detects both `revert:` prefix and `Revert "..."` format. A
revert commit cancels out the bump from the original commit. For example,
if a `feat:` is followed by a `revert:` of that feat, the net bump from
those two commits is zero.

---

## Workspaces & Groups

### What is the difference between a workspace and a group?

| Concept       | Scope                                         | Purpose                                          |
| ------------- | --------------------------------------------- | ------------------------------------------------ |
| **Workspace** | A directory tree with its own ecosystem/tool  | Separate release pipeline (branch, tags, state)  |
| **Group**     | A named set of glob patterns within a workspace | Filter which packages to include in a release  |

Workspaces are defined as `[workspace.<label>]` sections in
`releasekit.toml`. Each workspace gets its own release branch
(`releasekit--release--<label>`), state file, and tags.

Groups are defined within a workspace's config and used with `--group`
to selectively release a subset of packages.

### Can a package belong to multiple groups?

Yes, within the same workspace. Groups are just filters — a package
matching multiple groups simply appears when you use `--group` with any
of them. Versioning is computed once per workspace, not per group, so
there is no conflict.

### Can a package belong to two workspaces?

**No.** Each package must be discovered by exactly one workspace. If two
workspaces have overlapping `root` directories, the same package could be
discovered twice, leading to conflicting version bumps, duplicate tags,
and double publishes. The `check` command warns about this.

### How do I release only Python packages in a multi-ecosystem monorepo?

Use the `--workspace` flag (once implemented) or configure separate
workspace sections:

```toml
[workspace.py]
ecosystem = "python"
root = "py"

[workspace.js]
ecosystem = "js"
root = "js"
```

Then run:

```bash
releasekit publish --workspace py
```

### How do I exclude a package from publishing but still bump its version?

Add it to `exclude_publish`:

```toml
[workspace.py]
exclude_publish = ["internal-test-helpers", "group:samples"]
```

The package still gets version bumps and changelog entries, but
`releasekit publish` skips it.

### How do I exclude a package from everything?

Add it to `exclude` to skip it during discovery entirely:

```toml
[workspace.py]
exclude = ["experimental-*", "scratch-*"]
```

---

## Release PRs & CI

### How does the Release PR work?

1. `releasekit prepare` runs on push to `main`.
2. It computes bumps, updates `pyproject.toml` versions, generates
   changelogs, and commits everything to a release branch
   (`releasekit--release--<label>`).
3. It opens (or updates) a PR from that branch to `main` with the
   label `autorelease: pending`.
4. A human reviews and merges the PR.
5. On merge, `releasekit release` creates git tags and GitHub Releases.
6. Then `releasekit publish` uploads packages to registries.

### The Release PR keeps getting updated. Is that normal?

Yes. Every push to `main` triggers `releasekit prepare`, which
force-pushes to the release branch and updates the PR body with the
latest version manifest. This is by design — the PR always reflects
the current state of `main`.

### Can I have multiple Release PRs open at once?

One per workspace. Each workspace has its own release branch
(`releasekit--release--<label>`), so `workspace.py` and `workspace.js`
can have independent Release PRs open simultaneously.

### How do I test a release without publishing to the real registry?

```bash
# Dry run — no uploads, no tags, no PRs
releasekit publish --dry-run

# Publish to Test PyPI
releasekit publish \
  --index-url https://test.pypi.org/simple/ \
  --check-url https://test.pypi.org/simple/
```

### How do I re-run a failed CI release?

Simply re-trigger the GitHub Actions workflow. All ReleaseKit commands
are idempotent:

- `prepare` — force-pushes the release branch (safe to re-run).
- `release` — skips tags that already exist.
- `publish` — resumes from the crash-safe state file, skipping
  already-published packages.

---

## Configuration

### Where does ReleaseKit look for its config?

It looks for `releasekit.toml` at the repository root. The file uses
top-level keys (no `[tool.releasekit]` nesting) so it works for any
ecosystem.

### How do I set up a new monorepo?

```bash
releasekit init
```

This auto-detects ecosystems (by looking for `pyproject.toml`,
`package.json`, `go.mod`, `Cargo.toml`, etc.) and generates a
`releasekit.toml` with sensible defaults.

### What tag format should I use?

The default `{name}-v{version}` (e.g., `genkit-v1.2.3`) works well for
monorepos with multiple packages. For single-package repos, you might
prefer:

```toml
[workspace.main]
tag_format = "v{version}"
```

### What does `synchronize = true` do?

It forces all packages in the workspace to share the same version number.
When any package gets a bump, all packages are bumped to the same version.
Useful for tightly coupled package suites.

### What is `major_on_zero`?

By default, breaking changes on `0.x` versions produce MINOR bumps (per
semver spec, `0.x` has no stability guarantees). Setting
`major_on_zero = true` makes breaking changes produce MAJOR bumps even
on `0.x`.

---

## Versioning Schemes

### What versioning scheme does my project use?

ReleaseKit auto-detects the right scheme based on your ecosystem:

| Ecosystem | Default Scheme | Pre-release Example |
|-----------|---------------|---------------------|
| Python | `pep440` | `1.2.0rc1` |
| JS, Go, Rust, Dart, Java | `semver` | `1.2.0-rc.1` |

Python uses PEP 440 because PyPI **requires** it. Everything else uses
semver. You almost never need to think about this.

### Can I use semver for a Python package?

Yes. Override the default in your workspace config:

```toml
[workspace.py]
ecosystem = "python"
versioning_scheme = "semver"
```

!!! warning
    PyPI may reject semver pre-release versions like `1.0.0-rc.1`
    (the hyphen is not PEP 440 compliant). Stable versions like
    `1.2.3` work fine with either scheme.

### What is CalVer and when should I use it?

CalVer (Calendar Versioning) uses dates as version numbers, like
`2026.02.3`. It's good for projects that release on a fixed schedule
and don't make semver-style compatibility promises (e.g., Ubuntu,
pip, Black).

```toml
[workspace.py]
versioning_scheme = "calver"
calver_format = "YYYY.MM.MICRO"
```

### Can different packages in the same workspace use different schemes?

Yes! Use per-package configuration:

```toml
[workspace.mono]
ecosystem = "python"
versioning_scheme = "pep440"  # default for all

[workspace.mono.packages."my-js-wrapper"]
versioning_scheme = "semver"  # this one uses semver
```

See [Per-Package Configuration](per-package-config.md) for details.

---

## Per-Package Configuration

### What can I override per-package?

These fields: `versioning_scheme`, `calver_format`, `prerelease_label`,
`changelog`, `changelog_template`, `smoke_test`, `major_on_zero`,
`extra_files`, `dist_tag`, `registry_url`, `provenance`.

### How does the override resolution work?

Most specific wins:

1. **Exact package name** — `[workspace.X.packages."my-pkg"]`
2. **Group membership** — `[workspace.X.packages.my-group]`
3. **Workspace default** — `[workspace.X]`

### Can I override settings for a group of packages at once?

Yes. Use the group name as the key:

```toml
[workspace.mono.groups]
plugins = ["myorg-plugin-*"]

[workspace.mono.packages.plugins]
changelog = false
provenance = true
```

All packages matching `myorg-plugin-*` get these overrides.

### What happens if a package matches both an exact name and a group?

The exact name match wins. Group overrides are only used when there
is no exact match.

---

## Rollback

### Can I rollback from the GitHub Release page?

Yes, if you use the **Release with Rollback** workflow template.
It adds a "Rollback this release" link to every GitHub Release that
triggers a rollback workflow with one click.

See [Workflow Templates](workflow-templates.md#template-5-release-with-rollback-button)
for the full setup.

### What does rollback actually do?

`releasekit rollback --tag <tag>` does two things:

1. Deletes the git tag (locally and on the remote)
2. Deletes the associated GitHub/GitLab Release

It does **not** yank or unpublish packages from registries. That
requires manual action — see "Can I unpublish a package?" above.

### Can I preview a rollback before running it?

Yes:

```bash
releasekit rollback --tag genkit-v1.2.3 --dry-run
```

The rollback workflow template also defaults to dry-run mode.

---

## Snapshots & Pre-Releases

### What's the difference between a snapshot and a pre-release?

- **Snapshot** = throwaway dev build with git SHA in the version
  (`0.6.0.dev20260215+g1a2b3c4`). Not published to production.
- **Pre-release** = release candidate published to the real registry
  (`0.6.0rc1`). Users opt in explicitly.

### How do I create a PR preview build?

```bash
releasekit snapshot --pr 1234 --format json
```

This computes snapshot versions for all packages. Use the JSON output
in CI to comment on the PR with version previews.

See [Snapshots & Pre-Releases](snapshots.md) for a full CI workflow.

### How do I promote a release candidate to stable?

```bash
releasekit promote
```

This strips pre-release suffixes: `0.6.0rc1` → `0.6.0`.

---

## Signing & Verification

### Do I need to manage GPG keys?

No. ReleaseKit uses **Sigstore keyless signing** — your CI identity
(GitHub OIDC token) is the key. No secrets to manage or rotate.

### How do I sign artifacts in CI?

```bash
releasekit sign dist/
```

Requires `id-token: write` permission in GitHub Actions. See
[Signing & Verification](signing.md) for the full workflow.

### How do I verify a signed artifact?

```bash
releasekit verify dist/ \
  --cert-identity "https://github.com/OWNER/REPO/.github/workflows/release.yml@refs/heads/main" \
  --cert-oidc-issuer "https://token.actions.githubusercontent.com"
```

---

## Migration

### Can I migrate from release-please?

Yes:

```bash
releasekit migrate --from release-please --dry-run  # preview first
releasekit migrate --from release-please             # generate releasekit.toml
```

Your git tags and history are preserved. See [Migration Guide](migration.md).

### What other tools can I migrate from?

`release-please`, `semantic-release`, `changesets`, and `lerna`.

### Do I need to re-tag my existing releases?

No. ReleaseKit reads existing git tags to compute the next version.
Your tag history is fully compatible.

---

## Doctor & Health Checks

### What's the difference between `check` and `doctor`?

- **`check`** = fast package metadata validation (seconds)
- **`doctor`** = deep environment diagnostics including network checks
  (VCS, forge auth, registry auth)

Use `check` in CI on every commit. Use `doctor` when debugging or
setting up for the first time.

### Can `check` auto-fix issues?

Yes, some checks:

```bash
releasekit check --fix
```

This can add missing `py.typed` markers, fix `Private :: Do Not Upload`
classifiers, and remove stale namespace `__init__.py` files.

See [Health Checks & Doctor](health-checks.md) for the full list.

---

## Troubleshooting

### `releasekit plan` shows no changes but I know there are commits

Common causes:

1. **Shallow clone** — CI often does `fetch-depth: 1`. Use
   `fetch-depth: 0` in `actions/checkout`.
2. **Commits don't follow Conventional Commits** — only `feat:`, `fix:`,
   `perf:`, `revert:`, and `!` (breaking) prefixes trigger bumps.
3. **Commits don't touch the package directory** — bumps are scoped to
   files within each package's path.
4. **Tag already exists** — if `genkit-v1.2.3` already exists, commits
   before that tag are not counted.

### `RK-GRAPH-CYCLE-DETECTED` — what do I do?

Your packages have a circular dependency. Run:

```bash
releasekit graph --format ascii
```

to visualize the cycle. Fix it by removing one direction of the
dependency or extracting shared code into a separate package.

### `RK-CONFIG-UNKNOWN-KEY` — I'm sure the key is correct

ReleaseKit validates all config keys and suggests corrections for typos.
Check for:

- Spelling (e.g., `tag_fromat` → `tag_format`)
- Wrong section (global key in `[workspace.*]` or vice versa)
- Underscore vs. hyphen (`exclude-publish` → `exclude_publish`)

### How do I see what error code means?

```bash
releasekit explain RK-GRAPH-CYCLE-DETECTED
```

This prints the error description, common causes, and suggested fixes.

### Publish is slow. How do I speed it up?

- **Increase concurrency**: `releasekit publish --concurrency 10`
  (default is 5).
- **Use retries for flaky registries**: `--max-retries 2` adds
  exponential backoff with jitter.
- **Skip smoke tests**: Set `smoke_test = false` in your workspace
  config (not recommended for production).

### How do I debug what ReleaseKit is doing?

```bash
# Verbose logging (structured JSON via structlog)
releasekit publish -v

# Extra verbose
releasekit publish -vv

# Preview the full execution plan
releasekit plan --format full
```

---

## Edge Cases — Dependency Graphs

### What happens with a diamond dependency?

```text
    A
   / \
  B   C
   \ /
    D
```

If `D` gets a `feat:` (MINOR) bump, propagation walks reverse edges:
`D → B`, `D → C`, then `B → A` and `C → A`. Package `A` is only
bumped once (PATCH) even though two paths reach it. The BFS
deduplicates — once a package is marked as bumped, subsequent visits
are no-ops.

### What about disconnected components?

```text
  A → B       C → D       E (standalone)
```

Each connected component is independent. A bump in `A` propagates to
`B` but has no effect on `C`, `D`, or `E`. Standalone packages (no
internal deps, no dependents) are only bumped by their own commits.

### What if the graph is a single package with no deps?

Works fine. The graph has one node, zero edges. `topo_sort` returns
a single level with that package. No propagation occurs — the package
is bumped solely by its own commits.

### What about a long chain (A → B → C → D → E)?

Propagation is transitive via BFS. If `E` is bumped, `D` gets a PATCH
bump, which triggers `C`, then `B`, then `A`. All four dependents
receive PATCH bumps in a single pass.

### What if two packages depend on each other (cycle)?

`topo_sort` raises `RK-GRAPH-CYCLE-DETECTED`. Cycles make ordered
publishing impossible — you must break the cycle before releasing.
Run `releasekit graph --format ascii` to visualize it.

### What about self-dependencies (A → A)?

Treated as a cycle. `topo_sort` detects it and raises
`RK-GRAPH-CYCLE-DETECTED`.

---

## Edge Cases — Version Bumps

### A `feat!:` is followed by a `revert:` of that same commit

The revert cancels the MAJOR bump. If no other commits remain, the
package is skipped (no bump). Reverts decrement the bump counter for
the reverted level, so `feat!:` (+1 MAJOR) then `revert:` (−1 MAJOR)
nets to zero.

### Multiple bump levels in the same package

The highest wins. Ten `fix:` commits + one `feat:` = MINOR. One
`feat!:` + fifty `fix:` = MAJOR. Bump levels don't accumulate across
tiers — only the highest non-zero tier matters.

### Breaking change on a `0.x` version

By default (`major_on_zero = false`), breaking changes on `0.x`
produce MINOR bumps (per semver, `0.x` has no stability guarantees).
So `0.3.0` + `feat!:` → `0.4.0`, not `1.0.0`. Set
`major_on_zero = true` to get `0.3.0` → `1.0.0`.

### A package has commits but none are Conventional Commits

No bump. Only `feat:`, `fix:`, `perf:`, `revert:`, and `!` (breaking)
prefixes trigger bumps. Non-conventional commits are logged as
warnings but otherwise ignored.

### A package has no tag yet (first release)

All commits in the repo history (scoped to the package directory) are
scanned. If any are conventional, the package gets a bump from its
current `pyproject.toml` / `package.json` version. Use `bootstrap_sha`
to limit the scan to commits after a specific SHA (useful for
mid-stream adoption).

### `synchronize = true` with mixed bump levels

All packages receive the **maximum** bump computed across the entire
workspace. If package A has `feat:` (MINOR) and package B has `fix:`
(PATCH), both get MINOR. If any package has `feat!:` (MAJOR), all
packages get MAJOR.

### `propagate_bumps = false`

No transitive bumping. Each package is bumped only by its own commits.
If library `core` gets a MINOR bump but `plugin-foo` (which depends on
`core`) has no commits, `plugin-foo` is skipped. This is useful when
you want libraries to release independently without cascading bumps.

### `propagate_bumps = true` + `synchronize = true`

Propagation is disabled when `synchronize` is on (they are mutually
exclusive in practice). Synchronized mode already ensures all packages
share the same bump, so per-edge propagation is redundant.

### Diamond propagation with mixed direct bumps

```text
    A (no commits)
   / \
  B   C
   \ /
    D (feat: → MINOR)
```

`D` gets MINOR. Propagation gives `B` and `C` PATCH each. Then `A`
gets PATCH (from `B` or `C` — whichever BFS visits first; the second
visit is a no-op since `A` is already bumped). Direct bumps always
win: if `B` also had a `feat:` commit, it keeps MINOR (propagation
only upgrades from NONE to PATCH, never downgrades a direct bump).

### `force_unchanged` with propagation

`--force-unchanged` bumps packages with zero commits to PATCH. This
happens **after** propagation, so a package that was already
transitively bumped to PATCH is unaffected. Packages that were truly
untouched (no commits, no transitive trigger) get forced to PATCH.

### `exclude_bump` vs `exclude_publish`

- **`exclude_bump`**: Package is discovered and checked but never
  version-bumped. It does not participate in propagation as a source
  (its version stays frozen). Other packages that depend on it are
  unaffected.
- **`exclude_publish`**: Package gets version bumps and changelog
  entries but is skipped during `releasekit publish`. Useful for
  internal-only packages that should track versions but not be
  uploaded to a registry.

### `max_commits` truncates history — will I miss bumps?

Yes, intentionally. If `max_commits = 100` and there are 200 commits
since the last tag, only the most recent 100 are scanned. This is a
performance trade-off for very large repos. Set `max_commits = 0`
(default) to scan everything.

### Tag exists but is unreachable (corrupt or orphaned)

By default, `git log <tag>..HEAD` fails and ReleaseKit raises an
error. Pass `--ignore-unknown-tags` to fall back to scanning the
full history instead of erroring out.
