# A Letter to the Next Maintainer

> **Audience:** Future maintainers of the Genkit Python SDK.
>
> **TL;DR:** The monorepo and releasekit exist to protect users from
> broken installs. Do not split the plugins into separate repositories.
> Do not replace releasekit with shell scripts. This document explains
> why.

---

# Part I — Why the Plugins Live in the Same Repo

## 1. Atomic Cross-Cutting Changes

Many changes touch the core SDK *and* multiple plugins simultaneously:

- A new field in `GenerateRequest` requires every model plugin to handle it.
- A type signature change in `ai.Tool` ripples into every plugin that
  defines tools.
- A breaking change in the reflection API affects every plugin's action
  registration.

In a monorepo, this is **one PR, one review, one merge, one CI run**.
In a multi-repo world, it becomes N coordinated PRs across N repos,
each waiting on the core release to land first, each with its own CI
pipeline, each needing a reviewer who understands the cross-repo
context. You will lose days to coordination overhead on every
non-trivial change.

## 2. Version Synchronization

All plugins share a single version number (e.g., `0.5.0`). This is
intentional — users install `genkit==0.5.0` and
`genkit-plugin-google-genai==0.5.0` and expect them to work together
without compatibility matrices.

Releasekit bumps all plugin versions in lockstep from a single
`releasekit.toml`. If plugins lived in separate repos:

- You'd need a cross-repo version coordination tool (or do it manually).
- Users would hit version skew bugs that are nearly impossible to
  reproduce locally.
- Every plugin release would need to wait for the core release to
  propagate to PyPI before CI can even install the new core.

## 3. CI and Testing

The monorepo CI runs **all** plugin tests against the *current* core
code on every PR. This catches breakage immediately, before it ships.

Split repos mean:

- Plugin CI tests against the *last published* core, not the current
  HEAD. Breakage is discovered after the core release, not before.
- You need nightly or cron jobs to test each plugin against core HEAD —
  and someone has to triage failures across N repos.
- Conformance tests (which validate every model plugin against a shared
  spec) become a multi-repo orchestration nightmare.

## 4. Shared Infrastructure

The following are shared across all plugins and would need to be
duplicated or extracted into yet another repo:

| What | Where |
|------|-------|
| Lint config (Ruff, ty, pyrefly, pyright) | `py/pyproject.toml` |
| Consistency checks | `py/bin/check_consistency` |
| License header checks | `bin/check_license` |
| Release automation | `py/tools/releasekit/` |
| Model conformance test infra | `py/tests/conformance/` |
| Shared test fixtures | `py/tests/` |
| GitHub Actions workflows | `.github/workflows/` |
| Documentation build | `py/docs/` |

Splitting means maintaining N copies of lint configs that drift, N
CI pipelines that diverge, and N sets of release scripts that each
have their own bugs.

## 5. Developer Experience

A new contributor can:

1. Clone one repo.
2. Run `uv sync`.
3. Have every plugin, sample, and test available locally.
4. Run `bin/lint` and know the entire project is clean.

Split repos turn this into "clone 20 repos, figure out which ones
you need, hope the versions align, set up each one individually."

## 6. Discoverability

Users browse the repo and see every available plugin. They can
search across all plugins for usage patterns. They can copy code
from one plugin to another. Everything is indexed in one place.

## 7. Users Don't Blame the Plugin — They Blame Genkit

This is the most important section in this document.

When a user runs `pip install genkit genkit-plugin-anthropic` and
their first `generate()` call throws a `TypeError` because the plugin
hasn't been updated for a core API change, they don't think "the
Anthropic plugin is out of date." They think **"Genkit doesn't work."**

They close the tab. They open LangChain or LlamaIndex. They never
come back. You don't get a bug report. You don't get a second chance.

This is what happens in a multi-repo world:

1. Core ships a release on Monday. Plugins are in separate repos.
2. The Anthropic plugin maintainer is busy. They update on Thursday.
3. The Ollama plugin maintainer is on vacation. It ships the
   following week.
4. For that entire window, **any user** who installs the latest core
   with the stale plugin gets a broken experience.
5. Multiply this by 19 plugins and every release cycle.

In the monorepo, this **cannot happen**. A PR that changes the core
API must update every plugin in the same PR, or CI fails. The user
always gets a working combination because incompatible states are
never publishable.

**Every broken plugin is a user who gives up on Genkit.** The
monorepo is the only architecture that guarantees users always get
a working SDK. Protect that invariant above all else.

## 8. "But Google/Facebook/etc. Split Their Plugins"

Some ecosystems with hundreds of plugins across dozens of teams
do split. But they also have:

