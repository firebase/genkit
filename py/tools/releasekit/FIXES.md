# Releasekit: Audit Fixes Roadmap

Findings from an exhaustive audit cross-referencing known pain points from
[release-please](https://github.com/googleapis/release-please/issues) and
[python-semantic-release](https://github.com/python-semantic-release/python-semantic-release/issues)
against the releasekit codebase.

## Dependency Graph

```text
  F1: Label new PRs ──────────┐
                               │
  F2: Filter by head branch ──┼──▶ F5: Auto-prepare on push to main
                               │        │
  F3: checkout@v5 → v4 ───────┘        │
                                        ▼
  F4: --first-parent dedup ──────▶ F6: Write CHANGELOG.md to disk
                                   (per-package files, prepend new
                                    entries, commit in release branch)
```

## Reverse Topological Order (phases)

### Phase 1 — Foundations (no dependencies, land first)

These are prerequisites for the auto-prepare feature and fix real bugs.

| ID | Severity | File | Fix |
|----|----------|------|-----|
| **F1** | Medium | `prepare.py` | Add `autorelease: pending` label to **newly created** PRs, not just updated ones. Without this, `tag_release` can't find the merged PR. |
| **F2** | Medium | `release.py` | Filter `list_prs()` by `head='releasekit--release'` in addition to label. Prevents race where a stale PR with the same label is picked up. |
| **F3** | Medium | `publish_python.yml` | Change `actions/checkout@v5` → `@v4`. v5 doesn't exist; workflow will fail. |

### Phase 2 — Changelog Quality (independent)

| ID | Severity | File | Fix |
|----|----------|------|-----|
| **F4** | Critical | `vcs/git.py` + `vcs/__init__.py` | Add `--first-parent` to `git log` in the `log()` method. Prevents duplicate changelog entries when merge commits repeat the same conventional commit message as the squashed commit. See [release-please#2476](https://github.com/googleapis/release-please/issues/2476). |

### Phase 3 — Auto-Prepare + Changelog Files (depends on F1 + F2 + F4)

| ID | Severity | File | Fix |
|----|----------|------|-----|
| **F5** | Feature | `release.yml` | Add `push` trigger on `main` so `prepare` runs automatically on every merge. The Release PR stays up-to-date with accumulated changelogs. Publish remains manual or merge-triggered. |
| **F6** | Feature | `prepare.py` | Write per-package `CHANGELOG.md` files to disk during `prepare`. Prepend new entries to existing file (or create it). Commit alongside version bumps on the release branch. Depends on F4 so written changelogs are dedup-clean. |

## Detailed Fix Descriptions

### F1: Label new PRs with `autorelease: pending`

**Problem**: In `prepare.py:334-349`, the label is only added when an
existing PR is found and updated. When a brand-new PR is created, it
never gets the label. The `release` step searches for merged PRs by
this label, so it will miss PRs that were created fresh and then merged.

**Fix**: After `forge.create_pr()`, extract the PR number from the
result and call `forge.add_labels(pr_number, [_AUTORELEASE_PENDING])`.

### F2: Filter merged PR lookup by head branch

**Problem**: In `release.py:236-240`, `list_prs(label=..., state='merged')`
could return a stale PR from a previous release cycle if the label wasn't
cleaned up. Adding `head='releasekit--release'` narrows the search to
only the correct branch.

**Fix**: Add `head=_RELEASE_BRANCH` to the `list_prs` call. Import the
branch constant or define it locally.

### F3: Fix `actions/checkout` version

**Problem**: `publish_python.yml:84` uses `actions/checkout@v5` which
does not exist. The latest stable is `v4`.

**Fix**: One-line change: `@v5` → `@v4`.

### F4: Deduplicate changelog entries with `--first-parent`

**Problem**: When a PR is merged (not squashed), both the merge commit
and the original feature commit appear in `git log`. If both have the
same conventional commit message (common with GitHub's default merge
commit format), the changelog gets duplicate entries.

**Fix**: Add `--first-parent` flag to the git log command in
`GitCLIBackend.log()`. This follows only the first parent of merge
commits, which is the mainline. Also add the parameter to the `VCS`
protocol so all backends are aware of it.

### F5: Auto-prepare on push to main

**Problem**: Currently `release.yml` only triggers on `workflow_dispatch`,
requiring manual intervention to create/update the Release PR.

**Fix**: Add a `push` trigger filtered to `main` (and scoped to `py/`
paths). The `prepare` job's `if` condition is updated to also run on
push events. The `publish` job remains gated on manual dispatch or
PR merge with the `autorelease: pending` label.

Result:

```text
push to main ──▶ prepare runs ──▶ Release PR created/updated
                                       │
                           (human reviews, merges when ready)
                                       │
                                       ▼
                             publish triggers automatically
```

### F6: Write per-package CHANGELOG.md files to disk

**Problem**: Currently, changelogs are only rendered into the Release PR
body. There are no `CHANGELOG.md` files in any package directory. Users
cannot view the changelog locally, and published PyPI packages have no
changelog file included.

**Where changelogs go today**:
- PR body only (via `_build_pr_body` in `prepare.py`)
- `releasekit plan` shows version bumps but not changelog text

**Fix**: After generating changelogs in `prepare_release` (step 6),
write each package's rendered changelog to `{pkg.path}/CHANGELOG.md`:

1. If the file exists, prepend the new version's section above the
   existing content (below the `# Changelog` heading).
2. If the file doesn't exist, create it with a `# Changelog` heading
   followed by the new section.
3. Include the changelog files in the release branch commit (step 8).

This ensures:
- Changelog is visible in the repo alongside each package
- Changelog is included in the sdist/wheel (via `pyproject.toml`
  `[tool.setuptools]` or default inclusion)
- The Release PR diff shows the changelog additions for review
- `releasekit plan --format table` can optionally preview changelog text

## Low-Priority Notes (not blocking, document only)

| Issue | Notes |
|-------|-------|
| Signal handler in `pin.py` not async-safe | Acceptable — crash recovery only, atexit + finally handle normal cases |
| Prerelease format (`0.6.0rc1` vs `0.6.0a1`) | Valid PEP 440, but unconventional for `alpha`/`beta` labels |
| Pre-1.0 major bump convention | Design choice — `0.x` + breaking → `1.0.0`. Some prefer `0.x+1`. Document. |
| Advisory lock not atomic | Acceptable — CI concurrency group prevents races in practice |
