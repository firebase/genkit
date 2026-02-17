# Changelog

## 0.6.0 (2026-02-17)

### Features

- **releasekit**: add default branch detection, and packaging (202431c, #4650) — @Yesudeep Mangalapilly
- **py/conform**: isolate tool from repo, add concurrency controls, handle flaky tests (27e77b8, #4618) — @Yesudeep Mangalapilly
- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/samples**: add web-endpoints-hello — REST + gRPC kitchen-sink sample (8614e5e, #4498) — @Yesudeep Mangalapilly

### Bug Fixes

- **conform,anthropic**: native executors, tool schema handling, and CLI consolidation (f9223b5, #4698) — @Yesudeep Mangalapilly
- **releasekit**: replace literal null byte with git %x00 escape in changelog format (4866724, #4661) — @Yesudeep Mangalapilly
- issues reported by releasekit (fba9ed1, #4646) — @Yesudeep Mangalapilly
- **py/xai**: add structured output and streaming tool chunks (f7867bf, #4611) — @Yesudeep Mangalapilly
- **py**: resolve CI license check failures and lint diagnostics (e8519ef, #4524) — @Yesudeep Mangalapilly
- **py/plugins**: fix wheel build duplicate files in PEP 420 namespace packages (0c396b6, #4441) — @Yesudeep Mangalapilly

### Refactoring

- **py/plugins**: extract converters, add tests, community labeling (ebd0a2e, #4520) — @Yesudeep Mangalapilly
- **py/samples**: standardize naming taxonomy, consolidate shared logic, and close feature coverage gaps (1996c7c, #4488) — @Yesudeep Mangalapilly
- **py**: rename aws-bedrock plugin to amazon-bedrock (8acd6b0, #4448) — @Yesudeep Mangalapilly

All notable changes to `genkit-plugin-xai` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

- See the [workspace CHANGELOG](../../CHANGELOG.md) for a comprehensive list of changes.

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.5.0
