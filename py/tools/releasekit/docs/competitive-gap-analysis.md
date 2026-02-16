# Releasekit Competitive Gap Analysis

**Date:** 2026-02-15
**Sources:** Issue trackers and documentation of:
- [release-please](https://github.com/googleapis/release-please) (Google)
- [semantic-release](https://github.com/semantic-release/semantic-release) (JS ecosystem)
- [python-semantic-release](https://github.com/python-semantic-release/python-semantic-release) (Python ecosystem)
- [release-it](https://github.com/release-it/release-it) (JS ecosystem, plugin-based)
- [changesets](https://github.com/changesets/changesets) (JS monorepos)
- [knope](https://github.com/knope-dev/knope) (Rust-based, polyglot)
- [goreleaser](https://github.com/goreleaser/goreleaser) (Go ecosystem)
- [jreleaser](https://github.com/jreleaser/jreleaser) (Java ecosystem)

---

## Executive Summary

Releasekit already addresses several of the **most painful** issues plaguing
the three major release-automation tools — particularly monorepo support,
polyglot ecosystems, dependency-graph-aware publishing, and workspace health
checks. However, there are meaningful gaps that, if addressed, would make
releasekit significantly more robust and differentiated.

The gaps are organized by severity: **Critical** (users abandon tools over
these), **High** (frequent complaints / feature requests), and **Nice-to-have**
(quality-of-life improvements).

---

## 1. CRITICAL GAPS

### 1.1 Pre-release / Release-Candidate Workflow
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#510](https://github.com/googleapis/release-please/issues/510) | 100+ 👍, open since 2020 |
| release-please [#2294](https://github.com/googleapis/release-please/issues/2294) | High 👍 |
| release-please [#2515](https://github.com/googleapis/release-please/issues/2515) | Convert prerelease → stable |
| release-please [#2641](https://github.com/googleapis/release-please/issues/2641) | Pre-release forces wrong bump |
| python-semantic-release [#555](https://github.com/python-semantic-release/python-semantic-release/issues/555) | Broken changelog on prerelease→release |
| python-semantic-release [#817](https://github.com/python-semantic-release/python-semantic-release/issues/817) | Pre-release entries missing from final release changelog |
| semantic-release [#563](https://github.com/semantic-release/semantic-release/issues/563) | Multi-branch + pre-release |

**Current releasekit state:** The `compute_bumps` function accepts a
`prerelease` parameter and the forge backends support `prerelease=True` on
`create_release`. However, there is **no CLI flag** to trigger a pre-release
workflow, no branch-to-channel mapping, and no changelog handling for
collapsing pre-release entries into a final release.

**Recommendation:**
- Add `--prerelease <label>` flag to `publish` and `prepare` (e.g. `--prerelease rc`, `--prerelease alpha`).
- Support PEP 440 pre-release suffixes (`a`, `b`, `rc`, `dev`) natively.
- Implement changelog collapsing: when a stable release follows pre-releases, merge all pre-release sections into the stable entry.
- Add `promote` subcommand to convert a pre-release tag to a stable release.

### 1.2 Revert Commit Handling
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#296](https://github.com/googleapis/release-please/issues/296) | Open since 2019, many 👍 |
| python-semantic-release [#402](https://github.com/python-semantic-release/python-semantic-release/issues/402) | Confirmed bug, open |

**Current releasekit state:** ✅ **Done (2026-02-12).** `parse_conventional_commit`
handles `Revert "feat: ..."` (GitHub format) and `revert: feat: ...`
(conventional format). Bump computation uses per-level counters where reverts
decrement, so a reverted `feat:` cancels the MINOR bump. Reverted commits
appear in a "Reverted" changelog section.

### 1.3 Hotfix / Maintenance Branch Releases
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#2475](https://github.com/googleapis/release-please/issues/2475) | Recent, active discussion |
| semantic-release [#1038](https://github.com/semantic-release/semantic-release/issues/1038) | Tag errors on maintenance branch |
| semantic-release [#1131](https://github.com/semantic-release/semantic-release/issues/1131) | Can't publish maintenance release |
| semantic-release [#1487](https://github.com/semantic-release/semantic-release/issues/1487) | EINVALIDNEXTVERSION on maintenance branch |

**Current releasekit state:** No explicit support for releasing from
non-default branches. The `compute_bumps` function looks at tags from the
current branch but doesn't handle the case where a hotfix branch needs to
produce a patch release off an older version.

**Recommendation:**
- Support `--base-branch` or branch-to-channel configuration in `releasekit.toml`.
- Allow version computation relative to a specific tag (e.g. `--since-tag genkit-v1.2.0`).
- Prevent accidental double-bumps when hotfix branches merge back to main.
- Add `releasekit cherry-pick` command (R38) to selectively backport commits
  to release/maintenance branches with conflict detection and changelog updates.

---

## 2. HIGH-PRIORITY GAPS

### 2.1 Dependent Package Version Propagation in Monorepos
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#1032](https://github.com/googleapis/release-please/issues/1032) | Major pain point for OpenTelemetry |

**Current releasekit state:** ✅ **Done (2026-02-12).** `versioning.py:386-400`
implements BFS propagation via `graph.reverse_edges`. When package A bumps,
all dependents automatically get their dependency specifiers updated.

### 2.2 Contributor Attribution in Changelogs
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#292](https://github.com/googleapis/release-please/issues/292) | Feature request, many 👍 |
| python-semantic-release [#187](https://github.com/python-semantic-release/python-semantic-release/issues/187) | Add release notes in commit_message |

**Current releasekit state:** The changelog module generates sections by
commit type but does **not** extract or display commit authors/contributors.

**Recommendation:**
- Parse `git log --format` to extract author names and GitHub usernames.
- Add a "Contributors" section to generated changelogs.
- Optionally link to GitHub profiles (configurable).

### 2.3 PEP 440 Version Compliance
| Alternative tool issue | Votes/Comments |
|---|---|
| python-semantic-release [#455](https://github.com/python-semantic-release/python-semantic-release/issues/455) | Top 👍 issue |
| python-semantic-release [#1018](https://github.com/python-semantic-release/python-semantic-release/issues/1018) | Version variable not changed with PEP 440 |

**Current releasekit state:** ✅ **Done.** `versioning_scheme = "pep440"` config
option added. `_apply_bump()` is now scheme-aware: produces PEP 440 suffixes
(`1.0.1a1`, `1.0.1b1`, `1.0.1rc1`, `1.0.1.dev1`) when `versioning_scheme = "pep440"`
and semver format (`1.0.1-alpha.1`, `1.0.1-rc.1`) when `versioning_scheme = "semver"`.
`compute_bumps()` threads `versioning_scheme` from `WorkspaceConfig` through all
7 call sites (cli.py ×5, prepare.py, api.py). `_parse_base_version()` correctly
strips both semver and PEP 440 pre-release suffixes before bumping.
`ALLOWED_VERSIONING_SCHEMES` now includes `semver`, `pep440`, and `calver`.

### 2.4 Dry-Run / "What Version Would Be Published" Mode
| Alternative tool issue | Votes/Comments |
|---|---|
| semantic-release [#753](https://github.com/semantic-release/semantic-release/issues/753) | Very high 👍 |
| semantic-release [#1647](https://github.com/semantic-release/semantic-release/issues/1647) | Just print next version |

**Current releasekit state:** ✅ **Already addressed.** The `releasekit version`
and `releasekit plan` commands provide this functionality with `--format json`
output. This is a **competitive advantage** — document it prominently.

### 2.5 GitHub API Rate Limiting / Timeouts
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#2265](https://github.com/googleapis/release-please/issues/2265) | Hardcoded limits cause timeouts |
| release-please [#2577](https://github.com/googleapis/release-please/issues/2577) | 502 Bad Gateway |
| release-please [#2592](https://github.com/googleapis/release-please/issues/2592) | 502 on merge commit fetch |
| semantic-release [#2204](https://github.com/semantic-release/semantic-release/issues/2204) | Secondary rate limit exceeded |

**Current releasekit state:** ✅ **Done.** The `net.py` module has
retry/backoff logic, `github_api.py` has rate-limit handling, and the
publisher has configurable `max_retries` and `retry_base_delay`.
`--max-commits` (R25, done 2026-02-13) bounds commit scanning depth.
All forge API calls use exponential backoff with jitter.

### 2.6 Performance on Large Repositories
| Alternative tool issue | Votes/Comments |
|---|---|
| python-semantic-release [#722](https://github.com/python-semantic-release/python-semantic-release/issues/722) | 40 min for 3K commits |

**Current releasekit state:** ✅ **Mostly done.** Version computation uses
`git log` with `--since-tag` scoping. `--max-commits` (R25, done 2026-02-13)
bounds changelog generation for large repos. `compute_bumps` Phase 1 uses
`asyncio.gather` for ~10× speedup on 60+ packages (R32, done 2026-02-12).

**Remaining:** ✅ All done.
- ✅ ~~`bootstrap-sha` config option (R26)~~ — Done (2026-02-13).
- ✅ ~~Incremental changelog updates~~ — Done (2026-02-15). `write_changelog_incremental()`.

### 2.7 Stale State / "Stuck" Release Recovery
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#1946](https://github.com/googleapis/release-please/issues/1946) | "Untagged merged release PRs — aborting" |
| release-please [#2172](https://github.com/googleapis/release-please/issues/2172) | Manifest not updating |

**Current releasekit state:** ✅ **Done.** The `rollback` subcommand
can delete tags and releases. `run_doctor()` in `doctor.py` implements 6
diagnostic checks (config, tag alignment, orphaned tags, VCS state, forge
connectivity, default branch). `list_tags` and `current_branch` added to
VCS protocol (2026-02-13). `releasekit doctor` is fully wired in CLI with
`_cmd_doctor` handler and `doctor` subparser.

---

## 3. NICE-TO-HAVE GAPS

### 3.1 GPG / Sigstore Signing and Provenance
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#1314](https://github.com/googleapis/release-please/issues/1314) | GPG signing |
| semantic-release | npm provenance support |

**Current releasekit state:** ✅ **Done.** `signing.py` implements
keyless Sigstore signing via `sigstore-python`. `sign_artifact()` handles
ambient OIDC credential detection (GitHub Actions, Google Cloud) with
fallback to explicit `--identity-token`. `verify_artifact()` verifies
bundles against expected identity and OIDC issuer. CLI exposes
`releasekit sign` and `releasekit verify` subcommands, plus `--sign`
flag on `publish` for automatic post-publish signing.

**Remaining:**
- GPG signing (Sigstore only for now).
- PyPI Trusted Publishers / attestation workflows.

### 3.2 Auto-Merge Release PRs
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#2299](https://github.com/googleapis/release-please/issues/2299) | Enable auto-merge on PR |

**Current releasekit state:** The forge backends support `merge_pr` but
there's no auto-merge configuration.

**Recommendation:**
- Add `auto_merge = true` config option for release PRs.
- Support `--auto-merge` flag on `prepare`.

### 3.3 Disable/Customize Changelog Generation
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#2007](https://github.com/googleapis/release-please/issues/2007) | Option to disable changelog |
| release-please [#2634](https://github.com/googleapis/release-please/issues/2634) | changelog-path has no effect |
| python-semantic-release [#1132](https://github.com/python-semantic-release/python-semantic-release/issues/1132) | Custom changelog ignores update mode |

**Current releasekit state:** ✅ **Partially done.** The `changelog = false`
config option exists per-workspace in `WorkspaceConfig`. Customization via
Jinja2 templates is not yet implemented.

**Recommendation:**
- Support custom Jinja2 templates for changelog rendering.
- Add `changelog_path` config for non-standard locations.

### 3.4 Plugin / Extension System
| Alternative tool issue | Votes/Comments |
|---|---|
| python-semantic-release [#321](https://github.com/python-semantic-release/python-semantic-release/issues/321) | Plugin-based releases |
| semantic-release | Entire architecture is plugin-based |

**Current releasekit state:** The backend architecture (VCS, PM, Forge,
Registry) is already modular and swappable. But there's no user-facing
plugin system for custom steps.

**Recommendation (lower priority):**
- Consider entry-point-based plugin discovery for custom fixers, checks,
  and publish steps.
- This is lower priority since the backend architecture already provides
  extensibility for internal use.

### 3.5 Multi-Forge Notifications
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#1021](https://github.com/googleapis/release-please/issues/1021) | Change git provider + notifications |
| python-semantic-release [#149](https://github.com/python-semantic-release/python-semantic-release/issues/149) | Publish to two different remote VCS |

**Current releasekit state:** ✅ **Already addressed.** Releasekit supports
GitHub (CLI + API), GitLab, Bitbucket, and a null forge. This is a
competitive advantage.

### 3.6 Unconventional Tag Handling
| Alternative tool issue | Votes/Comments |
|---|---|
| python-semantic-release [#633](https://github.com/python-semantic-release/python-semantic-release/issues/633) | NotImplementedError on unconventional tags |

**Current releasekit state:** ✅ **Done (2026-02-12).** The `tags.py` module
uses configurable `tag_format` patterns with `{label}` placeholder support
(2026-02-13). `--ignore-unknown-tags` flag added to `publish`, `plan`,
`version` commands. `compute_bumps(ignore_unknown_tags=True)` falls back to
full history on bad tags with a warning.

---

## 4. RELEASEKIT COMPETITIVE ADVANTAGES (already addressed)

These are pain points in alternatives that releasekit **already solves**:

| Pain Point | Alternative Tool Status | Releasekit Status |
|---|---|---|
| **Monorepo support** | semantic-release [#193](https://github.com/semantic-release/semantic-release/issues/193) (open since 2016!), python-semantic-release [#168](https://github.com/python-semantic-release/python-semantic-release/issues/168) | ✅ First-class: workspace discovery, dep graph, topo-sorted publish |
| **Polyglot ecosystems** | release-please [#2207](https://github.com/googleapis/release-please/issues/2207) (Rust+Node monorepo broken) | ✅ Multi-ecosystem detection (Python, JS, Go) |
| **uv workspace support** | release-please [#2561](https://github.com/googleapis/release-please/issues/2561) (feature request) | ✅ Native uv workspace discovery |
| **Version preview** | semantic-release [#753](https://github.com/semantic-release/semantic-release/issues/753), [#1647](https://github.com/semantic-release/semantic-release/issues/1647) | ✅ `releasekit version` and `releasekit plan` |
| **Multi-forge support** | release-please (GitHub only), python-semantic-release [#666](https://github.com/python-semantic-release/python-semantic-release/issues/666) (GitLab guide needed) | ✅ GitHub, GitLab, Bitbucket, none |
| **Workspace health checks** | No equivalent in any alternative | ✅ 34 automated checks with `--fix` |
| **Shell completions** | Not available in alternatives | ✅ bash, zsh, fish |
| **Error explainer** | Not available in alternatives | ✅ `releasekit explain <code>` |
| **Rollback** | No built-in rollback in alternatives | ✅ `releasekit rollback <tag>` |
| **Retry with backoff** | semantic-release [#2204](https://github.com/semantic-release/semantic-release/issues/2204) (rate limit crashes) | ✅ Configurable retries + exponential backoff |
| **Release locking** | No equivalent | ✅ File-based release lock prevents concurrent publishes |
| **Dependency graph visualization** | No equivalent | ✅ `releasekit graph` with dot, mermaid, d2, levels formats |
| **Distro packaging sync** | No equivalent in any alternative | ✅ Auto-syncs Debian, Fedora, Homebrew deps from `pyproject.toml` via `releasekit check --fix` |
| **Revert cancellation** | release-please [#296](https://github.com/googleapis/release-please/issues/296) (open since 2019) | ✅ Per-level bump counters with revert decrement |
| **Sigstore signing** | release-please [#1314](https://github.com/googleapis/release-please/issues/1314) (GPG only) | ✅ Keyless Sigstore signing + verification via `releasekit sign`/`verify` |
| **SBOM generation** | No equivalent in any alternative (except goreleaser) | ✅ CycloneDX + SPDX via `sbom.py` |
| **Release state diagnostics** | No equivalent | ✅ `releasekit doctor` with 6 checks (config, tags, VCS, forge, branch) |

---

## 5. GAP RESOLUTION STATUS

### Completed

1. ✅ **Pre-release workflow** — `prerelease.py`.
2. ✅ **Revert commit handling** — Per-level bump counters with revert decrement.
3. ✅ **`releasekit doctor`** — 6 diagnostic checks.
4. ✅ **Internal dependency version propagation** — BFS via `graph.reverse_edges`.
5. ✅ **Contributor attribution in changelogs** — `ChangelogEntry.author`.
6. ✅ **Incremental changelog generation** — `write_changelog_incremental()`.
7. ✅ **Hotfix branch support** — `hotfix.py`.
8. ✅ **Sigstore signing + verification** — `signing.py`.
9. ✅ **Auto-merge release PRs** — `auto_merge` config.
10. ✅ **SBOM generation** — CycloneDX + SPDX.
11. ✅ **Custom changelog templates** — Jinja2 support.

### Remaining

1. **Plugin system for custom steps**

---

## 6. GENKIT JS — CURRENT RELEASE TOOLING ANALYSIS

The Genkit JS side uses a **completely manual, shell-script-based** release
process. Understanding its pain points is critical because releasekit is
intended to replace it.

### 6.1 Current JS Release Architecture

**Version bumping** — `js/scripts/bump_version.sh`:
- Uses `npm version <type> --preid <id>` per package.
- Hardcoded list of ~20 packages in `bump_and_tag_js.sh`.
- Each package bumped individually with `cd` into directory.
- Tags created per-package (e.g. `@genkit-ai/core@1.2.3`).
- Single commit with all bumps, then all tags pushed.

**Publishing** — `scripts/release_main.sh`:
- Sequential `pnpm publish` per package (20+ `cd` / `pnpm publish` blocks).
- Publishes to `wombat-dressing-room.appspot.com` (Google's npm proxy).
- `--provenance=false` hardcoded (no supply-chain attestation).
- No dependency ordering — publishes in hardcoded order.
- No error recovery — if one package fails, script continues blindly.
- No retry logic.

**CLI binary releases** — `scripts/cli-releases/`:
- Separate process: download from GitHub Actions artifacts → upload to GCS.
- Channel-based promotion (`next` → `prod`).
- Metadata JSON files for version discovery.

**GitHub Actions workflows:**
- `bump-js-version.yml` — Manual dispatch, calls `bump_and_tag_js.sh`.
- `bump-cli-version.yml` — Manual dispatch for CLI binary version.
- `bump-package-version.yml` — Manual dispatch for individual packages.
- `release_js_main.yml` — Manual dispatch, runs `release_main.sh`.
- `release_js_package.yml` — Manual dispatch for single package publish.

### 6.2 Pain Points in the Current JS Process

| Problem | Severity | Releasekit Status |
|---------|----------|-------------------|
| **Hardcoded package lists** — Adding a new plugin requires editing 3+ shell scripts and workflows | Critical | ✅ Auto-discovery via workspace |
| **No dependency ordering** — Packages published in hardcoded order, not topological | High | ✅ Topo-sorted publish via `graph.py` |
| **No error recovery** — If `pnpm publish` fails mid-way, no rollback or retry | High | ✅ Retry with backoff, rollback command |
| **No changelog generation** — Version bumps have no associated changelogs | High | ✅ `releasekit changelog` from conventional commits |
| **No preflight checks** — Dirty worktree, unpushed commits, etc. not validated | High | ✅ 34 preflight checks |
| **No dry-run for publish** — Can only test by actually publishing | High | ✅ `--dry-run` on all commands |
| **Sequential publishing** — No parallelism within dependency levels | Medium | ✅ Concurrent publish with configurable parallelism |
| **No provenance** — `--provenance=false` hardcoded | Medium | ✅ `--provenance` flag on `PnpmBackend.publish()` + `WorkspaceConfig` |
| **Manual dispatch only** — No automated release on merge | Medium | ✅ `prepare` + `release` workflow |
| **Wombat proxy coupling** — Hardcoded to Google's internal npm proxy | Low | ✅ Configurable registry URL |
| **No version preview** — Can't see what would be bumped before bumping | Medium | ✅ `releasekit version` / `plan` |
| **All packages bump together** — No independent versioning per package | Medium | ✅ Per-package bump based on git changes |

### 6.3 Key Takeaway for Releasekit

The JS release process is the **strongest argument for releasekit's existence**.
Every single pain point listed above is already addressed by releasekit's
architecture. The main remaining work is:

1. ✅ **JS/pnpm workspace backend** — `PnpmBackend` fully implemented with
   `build()`, `publish()`, `lock()`, `version_bump()`, `resolve_check()`,
   `smoke_test()`. Ecosystem-aware `_create_backends()` selects it for JS.
2. ✅ **npm registry backend** — `NpmRegistry` fully implemented with
   `is_published()` and `latest_version()` via npm registry API.
3. ✅ **Wombat proxy support** — `PnpmBackend.publish(index_url=...)` maps
   to `--registry`. Works with any custom registry URL.
4. ✅ **Tag format compatibility** — `tag_format` with `{label}` placeholder
   supports `{name}@{version}` and any custom format per workspace.

---

## 7. ADDITIONAL TOOLS COMPARISON

### 7.1 Changesets (`@changesets/cli`)

**What it is:** Intent-based versioning for JS monorepos. Developers write
"changeset" files describing what changed and the bump type. At release time,
changesets are consumed to produce version bumps and changelogs.

**Stars:** ~9K | **Ecosystem:** JS/TS monorepos

**Key features releasekit should learn from:**
- **Intent files** — Changeset files (`.changeset/*.md`) let developers
  declare bump intent at PR time, not release time. This decouples "what
  changed" from "when to release."
- **Linked packages** — Groups of packages that always share the same version.
- **Fixed packages** — Packages that always bump together.
- **Snapshot releases** — Publish ephemeral versions for testing (e.g.
  `0.0.0-dev-20240115`).

**Top pain points (from their issues):**
- [#862](https://github.com/changesets/changesets/issues/862) — Want conventional commit support (changesets is manual-only).
- [#577](https://github.com/changesets/changesets/issues/577) — Better conventional commits integration.
- [#614](https://github.com/changesets/changesets/issues/614) — No dry-run for publish.
- [#1152](https://github.com/changesets/changesets/issues/1152) — No provenance support.
- [#879](https://github.com/changesets/changesets/issues/879) — No GitLab support.
- [#264](https://github.com/changesets/changesets/issues/264) — No aggregated monorepo changelog.
- [#1160](https://github.com/changesets/changesets/issues/1160) — Can't publish individual packages independently.
- [#1139](https://github.com/changesets/changesets/issues/1139) — Doesn't update lockfiles.

**Releasekit advantages over changesets:**
- ✅ Conventional commits (automatic bump detection, no manual files).
- ✅ Dry-run on all commands.
- ✅ Multi-forge (GitHub, GitLab, Bitbucket).
- ✅ Polyglot (not JS-only).
- ✅ Individual package publishing.

**Gap to consider:** ✅ Done.
- ✅ ~~**Snapshot releases**~~ — Done (2026-02-15). `snapshot.py` with
  `snapshot` CLI subcommand that publishes `0.0.0-dev.<sha>` versions.
- **Intent files** — Could be a complementary approach to conventional
  commits for cases where commit messages are insufficient.

### 7.2 Nx Release

**What it is:** Built-in release management in the Nx monorepo build system.

**Stars:** ~25K (Nx overall) | **Ecosystem:** JS/TS, Rust, Docker

**Key features:**
- **Three-phase model** — Version → Changelog → Publish (same as releasekit).
- **Programmatic API** — Node.js API for custom release scripts.
- **Version plans** — File-based versioning (like changesets).
- **Release groups** — Group packages for coordinated releases.
- **Project graph awareness** — Uses Nx's dependency graph for ordering.

**Top pain points:**
- Tightly coupled to Nx ecosystem — can't use without Nx.
- No Python/Go support.
- No multi-forge support.

**Releasekit advantages over Nx Release:**
- ✅ Standalone tool (no build system lock-in).
- ✅ Polyglot (Python, JS, Go).
- ✅ Multi-forge support.
- ✅ Workspace health checks.

**Gap to consider:**
- **Programmatic API** — Nx Release's Node.js API is powerful for custom
  workflows. Releasekit could expose a Python API for scripting.

### 7.3 Knope

**What it is:** Rust-based release tool supporting both conventional commits
and changesets, with monorepo support.

**Stars:** ~800 | **Ecosystem:** Rust, JS, Go, Python (via generic files)

**Key features:**
- **Hybrid input** — Combines conventional commits AND changesets.
- **Workflow DSL** — TOML-based workflow definitions with steps.
- **Multi-forge** — GitHub and Gitea.
- **Monorepo support** — Per-package versioning and changelogs.

**Top pain points:**
- [#162](https://github.com/knope-dev/knope/issues/162) — Doesn't update lockfiles.
- [#924](https://github.com/knope-dev/knope/issues/924) — Can't disable conventional commits.
- [#988](https://github.com/knope-dev/knope/issues/988) — Variables don't work across packages.

**Gap to consider:** ✅ Done.
- ✅ ~~**Hybrid conventional commits + changesets**~~ — Done (2026-02-15).
  `changesets.py` reads `.changeset/*.md` files and merges with conventional
  commit bumps (higher wins). Same approach as Knope.

### 7.4 GoReleaser

**What it is:** Go-focused release tool for building, archiving, packaging,
signing, and publishing.

**Stars:** ~14K | **Ecosystem:** Go

**Key features:**
- **Cross-compilation** — Builds for multiple OS/arch targets.
- **Package managers** — Homebrew, Snap, Scoop, AUR, Docker, etc.
- **Signing** — GPG and Cosign/Sigstore.
- **SBOM generation** — Software Bill of Materials.
- **Checksums** — Automatic checksum files.
- **Announce** — Slack, Discord, Teams, Twitter notifications.

**Releasekit advantages:**
- ✅ Polyglot (not Go-only).
- ✅ Monorepo-native.
- ✅ Workspace health checks.

**Gaps to consider:**
- ✅ ~~**SBOM generation**~~ — Done. CycloneDX + SPDX via `sbom.py`.
- ✅ ~~**Announcement integrations**~~ — Done. Slack, Discord, custom webhooks via `announce.py`.
- **Cross-compilation orchestration** — Relevant for Genkit CLI binaries
  (currently handled by separate `promote_cli_gcs.sh`).

### 7.5 JReleaser

**What it is:** Java-focused but polyglot release tool.

**Stars:** ~800 | **Ecosystem:** Java, but supports any language

**Key features:**
- **Extensive packager support** — Homebrew, Snap, Scoop, Chocolatey, Docker,
  Flatpak, AppImage, JBang, SDKMAN.
- **Signing** — GPG and Cosign.
- **Announce** — 20+ announcement channels.
- **SBOM** — CycloneDX and SPDX.
- **Deploy** — Maven Central, GitHub Packages, Artifactory.

**Gap to consider:**
- **Packager integrations** — If releasekit ever needs to publish to
  Homebrew, Snap, etc., JReleaser's approach is a good reference.

### 7.6 release-it

**What it is:** Generic CLI tool to automate versioning and package
publishing. Plugin-based architecture where core is minimal and features
are added via plugins.

**Stars:** ~9K | **Ecosystem:** JS/TS primarily, but extensible via plugins

**Key features:**
- **Interactive + CI mode** — Interactive prompts by default, `--ci` for
  fully automated. `--only-version` for prompt-only version selection.
- **Hooks system** — `before:init`, `after:bump`, `after:release` etc.
  Shell commands at any lifecycle point. Template variables available.
- **Pre-release management** — `--preRelease=beta`, `--preRelease=rc`,
  consecutive pre-releases, `--preReleaseBase=1` for starting count.
- **Re-run releases** — `--no-increment` to update/republish an existing
  tag without bumping version.
- **Programmatic API** — Can be used as a Node.js dependency, not just CLI.
- **npm Trusted Publishing** — OIDC integration for token-free CI publishing
  (as of July 2025).
- **Multi-forge** — GitHub and GitLab releases (not Bitbucket).
- **Dry-run** — `--dry-run` shows what would happen.
- **CalVer support** — Via `release-it-calver-plugin`.

**Plugin ecosystem (things that require plugins in release-it):**

| Capability | release-it plugin required | releasekit built-in? |
|---|---|---|
| Conventional commits | `@release-it/conventional-changelog` | ✅ Built-in |
| Changelog generation | `@release-it/conventional-changelog` or `@release-it/keep-a-changelog` | ✅ Built-in |
| Version bumping in non-package.json files | `@release-it/bumper` | ✅ Built-in (any manifest) |
| Monorepo workspaces | `@release-it-plugins/workspaces` | ✅ Built-in (first-class) |
| pnpm support | `release-it-pnpm` | ✅ Built-in (`PnpmBackend`) |
| CalVer versioning | `release-it-calver-plugin` | ✅ Built-in (`calver.py`) |
| Changesets integration | `changesets-release-it-plugin` | ✅ Built-in (`changesets.py`) |
| .NET publishing | `@jcamp-code/release-it-dotnet` | ❌ Not yet |
| Gitea support | `release-it-gitea` | ❌ Not yet (GH/GL/BB only) |
| Regex-based version bumping | `@j-ulrich/release-it-regex-bumper` | ✅ Built-in (configurable `tag_format`) |

**Top pain points (from their issues):**
- [#1110](https://github.com/release-it/release-it/issues/1110) — Want Cargo, Maven, PIP publishing (JS-only out of the box).
- [#1075](https://github.com/release-it/release-it/issues/1075) — Want PR labels instead of commit messages for version detection.
- [#1126](https://github.com/release-it/release-it/issues/1126) — Want GitHub PR-oriented flow (like release-please).
- [#1127](https://github.com/release-it/release-it/issues/1127) — Release notes from RCs not carried to stable release.
- [#1246](https://github.com/release-it/release-it/issues/1246) — `whatBump` broken with consecutive pre-releases.
- [#1112](https://github.com/release-it/release-it/issues/1112) — Pre-release ignores undefined recommended bump.
- [#1234](https://github.com/release-it/release-it/issues/1234) — No npm 2FA with security keys.
- [#1131](https://github.com/release-it/release-it/issues/1131) — GitLab integration doesn't support proxy settings.
- [#1216](https://github.com/release-it/release-it/issues/1216) — Tags latest commit instead of current on GitLab.

**Releasekit advantages over release-it:**
- ✅ Polyglot out-of-the-box (Python, JS, Go, Rust, Java, Dart) — no plugins needed.
- ✅ Monorepo-native with dependency graph — release-it needs `@release-it-plugins/workspaces` and manual `@release-it/bumper` config per package.
- ✅ Topological publish ordering — release-it publishes in hardcoded order.
- ✅ 34 workspace health checks + auto-fix — no equivalent.
- ✅ Rollback command — no equivalent.
- ✅ Conventional commits built-in — release-it needs a plugin.
- ✅ Changelog built-in — release-it's default is raw `git log`.
- ✅ Retry with backoff — no equivalent.
- ✅ Bitbucket support — release-it only has GitHub + GitLab.

**release-it advantages over releasekit:**
- ✅ Interactive mode with prompts — releasekit is CLI-only.
- ✅ Hooks system for arbitrary shell commands at lifecycle points.
- ✅ `--no-increment` to re-run/update existing releases.
- ✅ Programmatic Node.js API.
- ✅ npm Trusted Publishing (OIDC).
- ✅ CalVer support (via plugin).
- ✅ Mature plugin ecosystem with 15+ community plugins.

**Monorepo support comparison:**

release-it's monorepo recipe is **manual and fragile**:
1. Each workspace needs its own `.release-it.json` with `git: false`.
2. Internal dependencies require explicit `@release-it/bumper` config
   listing every dependency path (e.g. `"dependencies.package-a"`).
3. Root `package.json` runs `npm run release --workspaces && release-it`.
4. No dependency graph — publish order is workspace declaration order.
5. No health checks — misconfigured workspaces silently break.

Releasekit's monorepo support is **automatic**:
1. Auto-discovers all packages via workspace backend.
2. Builds dependency graph, publishes in topological order.
3. Internal dependency versions propagated automatically via BFS.
4. 34 health checks catch misconfigurations before publish.

---

## 8. NEW GAPS IDENTIFIED (2026-02-15)

### 8.1 Scheduled / Cadence-Based Releases

**The problem:** None of the major release tools have built-in support for
scheduled releases. Teams that want daily, weekly, or per-sprint releases
must cobble together CI cron triggers + release tool invocation. This is
a common request (see [semantic-release SO question](https://stackoverflow.com/questions/75179976/daily-release-using-semantic-release)).

**How teams work around it today:**
- **semantic-release:** CI cron job triggers `npx semantic-release` on a
  schedule. If no releasable commits exist, it's a no-op. Works but has
  no batching — every cron run is independent.
- **release-it:** Same approach — CI cron + `npx release-it --ci`. No
  built-in scheduling.
- **release-please:** GitHub Action runs on every push to main, creates
  a release PR. Merging the PR triggers the release. No scheduling.

**What's missing across all tools:**
1. **Batched releases** — Accumulate commits over a time window, release
   once. Current tools release per-commit or require manual trigger.
2. **Release cadence config** — `release_cadence = "daily"` or
   `release_cadence = "weekly:monday"` in config.
3. **Minimum change threshold** — Don't release if only `chore:` commits
   accumulated (no version bump needed).
4. **Release windows** — Only release during business hours or specific
   days (avoid Friday deploys).
5. **Cooldown period** — Minimum time between releases to prevent
   rapid-fire publishing.

**Current releasekit state:** No scheduling support. Releasekit is
invoked manually or via CI triggers.

**Recommendation:**
- Add `[schedule]` section to `releasekit.toml`:
  ```toml
  [schedule]
  cadence = "daily"          # or "weekly:monday", "biweekly", "on-push"
  release_window = "09:00-17:00"  # UTC, optional
  cooldown_minutes = 60      # minimum time between releases
  min_bump = "patch"         # skip release if only chore/docs commits
  ```
- Add `releasekit should-release` command that returns exit code 0 if a
  release should happen (for CI cron integration):
  ```yaml
  # GitHub Actions example
  on:
    schedule:
      - cron: '0 9 * * 1-5'  # weekdays at 9am UTC
  jobs:
    release:
      steps:
        - run: releasekit should-release || exit 0
        - run: releasekit publish --ci
  ```
- The `should-release` command checks: (a) releasable commits exist,
  (b) within release window, (c) cooldown elapsed, (d) minimum bump met.

### 8.2 Release-Per-Commit / Continuous Deployment

**The problem:** Some teams want every merge to main to produce a release
(trunk-based development). semantic-release was designed for this but
struggles with monorepos ([#1529](https://github.com/semantic-release/semantic-release/issues/1529)).
release-it requires manual `--ci` invocation.

**Current releasekit state:** Releasekit supports `releasekit publish`
which can be triggered on every push. However, there's no explicit
"continuous release" mode that:
1. Skips release PR creation (direct publish on merge).
2. Handles concurrent CI runs safely (two merges in quick succession).
3. Provides idempotency (re-running on the same commit is a no-op).

**Recommendation:**
- Add `release_mode = "continuous"` config option (vs default `"pr"`):
  ```toml
  [workspace]
  release_mode = "continuous"  # publish on every merge, no release PR
  ```
- In continuous mode, `releasekit publish` should:
  - Check if current HEAD already has a release tag → no-op.
  - Use the release lock to prevent concurrent publishes.
  - Skip PR creation, go directly to tag + publish.
- Add `--if-needed` flag: `releasekit publish --if-needed` exits 0
  without error if no releasable changes exist.

### 8.3 Trunk-Based Development Support

**The problem:** semantic-release [#1529](https://github.com/semantic-release/semantic-release/issues/1529)
highlights confusion about how release tools integrate with trunk-based
development. Key questions from users:
- Should releases happen from trunk or from release branches?
- How do feature branches interact with release automation?
- How do pre-releases map to trunk-based development?

**Current releasekit state:** Releasekit is branch-agnostic — it works
from whatever branch you run it on. But there's no documentation or
configuration for trunk-based workflows specifically.

**Recommendation:**
- Document a "Trunk-Based Development" recipe in docs:
  - Continuous mode: every merge to main → release.
  - Release branches: `release/v1.x` for maintenance, main for latest.
  - Feature flags over feature branches for unreleased work.
- Add `branch_channels` config for mapping branches to release channels:
  ```toml
  [branches]
  main = "latest"
  "release/v1.*" = "v1-maintenance"
  "next" = "next"
  ```

### 8.4 Plugin-vs-Built-in Analysis

A key architectural difference between releasekit and alternatives:

**release-it's plugin model:**
- Core does: git tag, git push, npm publish, GitHub/GitLab release.
- Everything else requires plugins: conventional commits, changelog,
  monorepo, pnpm, CalVer, .NET, Gitea, version bumping in non-JS files.
- **Pro:** Minimal core, community can extend.
- **Con:** Fragmented ecosystem, version compatibility issues between
  plugins, no guarantee of quality, monorepo support is bolted on.

**semantic-release's plugin model:**
- Core does: version determination, git tag.
- Plugins for: npm publish, GitHub release, changelog, commit analysis.
- Even the default behavior requires `@semantic-release/npm`,
  `@semantic-release/github`, `@semantic-release/commit-analyzer`.
- **Pro:** Extremely flexible.
- **Con:** Confusing for beginners (need 4+ plugins for basic use),
  monorepo support is a third-party plugin (`semantic-release-monorepo`)
  that's frequently broken.

**releasekit's built-in model:**
- Core does: everything needed for a complete release workflow.
- No plugins needed for: conventional commits, changelog, monorepo,
  dependency graph, health checks, auto-fix, multi-forge, multi-ecosystem,
  rollback, retry, dry-run, version preview.
- **Pro:** Works out of the box, consistent behavior, no version
  compatibility matrix, monorepo is first-class.
- **Con:** Less extensible for niche use cases, larger core surface area.

**What alternatives need plugins for that releasekit does out-of-the-box:**

| Capability | semantic-release plugin | release-it plugin | releasekit |
|---|---|---|---|
| Conventional commits | `@semantic-release/commit-analyzer` | `@release-it/conventional-changelog` | ✅ Built-in |
| Changelog | `@semantic-release/changelog` | `@release-it/conventional-changelog` | ✅ Built-in |
| npm publish | `@semantic-release/npm` | Built-in | ✅ Built-in |
| GitHub release | `@semantic-release/github` | Built-in | ✅ Built-in |
| GitLab release | `@semantic-release/gitlab` | Built-in | ✅ Built-in |
| Monorepo | `semantic-release-monorepo` (3rd party) | `@release-it-plugins/workspaces` | ✅ Built-in |
| Dep graph ordering | ❌ Not available | ❌ Not available | ✅ Built-in |
| Health checks | ❌ Not available | ❌ Not available | ✅ Built-in |
| Auto-fix | ❌ Not available | ❌ Not available | ✅ Built-in |
| Rollback | ❌ Not available | ❌ Not available | ✅ Built-in |
| Version preview | ❌ Not available | `--release-version` flag | ✅ Built-in (`plan`, `version`) |
| Retry/backoff | ❌ Not available | ❌ Not available | ✅ Built-in |
| Multi-ecosystem | ❌ JS only | ❌ JS only (plugins for others) | ✅ Py/JS/Go/Rust/Java/Dart |
| Revert handling | ❌ Not available | ❌ Not available | ✅ Built-in |

**Recommendation:** Releasekit's built-in approach is the right default.
However, consider adding a lightweight hooks system (like release-it's
`before:init` / `after:release`) for teams that need custom steps without
writing a full plugin. This could be as simple as:
```toml
[hooks]
before_publish = ["npm run build", "npm test"]
after_publish = ["./scripts/notify-slack.sh"]
after_tag = ["echo 'Tagged ${version}'"]
```

---

## 9. UPDATED FEATURE COMPARISON MATRIX

| Feature | releasekit | release-please | semantic-release | python-semantic-release | release-it | changesets | nx release | knope | goreleaser |
|---------|-----------|----------------|-----------------|------------------------|------------|------------|------------|-------|------------|
| **Monorepo** | ✅ | ✅ | ❌ (plugin) | ❌ | ❌ (plugin) | ✅ | ✅ | ✅ | ❌ |
| **Polyglot** | ✅ Py/JS/Go/Rust/Java/Dart | Multi-lang | JS-centric | Python-only | JS (plugins for others) | JS-only | JS/Rust/Docker | Multi | Go-only |
| **Conv. commits** | ✅ | ✅ | ✅ (plugin) | ✅ | ❌ (plugin) | ❌ | ✅ | ✅ | ✅ |
| **Changesets** | ✅ | ❌ | ❌ | ❌ | ❌ (plugin) | ✅ | ✅ (version plans) | ✅ | ❌ |
| **Dep graph** | ✅ | Partial | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **Topo publish** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Health checks** | ✅ (34) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Auto-fix** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-forge** | ✅ GH/GL/BB | GitHub only | GH/GL/BB | GH/GL/BB | GH/GL | GitHub only | ❌ | GH/Gitea | GitHub only |
| **Pre-release** | ✅ | Partial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Dry-run** | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Rollback** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Version preview** | ✅ | ❌ | ❌ | ❌ | ✅ (`--release-version`) | ❌ | ✅ | ❌ | ❌ |
| **Graph viz** | ✅ dot/mermaid/d2 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Shell completions** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Error explainer** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Retry/backoff** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Release lock** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Distro pkg sync** | ✅ Deb/RPM/Brew | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Hooks** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Interactive mode** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Scheduled releases** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Continuous deploy** | ✅ | ❌ | ✅ | ✅ | ✅ (`--ci`) | ❌ | ❌ | ❌ | ❌ |
| **Re-run release** | ❌ | ❌ | ❌ | ❌ | ✅ (`--no-increment`) | ❌ | ❌ | ❌ | ❌ |
| **Programmatic API** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **PEP 440** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **CalVer** | ✅ | ❌ | ❌ | ❌ | ❌ (plugin) | ❌ | ❌ | ❌ | ❌ |
| **Cherry-pick** | ✅ | ❌ | Partial | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Signing** | ✅ Sigstore | ❌ | npm provenance | ❌ | npm OIDC | ❌ | ❌ | ❌ | ✅ GPG/Cosign |
| **SBOM** | ✅ CycloneDX/SPDX | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Announcements** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 10. IMPLEMENTATION STATUS

### Completed (34 items)

1. ✅ **pnpm workspace publish pipeline** — `PnpmBackend` + `NpmRegistry`.
2. ✅ **Revert commit handling** — Per-level bump counters with revert cancellation.
3. ✅ **`releasekit doctor`** — `run_doctor()` with 6 checks.
4. ✅ **Pre-release workflow** — `prerelease.py` (PEP 440 + semver, `promote` CLI).
5. ✅ **npm dist-tag support** — `--dist-tag` CLI flag.
6. ✅ **`--publish-branch` + `--provenance`** — `PnpmBackend.publish()`.
7. ✅ **Internal dependency version propagation** — BFS via `graph.reverse_edges`.
8. ✅ **Contributor attribution in changelogs** — `ChangelogEntry.author`.
9. ✅ **Continuous deploy mode** — `release_mode = "continuous"` + `--if-needed`.
10. ✅ **`releasekit should-release`** — CLI subcommand.
11. ✅ **Lifecycle hooks** — `hooks.py` with 4 lifecycle events.
12. ✅ **Incremental changelog generation** — `write_changelog_incremental()`.
13. ✅ **Hotfix / maintenance branch support** — `hotfix.py`.
14. ✅ **Cherry-pick for release branches** — `cherry_pick_commits()`.
15. ✅ **Snapshot releases** — `snapshot.py`.
16. ✅ **`bootstrap-sha` config** — `bootstrap_sha` on `WorkspaceConfig`.
17. ✅ **Scheduled / cadence-based releases** — `should_release.py`.
18. ✅ **Branch-to-channel mapping** — `channels.py`.
19. ✅ **Sigstore signing + verification** — `signing.py`.
20. ✅ **SBOM generation** — `sbom.py` (CycloneDX + SPDX).
21. ✅ **Auto-merge release PRs** — `auto_merge` config.
22. ✅ **Custom changelog templates** — Jinja2 support.
23. ✅ **Announcement integrations** — `announce.py` (Slack, Discord, webhooks).
24. ✅ **Optional changeset file support** — `changesets.py`.
25. ✅ **Programmatic Python API** — `api.py` with `ReleaseKit` class.
26. ✅ **CalVer support** — `calver.py`.

### Remaining

1. **Plugin system for custom steps**.
2. **Cross-compilation orchestration** (for CLI binaries).
3. **`releasekit migrate`** — Protocol-based migration from alternatives.
4. **Bazel workspace backend** (BUILD files, `bazel run //pkg:publish`).
5. **Rust/Cargo workspace backend** (`Cargo.toml`, `cargo publish`).
6. **Java backend** (Maven `pom.xml` / Gradle `build.gradle`, `mvn deploy`).
7. **Dart/Pub workspace backend** (`pubspec.yaml`, `dart pub publish`).
8. **Rustification** — Rewrite core in Rust with PyO3/maturin.

> **See [../roadmap.md](../roadmap.md)** for the detailed implementation
> roadmap with dependency graphs.

---

## Methodology

- Scanned **open and closed issues** sorted by most comments and most 👍
  reactions across all repositories.
- Read README and documentation for feature comparison.
- Analyzed Genkit JS release scripts (`js/scripts/bump_version.sh`,
  `scripts/release_main.sh`, `scripts/cli-releases/`) and GitHub Actions
  workflows (`bump-js-version.yml`, `release_js_main.yml`, etc.).
- Cross-referenced against releasekit's codebase (`cli.py`, `versioning.py`,
  `changelog.py`, `checks/`, `backends/`, `config.py`, `net.py`,
  `scheduler.py`).
- Compared against 9 tools: release-please, semantic-release,
  python-semantic-release, release-it, changesets, nx release, knope,
  goreleaser, jreleaser.
- Focused on issues with high community engagement (comments, reactions) as
  indicators of real pain points rather than edge cases.
- Analyzed plugin-vs-built-in architectural tradeoffs across release-it,
  semantic-release, and releasekit (see §8.4).
