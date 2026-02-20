# PR: Genkit Python SDK v0.5.0 Release

## Summary
Version bump and release documentation for Genkit Python SDK v0.5.0.

## Changes

### Version Bump
- All packages bumped to version 0.5.0:
  - `packages/genkit` (core)
  - All 22 plugins
  - All 36 samples

### Release Documentation
- `CHANGELOG.md` - Comprehensive changelog with:
  - New features (Session/Chat, Dotprompt, Tool Interrupts)
  - Bug fixes and improvements
  - Contributor acknowledgments with PR links
- `PR_DESCRIPTION_0.5.0.md` - Release notes for GitHub

### Contributor Acknowledgments
13 contributors recognized with 188 total pull requests:
- @pavelgj (34 PRs) - Technical lead
- @nickstenning (27 PRs) - TypedDict handling, Pydantic v2
- @AJV009 (6 PRs) - Multi-modal vision, Fern docs
- @Vidit-Ostwal (2 PRs) - pytest-asyncio improvements
- @mbleigh (6 PRs) - Dotprompt spec, critical fixes
- @amanc1361 (1 PR) - xAI plugin
- @mgcam (1 PR) - Type hints
- And more...

## Testing
- [x] All tests pass
- [x] Version consistency verified
- [x] CHANGELOG has current version section

## Release Checklist
- [ ] Merge this PR
- [ ] Create release tag: `git tag -a py/v0.5.0 -m "Genkit Python SDK v0.5.0"`
- [ ] Push tag: `git push origin py/v0.5.0`
- [ ] Create GitHub release from tag
- [ ] Trigger publish workflow with `publish_scope: all`
- [ ] Verify packages on PyPI
