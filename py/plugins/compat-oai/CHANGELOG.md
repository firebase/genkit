# Changelog

## 0.6.0 (2026-02-17)

### Features

- **py/conform**: isolate tool from repo, add concurrency controls, handle flaky tests (27e77b8, #4618) — @Yesudeep Mangalapilly
- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/samples**: add web-endpoints-hello — REST + gRPC kitchen-sink sample (8614e5e, #4498) — @Yesudeep Mangalapilly
- **py/plugins**: add reasoning_content extraction for DeepSeek R1 models (50e7c69, #4480) — @Yesudeep Mangalapilly
- **py/compat-oai**: add multimodal model support (image, TTS, STT) (5358df2, #4477) — @Yesudeep Mangalapilly

### Bug Fixes

- **releasekit**: replace literal null byte with git %x00 escape in changelog format (4866724, #4661) — @Yesudeep Mangalapilly
- **py**: fix structlog config blowaway, DeepSeek reasoning, and double JSON encoding (ea0223b, #4625) — @Yesudeep Mangalapilly
- **py/plugins**: various model conformance fixes (974a7ff, #4617) — @Yesudeep Mangalapilly
- **py/anthropic**: fix streaming tool requests and structured output (5fe1b5f, #4615) — @Yesudeep Mangalapilly
- **py**: fix broken flows in shot-n-long and combat-oai (9bdf5fd, #4610) — @Elisa Shen
- **py/compat-oai**: strip markdown fences from DeepSeek JSON responses (d0a1b11, #4613) — @Yesudeep Mangalapilly
- **py/compat-oai**: migrate to AsyncOpenAI and fix string role mapping (e49de2c, #4605) — @Yesudeep Mangalapilly
- **py**: resolve CI license check failures and lint diagnostics (e8519ef, #4524) — @Yesudeep Mangalapilly
- **py/plugins**: fix wheel build duplicate files in PEP 420 namespace packages (0c396b6, #4441) — @Yesudeep Mangalapilly

### Refactoring

- **py/samples**: standardize naming taxonomy, consolidate shared logic, and close feature coverage gaps (1996c7c, #4488) — @Yesudeep Mangalapilly
- **py**: rename aws-bedrock plugin to amazon-bedrock (8acd6b0, #4448) — @Yesudeep Mangalapilly

All notable changes to `genkit-plugin-compat-oai` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

- See the [workspace CHANGELOG](../../CHANGELOG.md) for a comprehensive list of changes.

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.5.0
