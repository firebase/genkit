# Changelog

## 0.6.0 (2026-02-17)

### Features

- **releasekit**: add default branch detection, and packaging (202431c, #4650) — @Yesudeep Mangalapilly
- **py/conform**: isolate tool from repo, add concurrency controls, handle flaky tests (27e77b8, #4618) — @Yesudeep Mangalapilly
- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/plugins**: add Cohere provider plugin (e424dcd, #4518) — @Yesudeep Mangalapilly

### Bug Fixes

- **releasekit**: replace literal null byte with git %x00 escape in changelog format (4866724, #4661) — @Yesudeep Mangalapilly
- issues reported by releasekit (fba9ed1, #4646) — @Yesudeep Mangalapilly
- **py**: fix tox test error for cohere plugin (5236ce8, #4614) — @Elisa Shen
- **py**: address releasekit check warnings for metadata and grouping (4f5a910, #4595) — @Yesudeep Mangalapilly

### Refactoring

- **py/plugins**: extract converters, add tests, community labeling (ebd0a2e, #4520) — @Yesudeep Mangalapilly

## 0.5.0 (Unreleased)

### Added
- Initial release of the Cohere AI plugin for Genkit.
- Chat model support via Cohere V2 API (Command A, Command R+, Command R,
  Command R7B, Command, Command Light).
- Streaming support for chat models.
- Tool calling support for Command A and Command R family models.
- Structured JSON output support.
- Embedding support (Embed v4.0, English/Multilingual v3.0 and light variants).
- Lazy model resolution via plugin registry.
