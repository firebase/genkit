# Changelog

## 0.6.0 (2026-02-17)

### Features

- **releasekit**: add Forge protocol extensions, transitive propagation, and multi-backend conformance (d6dbb44, #4577) — @Yesudeep Mangalapilly
- **py/samples**: add web-endpoints-hello — REST + gRPC kitchen-sink sample (8614e5e, #4498) — @Yesudeep Mangalapilly
- **py/plugins/google-genai**: add Imagen support under googleai/ prefix (c4ed8a9, #4472) — @Yesudeep Mangalapilly
- **py/google-genai**: add Vertex AI rerankers and evaluators (9997401, #4428) — @Yesudeep Mangalapilly
- **py**: enables automated testing of all flows in any Genkit sample (0580e04, #4442) — @Elisa Shen

### Bug Fixes

- **py**: update google-genai evaluators and cleanup sample-test (c228dd7, #4648) — @Elisa Shen
- **py**: handle nullable JSON Schema types in Gemini plugin and clean up samples (4daef62, #4629) — @Yesudeep Mangalapilly
- **py**: resolve embedder output schema (ce14db1, #4554) — @Elisa Shen
- **py**: migrate default embedding model to gemini-embedding-001 (051f75f, #4557) — @Elisa Shen
- **py**: resolve CI license check failures and lint diagnostics (e8519ef, #4524) — @Yesudeep Mangalapilly
- **py**: fix model config consistencies for gemini (8a012b8, #4463) — @Elisa Shen
- **py/plugins**: move in-function import to top level in google-genai (7235768, #4461) — @Yesudeep Mangalapilly
- **py/plugins**: fix wheel build duplicate files in PEP 420 namespace packages (0c396b6, #4441) — @Yesudeep Mangalapilly

### Refactoring

- **py/samples**: standardize naming taxonomy, consolidate shared logic, and close feature coverage gaps (1996c7c, #4488) — @Yesudeep Mangalapilly
- **py**: consolidate msfoundry and azure plugins into microsoft-foundry (554cd71, #4450) — @Yesudeep Mangalapilly
- **py**: rename aws-bedrock plugin to amazon-bedrock (8acd6b0, #4448) — @Yesudeep Mangalapilly

All notable changes to `genkit-plugin-google-genai` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

- See the [workspace CHANGELOG](../../CHANGELOG.md) for a comprehensive list of changes.

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.5.0
