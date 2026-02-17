# Changelog

## 0.6.0 (2026-02-17)

### Features

- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/checks**: add Google Checks AI Safety plugin (a8bf3c1, #4504) — @Yesudeep Mangalapilly

### Bug Fixes

- **releasekit**: replace literal null byte with git %x00 escape in changelog format (4866724, #4661) — @Yesudeep Mangalapilly
- issues reported by releasekit (fba9ed1, #4646) — @Yesudeep Mangalapilly
- **py**: resolve CI license check failures and lint diagnostics (e8519ef, #4524) — @Yesudeep Mangalapilly

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-02-09

### Added

- Initial release of the `genkit-plugin-checks` package.