- Dedicated release engineering teams.
- Custom cross-repo CI orchestration (like Google's TAP).
- Internal monorepo tooling (Bazel, Buck) that handles cross-repo
  deps natively.
- Hundreds of engineers to absorb the coordination overhead.

We are a small team. The monorepo is our force multiplier.

## 9. When Splitting *Would* Make Sense

For completeness, here are the rare cases where splitting is justified:

- **A plugin has a fundamentally different release cadence** (e.g.,
  daily releases tied to a rapidly-changing external API). Even then,
  consider a separate release group in `releasekit.toml` first.
- **A plugin has incompatible licensing** (e.g., GPL dependency in an
  otherwise Apache-2.0 repo). This hasn't happened.
- **The repo becomes so large that clone/CI times are untenable.**
  We're nowhere near this — the entire `py/` tree is a few MB.

None of these apply today. If they do in the future, split *that one
plugin*, not all of them.

## Monorepo Summary

| Concern | Monorepo | Multi-Repo |
|---------|----------|------------|
| Atomic cross-cutting changes | 1 PR | N coordinated PRs |
| Version sync | Automatic | Manual or custom tooling |
| CI catches breakage | Before release | After release |
| Lint/config consistency | One source of truth | N drifting copies |
| Developer onboarding | Clone once, run once | Clone N repos, configure each |
| Release automation | One tool, one config | N pipelines |
| Discoverability | Grep the repo | Search across N repos |
| User trust | Plugins always match core | Version skew → "Genkit is broken" |

**Keep it together. Your future self will thank you.**

---

# Part II — Why Releasekit Exists

Releasekit was built because releasing 19+ packages from a monorepo
has dozens of edge cases that will bite you if you try to do it with
shell scripts or manual processes. Every feature exists because we
hit the bug it prevents.

Releasekit is **ecosystem-agnostic** — it supports Python (uv), JS
(pnpm), Go, Dart (pub), Java/Kotlin (Maven/Gradle), Clojure
(Leiningen/tools.deps), and Rust (Cargo). Each ecosystem has a
workspace backend that discovers packages, a package manager backend
that builds/publishes, and a registry backend that verifies
availability. Adding a new ecosystem means implementing three
protocols — no changes to the core orchestration.

## The Release Process

A single release involves:

1. Parsing conventional commits to determine version bumps.
2. Bumping versions in 19+ `pyproject.toml` files.
3. Generating per-package changelogs.
4. Creating a release PR with an embedded manifest.
5. Creating per-package git tags and an umbrella tag.
6. Building 19+ source distributions and wheels.
7. Pinning internal dependencies to exact versions for PyPI.
8. Publishing in topological order (core before plugins).
9. Verifying each package appears on PyPI.
10. Restoring the pinned files to their original state.
11. Creating a GitHub release with release notes.
12. Bumping to `.dev0` versions post-release.

If *any* of these steps fails partway through, you need to recover
gracefully. This is what releasekit does.

## Edge Cases Releasekit Handles

### Dependency Ordering

Plugins depend on the core package. If you publish `genkit-plugin-foo`
before `genkit`, pip installs on user machines will fail because the
dependency doesn't exist on PyPI yet.

**What releasekit does:**
- Builds a dependency graph from workspace `pyproject.toml` files.
- Detects circular dependencies before attempting anything.
- Computes topological levels (core = level 0, plugins = level 1).
- Publishes in dependency order with configurable concurrency per level.
- Uses a dependency-triggered scheduler: packages start as soon as
  their deps complete, not when the entire level finishes.

### Ephemeral Dependency Pinning

In the monorepo, `pyproject.toml` files use `[tool.uv.sources]` to
resolve dependencies locally. PyPI doesn't understand these — it needs
exact version pins like `genkit==0.5.0`.

**What releasekit does:**
- Rewrites `pyproject.toml` with exact version pins before building.
- Restores the original file byte-for-byte after publishing.
- Verifies restoration with SHA-256 checksums.
- Registers `atexit` and signal handlers (SIGTERM/SIGINT) so the
  original file is restored even if the process is killed.
- Keeps a `.bak` file as a last resort for manual recovery.

### Already-Published Versions

PyPI is immutable — you cannot re-upload a version that already exists.
If a release is partially complete (3 of 19 packages published) and
the process crashes, re-running must skip the already-published ones.

**What releasekit does:**
- Checks the registry before publishing each package.
- Skips packages whose version already exists on PyPI.
- Preflight checks warn about version conflicts before starting.

### Resume After Crash

A CI runner can die mid-release (OOM, timeout, network flap). You
need to resume without re-publishing what already succeeded.

**What releasekit does:**
- Persists per-package status to a JSON state file after each step.
- Uses atomic writes (`tempfile` + `os.replace`) so the state file
  is never corrupted by a mid-write crash.
- Validates that HEAD SHA matches the state file's SHA on resume —
  if someone pushed a commit between the crash and the retry, the
  state is invalidated because versions may have changed.
- Status transitions: `pending → building → publishing → verifying →
  published` (or `→ failed`).

### Stale Build Artifacts

If a `dist/` directory contains leftover `.whl` or `.tar.gz` files
from a previous build, `uv publish` may upload the wrong artifacts.

**What releasekit does:**
- Preflight check scans every package for non-empty `dist/` dirs.
- Fails the release before any publishing happens.

### Shallow Git Clones

GitHub Actions uses `fetch-depth: 1` by default. This truncates git
history, which means conventional commit parsing finds zero commits
and computes zero version bumps.

**What releasekit does:**
- Preflight check detects shallow clones and warns.
- Workflows use `fetch-depth: 0` and `fetch-tags: true`.

### Registry Verification

Publishing to PyPI returns 200 immediately, but the package may not
be installable for several minutes (CDN propagation, index updates).
If you tag the release and announce it before the package is actually
available, users get `404 Not Found` from pip.

**What releasekit does:**
- Polls the registry after publishing until the package resolves.
- Configurable timeout and polling interval.
- Verifies SHA-256 checksums of the published artifacts against
  local build output to catch upload corruption.

### Publish Retries with Backoff

PyPI and npm can return transient 5xx errors. A single failure
shouldn't abort a 19-package release.

**What releasekit does:**
- Retries failed publishes with exponential backoff + full jitter.
- Configurable `max_retries` (exposed as a workflow input).
- Maximum backoff capped at 60 seconds.
- Each retry is logged with attempt number and delay.

### Concurrent Publishing

Publishing 19 packages sequentially takes a long time. But publishing
all 19 in parallel can overwhelm PyPI's rate limits.

**What releasekit does:**
- Semaphore-controlled concurrency within each topological level.
- Configurable `concurrency` (exposed as a workflow input).
- The scheduler dispatches packages as soon as dependencies complete,
  maximizing parallelism without violating ordering constraints.

### Trusted Publishing (OIDC)

API tokens are a security liability. PyPI supports OIDC-based
"trusted publishing" where the CI platform proves its identity
without long-lived secrets.

**What releasekit does:**
- Preflight check detects when publishing from CI without OIDC.
- Warns but doesn't block (local publishing with tokens is still
  valid).
