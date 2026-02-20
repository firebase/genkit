# Release Workflow Migration Plan

Migrate the JS and Go release workflows from hand-rolled shell scripts
to releasekit-managed pipelines.  The Python workspace (`workspace.py`)
is already live.  JS and Go workspace configs exist in `releasekit.toml`
(commented out) and are ready to activate.

---

## Current State

### Python (live on releasekit)

| Item | Status |
| --- | --- |
| Workflow | `.github/workflows/releasekit-uv.yml` |
| Config | `[workspace.py]` in `releasekit.toml` |
| Features | prepare → release → publish → verify → notify |
| AI | Ollama + Google GenAI with model caching |
| Provenance | SLSA + PEP 740 + Sigstore |
| SBOM | CycloneDX + SPDX |

### JS (manual shell script)

| Item | Status |
| --- | --- |
| Workflow | `.github/workflows/release_js_main.yml` |
| Script | `scripts/release_main.sh` (123 lines, 20 hard-coded `cd`/`pnpm publish` pairs) |
| Version bumps | Manual — no conventional commit parsing |
| Changelog | None |
| Tags / GitHub Release | None |
| Retry on failure | None — if package 8 fails, 9-20 still attempt |
| Provenance | `--provenance=false` |
| SBOM | None |
| Registry | `wombat-dressing-room.appspot.com` (Google's npm proxy) |
| Dry run | None |

### Go (no automation)

| Item | Status |
| --- | --- |
| Workflow | None |
| Publishing | Manual `git tag` + Go module proxy auto-picks up |
| Config | `[workspace.go]` commented out in `releasekit.toml` |

---

## Migration Steps: JS

### Prerequisites

1. **Pick `bootstrap_sha`** — Find the last commit before releasekit
   adoption.  This is the commit from which releasekit starts scanning
   conventional commits for version bumps.

   ```bash
   # Find the last JS release tag
   git tag --list 'genkit@*' --sort=-version:refname | head -1
   # Get the commit it points to
   git rev-list -1 <tag>
   ```

2. **Verify wombat-dressing-room compatibility** — releasekit's
   `PnpmBackend` calls `pnpm publish`.  The registry URL is passed
   via `--registry`.  Confirm that `registry_url` in the workspace
   config is sufficient, or whether `NODE_AUTH_TOKEN` + `.npmrc`
   setup is also needed.

3. **Audit package list** — Compare the 20 packages in
   `release_main.sh` against what releasekit discovers.  Run:

   ```bash
   releasekit --workspace js plan --dry-run
   ```

### Step 1: Activate the JS workspace config

Uncomment `[workspace.js]` and `[workspace.js-cli]` in
`releasekit.toml`.  Set:

```toml
[workspace.js]
# ... existing config ...
bootstrap_sha = "<sha>"
registry_url  = "https://wombat-dressing-room.appspot.com/"
```

### Step 2: Dry-run validation

```bash
# Verify package discovery matches release_main.sh
releasekit --workspace js plan --format full

# Dry-run prepare (no PR created)
releasekit --workspace js prepare --dry-run

# Dry-run publish (no packages published)
releasekit --workspace js publish --dry-run
```

### Step 3: Create `releasekit-pnpm.yml`

Mirror the structure of `releasekit-uv.yml` with these differences:

- **Setup**: `pnpm/action-setup@v4` + `actions/setup-node@v6` instead
  of `astral-sh/setup-uv@v5`.
- **Install**: `pnpm install` (root workspace) + `uv sync` (releasekit
  tool).
- **Registry auth**: `NODE_AUTH_TOKEN` secret + `.npmrc` pointing to
  wombat-dressing-room.
- **Workspace flag**: `--workspace js` instead of `--workspace py`.
- **Ollama**: Same `setup-ollama` composite action for AI features.
- **Trigger paths**: `js/**`, `genkit-tools/**`.

### Step 4: Shadow run

Run the new workflow in parallel with the old one for 1-2 releases:

1. Use `--dry-run` on the new workflow.
2. Compare the output (tags, versions, publish order) against what
   `release_main.sh` actually did.
3. Verify the changelog and release notes quality.

### Step 5: Cut over

1. Remove `--dry-run` from the new workflow.
2. Disable the old `release_js_main.yml` (change trigger to
   `workflow_dispatch` only, like we did with `python-samples.yml`).
3. After 2-3 successful releases, delete the old workflow and
   `scripts/release_main.sh`.

### Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Wombat-dressing-room auth differs from standard npm | Test with `--dry-run` first; verify `.npmrc` setup |
| Package discovery misses a package | Compare `releasekit plan` output against `release_main.sh` list |
| Topological order differs from hard-coded order | releasekit uses dependency graph; verify with `plan --format full` |
| `--provenance=false` is intentional | Check if wombat-dressing-room supports provenance; if not, set `provenance = false` in config |
| `genkit-tools/` is a separate pnpm workspace root | Use `[workspace.js-cli]` with `root = "genkit-tools"` |

---

## Migration Steps: Go

### Go Prerequisites

1. **Pick `bootstrap_sha`** — Last commit before releasekit adoption
   for the Go module.

2. **Verify Go proxy behavior** — After `git tag go/v{version}`,
   the Go module proxy picks up the new version automatically.
   releasekit's `GoBackend` handles this.

### Go Step 1: Activate the workspace config

Uncomment `[workspace.go]` in `releasekit.toml`.  Set `bootstrap_sha`.

### Go Step 2: Dry-run validation

```bash
releasekit --workspace go plan --format full
releasekit --workspace go prepare --dry-run
```

### Go Step 3: Create `releasekit-go.yml`

Simpler than JS — Go doesn't need a publish step (tags are the
release mechanism).  The workflow only needs prepare + release jobs.

### Go Step 4: Cut over

Go has no existing automation, so there's no shadow-run needed.
Just enable the workflow.

---

## Feature Parity Checklist

Features that `releasekit-uv.yml` has and new workflows should match:

- [x] Prepare → Release → Publish → Verify → Notify pipeline
- [x] Manual dispatch with dry-run, group, bump-type, prerelease inputs
- [x] Concurrency control (one release at a time per ref)
- [x] Ollama + model caching via `.github/actions/setup-ollama`
- [x] SLSA provenance + Sigstore signing
- [x] SBOM generation (CycloneDX + SPDX)
- [x] Artifact upload (manifest, provenance, SBOM)
- [x] Post-release verification (install smoke test)
- [x] Downstream notification via `repository_dispatch`
- [ ] JS: wombat-dressing-room registry support (needs `registry_url`)
- [ ] JS: `NODE_AUTH_TOKEN` secret setup
- [ ] JS: `genkit-tools/` as separate workspace (`js-cli`)
- [ ] Go: tag-only release (no registry publish)
- [ ] Go: Go proxy verification instead of install smoke test
