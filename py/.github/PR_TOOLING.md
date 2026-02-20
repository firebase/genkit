# PR: Release Tooling and Automation Improvements

## Summary
This PR introduces comprehensive release tooling and automation for the Genkit Python SDK, improving the release process reliability and developer experience.

## Changes

### CI/CD Improvements
- **Dynamic plugin matrix**: Automatically discovers plugins from `py/plugins/` directory instead of hardcoded list
- **Post-publish verification**: New workflow job that verifies packages are installable from PyPI after publishing
- **Publish summary**: GitHub Actions summary showing overall publish status and next steps
- **Publish-all option**: Ability to publish all packages with a single workflow trigger

### Release Scripts
- **`py/bin/create_release`**: Automates git tag creation and GitHub release from PR description
- **`py/bin/check_versions`**: Validates version consistency across all 59 packages (core + plugins + samples)
- **`py/bin/bump_version`**: Now includes samples in version bumping
- **`py/bin/validate_release_docs`**: Validates release documentation for common mistakes

### Shell Script Standards
- All scripts now use `#!/usr/bin/env bash` shebang (line 1)
- All scripts use `set -euo pipefail` for strict error handling
- Integrated `shellcheck` into `bin/lint` and `py/bin/release_check`
- Fixed shellcheck warnings in `publish_pypi.sh`, `validate_release_docs`

### API Documentation
- Added all 22 plugins to `mkdocs.yml` for complete API docs
- Updated `docs/index.md` with all 18 exports from `genkit.ai`
- Updated `docs/types.md` with all 40+ exports from `genkit.types`
- Fixed import paths for mkdocstrings compatibility

### Documentation Updates
- Updated `py/GEMINI.md` with:
  - Shell script standards (shebang, pipefail)
  - Version consistency requirements
  - Release publishing guide
- Updated `py/engdoc/ROADMAP.org` with:
  - Completed release management tasks
  - Future API documentation work items

## Testing
- [x] `mkdocs build` succeeds (3.01 seconds)
- [x] All shell scripts pass `shellcheck`
- [x] `bin/check_versions` correctly identifies version mismatches
- [x] `bin/lint` runs shellcheck on both `bin/` and `py/bin/`

## Files Changed
- `.github/workflows/publish_python.yml` - CI improvements
- `py/bin/create_release` - New release script
- `py/bin/check_versions` - New version check script
- `py/bin/bump_version` - Updated for samples
- `py/bin/validate_release_docs` - Fixed shebang/pipefail
- `py/bin/publish_pypi.sh` - Fixed shebang/shellcheck
- `py/bin/release_check` - Added root bin/ to shellcheck
- `bin/lint` - Added shellcheck for both directories
- `py/mkdocs.yml` - All plugins added
- `py/docs/index.md` - Complete API reference
- `py/docs/types.md` - Complete types reference
- `py/GEMINI.md` - Documentation updates
- `py/engdoc/ROADMAP.org` - Updated roadmap