- Checks for GitHub Actions, GitLab CI, and CircleCI OIDC tokens.

### Lock File Drift

If `uv.lock` is out of date, the build may use different dependency
versions than what was tested in CI.

**What releasekit does:**
- Preflight check runs `uv lock --check` to verify the lock file.
- Fails the release if the lock file needs updating.

### Metadata Validation

PyPI rejects uploads with missing metadata fields (`description`,
`license`, `requires-python`, `authors`). Discovering this after
publishing 10 of 19 packages is painful.

**What releasekit does:**
- Preflight check validates required metadata in every package's
  `pyproject.toml` before building anything.

### Vulnerability Scanning

Publishing a package with known CVEs is a bad look.

**What releasekit does:**
- Optional preflight check runs `pip-audit` against the workspace.
- Advisory only (doesn't block) because vulnerability databases
  may flag false positives in transitive dependencies.

### Changelog Generation

Manually writing changelogs for 19 packages is tedious and error-prone.

**What releasekit does:**
- Parses conventional commits (`feat:`, `fix:`, `chore:`, etc.).
- Scopes commits to the package they modified (using file paths).
- Generates per-package changelogs with categorized sections.
- Generates umbrella release notes summarizing all packages.
- Embeds the release manifest in the PR body for machine parsing.

### Tag Management

Each package gets its own tag (`genkit-v0.5.0`) plus an umbrella
tag (`v0.5.0`). Tags must be idempotent — re-running shouldn't fail
if a tag already exists.

**What releasekit does:**
- Skips tags that already exist (logged, not errored).
- Supports secondary tag formats (e.g., npm-scoped `@genkit-ai/core@1.2.3`).
- Supports tag deletion for rollback scenarios.
- Supports draft releases in CI mode (tag before publish, promote
  after all packages succeed).

### Post-Release Version Bumping

After a release, all packages should be bumped to `X.Y.Z+1.dev0` so
that local development builds are always newer than the release.

**What releasekit does:**
- Computes the next dev version automatically.
- Creates a commitback PR with the bumped versions.
- Handles forge unavailability gracefully (pushes the branch even
  if PR creation fails).

### Graceful Degradation

Not every environment has `gh` CLI, `pip-audit`, or network access.

**What releasekit does:**
- Every backend is injected via dependency injection.
- Missing tools produce warnings, not failures.
- Forge operations (PR creation, releases) are skipped gracefully
  when the forge is unavailable.
- All checks are categorized as blocking (fail) or advisory (warn).

## Why Not Use Existing Tools?

| Tool | Why it didn't work |
|------|-------------------|
| **release-please** | Designed for single-package repos. Monorepo support is limited and doesn't handle topological publishing. |
| **semantic-release** | Node-only. Python support via plugins is incomplete. No dependency-ordered publishing. |
| **changesets** | Excellent for JS, but no Python ecosystem support. No registry verification. |
| **Manual scripts** | We tried. The edge cases above accumulated as shell script spaghetti that no one wanted to maintain. |
| **uv publish** (raw) | Handles a single package. Doesn't know about workspace ordering, pinning, verification, or resume. |

Releasekit was built incrementally as each of these edge cases bit us
in production. Every module exists because a release failed without it.

## Releasekit Architecture

Every module is tested with fake backends (no network, no git, no
registry calls in tests). The backends are pluggable via protocols:
VCS (Git, Mercurial), PackageManager (uv, pnpm, Go, Dart, Maven,
Cargo), Registry (PyPI, npm, Go proxy, pub.dev, Maven Central,
crates.io), Forge (GitHub, GitLab, Bitbucket), and Workspace
(package discovery per ecosystem).

**If you're tempted to replace releasekit with shell scripts, read
Part II again first.** The edge cases are real, and they will find you
in production at the worst possible time.

## Release Tool Invariants

These are **hard requirements** — violations are P0 bugs. Tests live
in `tests/rk_invariants_test.py`.

| Key | Invariant | One-liner |
|-----|-----------|----------|
| `INV-IDEMPOTENCY` | Idempotency | Re-running a command is always safe |
| `INV-CRASH-SAFETY` | Crash Safety | Interrupted releases resume without re-publishing |
| `INV-ATOMICITY` | Atomicity | Each publish fully succeeds or fully fails |
| `INV-DETERMINISM` | Determinism | Same inputs always produce same outputs |
| `INV-OBSERVABILITY` | Observability | Every action emits structured logs |
| `INV-DRY-RUN` | Dry-Run Fidelity | `--dry-run` exercises real code paths |
| `INV-GRACEFUL-DEGRADATION` | Graceful Degradation | Missing optional components degrade to no-ops |
| `INV-TOPO-ORDER` | Topological Correctness | Packages publish in dependency order |
| `INV-SUPPLY-CHAIN` | Supply Chain Integrity | Published artifacts are verified against checksums |

---

# A Note from the Team

If you're reading this, you've inherited a codebase that we poured a
lot of care into. We hope the architecture makes sense, the tests give
you confidence, and the tooling saves you time.

The Python SDK was built by (in order of contribution):

- **Yesudeep Mangalapilly** — architecture, plugins, release tooling,
  conformance testing, docs
- **Pavel Jbanov** — core framework, early plugin foundations
- **Mengqin Shen (Elisa)** — sample testing, plugin fixes, Dev UI,
  embedding migration
- **Abraham J. Lázaro** — plugin contributions
- **Niraj Nepal** — telemetry (AIM, Firebase), logging
- **Jeff Huang** — plugin contributions
- **Tatsiana Havina** — plugin contributions
- **Samuel Bushi** — plugin contributions
- **Kyrylo Hrymailo (Kirill Grimaylo)** — plugin contributions
- **Hendrik Martina** — plugin contributions
- **Roman Yermilov** — plugin contributions
- **Kamil Korski** — plugin contributions

…and community contributors including Ty Schlichenmeyer, Shruti P,
Sahdev Garg, Michael Doyle, Marcel Folaron, Madhav, Louise Kümmel,
Junhyuk Han, Hugo Aguirre, Nozomi Koborinai, Chris Ray Gill, and
Alex Pascal.

A few parting thoughts:

- **Maintaining this is hard work.** There are 19 plugins across
  multiple AI providers, each with their own API quirks, rate limits,
  auth flows, and breaking changes. Model capabilities shift under
  your feet. Dependencies update. CI breaks for reasons outside your
  control. It's not glamorous work, but it's the work that matters.
  Users come first. Developer convenience comes second. When you're
  torn between making something easier for yourself and making
  something more reliable for users, choose the users every time.
- **The abstractions are there for a reason.** Before removing
  something that looks like over-engineering, check the git blame —
  there's usually a bug or edge case that motivated it.
- **The tests are your safety net.** Run them often. Trust them when
  they're green. Fix them immediately when they're red.
- **The users are counting on you.** Every plugin, every sample, every
  doc page — someone out there is building something real with it.
  That's a privilege.

It was a joy to build this. We're proud of what we shipped, and we're
confident you'll take it further than we imagined.

Good luck, and have fun. 🚀

— The Genkit Python Team
