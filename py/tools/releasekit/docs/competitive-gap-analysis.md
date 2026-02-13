# Releasekit Competitive Gap Analysis

**Date:** 2026-02-13
**Sources:** Issue trackers and documentation of:
- [release-please](https://github.com/googleapis/release-please) (Google)
- [semantic-release](https://github.com/semantic-release/semantic-release) (JS ecosystem)
- [python-semantic-release](https://github.com/python-semantic-release/python-semantic-release) (Python ecosystem)

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

**Current releasekit state:** The `version_pep440` check validates PEP 440
compliance, but version bumping itself uses SemVer. For Python packages,
pre-release suffixes should follow PEP 440 (`1.0.0a1`, `1.0.0rc1`) not
SemVer (`1.0.0-alpha.1`).

**Recommendation:**
- Support a `version_scheme = "pep440"` config option.
- Ensure `compute_bumps` produces PEP 440-compliant versions for Python
  packages and SemVer for JS/Go packages.

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

**Remaining:**
- `bootstrap-sha` config option (R26) for repos with long histories.
- Incremental changelog updates (append new entries rather than regenerating).

### 2.7 Stale State / "Stuck" Release Recovery
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#1946](https://github.com/googleapis/release-please/issues/1946) | "Untagged merged release PRs — aborting" |
| release-please [#2172](https://github.com/googleapis/release-please/issues/2172) | Manifest not updating |

**Current releasekit state:** ⚠️ **Mostly done.** The `rollback` subcommand
can delete tags and releases. `run_doctor()` in `doctor.py` implements 7
diagnostic checks (config, VCS, forge, registry, orphaned tags, branch,
packages). `list_tags` and `current_branch` added to VCS protocol
(2026-02-13). CLI wiring for `releasekit doctor` still pending.

**Remaining:**
- Wire `releasekit doctor` into CLI.
- Add `--bootstrap-sha` to `init` for repos adopting releasekit mid-stream.

---

## 3. NICE-TO-HAVE GAPS

### 3.1 GPG / Sigstore Signing and Provenance
| Alternative tool issue | Votes/Comments |
|---|---|
| release-please [#1314](https://github.com/googleapis/release-please/issues/1314) | GPG signing |
| semantic-release | npm provenance support |

**Current releasekit state:** The `pin.py` module has signing-related code,
and the scheduler has provenance references. No end-to-end GPG or Sigstore
signing workflow is exposed via CLI.

**Recommendation:**
- Add `--sign` flag to `publish` that invokes `gpg` or Sigstore for tag signing.
- Support PyPI Trusted Publishers / attestation workflows.

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

---

## 5. PRIORITIZED ROADMAP RECOMMENDATION

### Phase 1 (Next release)
1. **Pre-release workflow** (`--prerelease` flag + PEP 440 suffixes)
2. **Revert commit handling** (cancel out reverted bumps)
3. **`releasekit doctor`** (state consistency checker)

### Phase 2 (Following release)
4. **Internal dependency version propagation** (`fix_internal_dep_versions`)
5. **Contributor attribution in changelogs**
6. **Incremental changelog generation** (performance)
7. **Hotfix branch support** (`--base-branch`)

### Phase 3 (Future)
8. **Sigstore / GPG signing**
9. **Auto-merge release PRs**
10. **Custom changelog templates**
11. **Plugin system for custom steps**

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

**Gap to consider:**
- **Snapshot releases** — Useful for CI testing. Releasekit could add
  `--snapshot` flag that publishes `0.0.0-dev.<sha>` versions.
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

**Gap to consider:**
- **Hybrid conventional commits + changesets** — Knope's approach of
  supporting both is elegant. Releasekit could optionally read changeset
  files alongside conventional commits.

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
- **SBOM generation** — Increasingly required for supply chain security.
- **Announcement integrations** — Slack/Discord notifications on release.
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

---

## 8. UPDATED FEATURE COMPARISON MATRIX

| Feature | releasekit | release-please | semantic-release | python-semantic-release | changesets | nx release | knope | goreleaser |
|---------|-----------|----------------|-----------------|------------------------|------------|------------|-------|------------|
| **Monorepo** | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Polyglot** | ✅ Py/JS/Go | Multi-lang | JS-centric | Python-only | JS-only | JS/Rust/Docker | Multi | Go-only |
| **Conv. commits** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Changesets** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ (version plans) | ✅ | ❌ |
| **Dep graph** | ✅ | Partial | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **Topo publish** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Health checks** | ✅ (34) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Auto-fix** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-forge** | ✅ GH/GL/BB | GitHub only | GH/GL/BB | GH/GL/BB | GitHub only | ❌ | GH/Gitea | GitHub only |
| **Pre-release** | Partial | Partial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Dry-run** | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Rollback** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Version preview** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Graph viz** | ✅ dot/mermaid/d2 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Shell completions** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Error explainer** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Retry/backoff** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Release lock** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Distro pkg sync** | ✅ Deb/RPM/Brew | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cherry-pick** | Planned (R38) | ❌ | Partial | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Signing** | Partial | ❌ | npm provenance | ❌ | ❌ | ❌ | ❌ | ✅ GPG/Cosign |
| **SBOM** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Announcements** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 9. REVISED PRIORITIZED ROADMAP

### Phase 1 — Immediate (finalize JS migration readiness)

1. ✅ ~~**Wire up pnpm workspace publish pipeline**~~ — Done. `PnpmBackend`
   and `NpmRegistry` fully implemented. Ecosystem-aware `_create_backends()`.
2. ✅ ~~**Revert commit handling**~~ — Done. Per-level bump counters with
   revert cancellation.
3. ⚠️ **`releasekit doctor`** — `run_doctor()` implemented with 7 checks.
   CLI wiring pending.
4. **Pre-release workflow** (`--prerelease rc` flag + PEP 440 / SemVer
   pre-release suffixes). Basic `prerelease` param exists in `compute_bumps`.
5. ✅ ~~**npm dist-tag support**~~ — Done. `--dist-tag` CLI flag wired through
   `WorkspaceConfig` → `PublishConfig` → `PnpmBackend.publish(--tag)`.
6. ✅ ~~**`--publish-branch` + `--provenance`**~~ — Done. Both params added to
   `PnpmBackend.publish()`, `PublishConfig`, `WorkspaceConfig`, and CLI.

### Phase 2 — High value

7. ✅ ~~**Internal dependency version propagation**~~ — Done. BFS via
   `graph.reverse_edges`.
8. ✅ ~~**Contributor attribution in changelogs**~~ — Done. `ChangelogEntry.author`
   field, git log format `%H\x00%an\x00%s`, rendered as `— @author` (2026-02-13).
9. **Incremental changelog generation** (performance for large repos).
10. **Hotfix / maintenance branch support** (`--base-branch`).
11. **Cherry-pick for release branches** (`releasekit cherry-pick`).
12. **Snapshot releases** (`--snapshot` for CI testing).
13. ✅ ~~**`bootstrap-sha` config**~~ (R26) — Done. `bootstrap_sha` on
   `WorkspaceConfig`, threaded through `compute_bumps` and all CLI call sites (2026-02-13).

### Phase 3 — Differentiation

14. **Sigstore / GPG signing + provenance**.
15. **SBOM generation** (CycloneDX / SPDX).
16. ✅ ~~**Auto-merge release PRs**~~ — Done. `auto_merge` config on
   `WorkspaceConfig`, `prepare.py` calls `forge.merge_pr()` after labeling (2026-02-13).
17. **Custom changelog templates** (Jinja2).
18. **Announcement integrations** (Slack, Discord).
19. **Optional changeset file support** (hybrid with conventional commits).

### Phase 4 — Future

20. **Plugin system for custom steps**.
21. **Programmatic Python API** (like Nx Release's Node.js API).
22. **Cross-compilation orchestration** (for CLI binaries).
23. **`releasekit migrate`** — Protocol-based migration from alternatives.
24. **Bazel workspace backend** (BUILD files, `bazel run //pkg:publish`).
25. **Rust/Cargo workspace backend** (`Cargo.toml`, `cargo publish`).
26. **Java backend** (Maven `pom.xml` / Gradle `build.gradle`, `mvn deploy`).
27. **Dart/Pub workspace backend** (`pubspec.yaml`, `dart pub publish`).
28. **Rustification** — Rewrite core in Rust with PyO3/maturin (see roadmap §12).

> **See [../roadmap.md](../roadmap.md)** for the detailed roadmap with
> dependency graphs and execution phases.

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
- Compared against 8 tools: release-please, semantic-release,
  python-semantic-release, changesets, nx release, knope, goreleaser,
  jreleaser.
- Focused on issues with high community engagement (comments, reactions) as
  indicators of real pain points rather than edge cases.
