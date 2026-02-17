# Changelog

## 0.6.0 (2026-02-17)

### Features

- **releasekit**: add default branch detection, and packaging (202431c, #4650) — @Yesudeep Mangalapilly
- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/samples**: add web-endpoints-hello — REST + gRPC kitchen-sink sample (8614e5e, #4498) — @Yesudeep Mangalapilly
- **py/plugins**: add reasoning_content extraction for DeepSeek R1 models (50e7c69, #4480) — @Yesudeep Mangalapilly

### Bug Fixes

- **releasekit**: replace literal null byte with git %x00 escape in changelog format (4866724, #4661) — @Yesudeep Mangalapilly
- issues reported by releasekit (fba9ed1, #4646) — @Yesudeep Mangalapilly
- **py/deepseek**: migrate from sync OpenAI to AsyncOpenAI client (d3c7a76, #4606) — @Yesudeep Mangalapilly
- **py/compat-oai**: migrate to AsyncOpenAI and fix string role mapping (e49de2c, #4605) — @Yesudeep Mangalapilly
- **py**: resolve CI license check failures and lint diagnostics (e8519ef, #4524) — @Yesudeep Mangalapilly
- **py/plugins**: fix wheel build duplicate files in PEP 420 namespace packages (0c396b6, #4441) — @Yesudeep Mangalapilly

### Refactoring

- **py/plugins**: extract converters, add tests, community labeling (ebd0a2e, #4520) — @Yesudeep Mangalapilly
- **py**: rename aws-bedrock plugin to amazon-bedrock (8acd6b0, #4448) — @Yesudeep Mangalapilly

All notable changes to `genkit-plugin-deepseek` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

- See the [workspace CHANGELOG](../../CHANGELOG.md) for a comprehensive list of changes.

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.5.0
