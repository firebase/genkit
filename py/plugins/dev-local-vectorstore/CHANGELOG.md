# Changelog

## 0.6.0 (2026-02-17)

### Features

- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/samples**: add web-endpoints-hello — REST + gRPC kitchen-sink sample (8614e5e, #4498) — @Yesudeep Mangalapilly

### Bug Fixes

- issues reported by releasekit (fba9ed1, #4646) — @Yesudeep Mangalapilly
- **py/dev-local-vectorstore**: migrate from pathlib to aiofiles for async I/O (57f691f, #4607) — @Yesudeep Mangalapilly
- **py**: migrate default embedding model to gemini-embedding-001 (051f75f, #4557) — @Elisa Shen
- **py/plugins**: fix wheel build duplicate files in PEP 420 namespace packages (0c396b6, #4441) — @Yesudeep Mangalapilly

### Refactoring

- **py**: rename aws-bedrock plugin to amazon-bedrock (8acd6b0, #4448) — @Yesudeep Mangalapilly

All notable changes to `genkit-plugin-dev-local-vectorstore` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

- See the [workspace CHANGELOG](../../CHANGELOG.md) for a comprehensive list of changes.

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.5.0
