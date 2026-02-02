# Changelog

All notable changes to the Genkit Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New telemetry plugins: Azure, Cloudflare (CF), Observability (Sentry, Honeycomb, Datadog, Grafana, Axiom)
- New model provider plugins: Mistral AI, Hugging Face
- Comprehensive release automation scripts (`bin/release_check`, `bin/bump_version`)
- Automated consistency checks (`bin/check_consistency`)
- Package metadata improvements (keywords, project URLs)

### Changed
- Synchronized all plugin versions to match core framework version
- Improved type checking coverage across all packages

### Fixed
- Sample naming consistency (directory names now match package names)
- Python version compatibility for CI (3.10, 3.11, 3.12, 3.13, 3.14)

## [0.4.0] - 2026-02-02

### Added
- **Telemetry Plugins**
  - `genkit-plugin-azure`: Azure Application Insights integration
  - `genkit-plugin-cf`: Generic OTLP export for Cloudflare and other backends
  - `genkit-plugin-observability`: Unified presets for Sentry, Honeycomb, Datadog, Grafana Cloud, Axiom

- **Model Provider Plugins**
  - `genkit-plugin-mistral`: Mistral AI models (Large, Small, Codestral, Pixtral)
  - `genkit-plugin-huggingface`: Hugging Face Inference API with 17+ inference providers

- **Core Framework**
  - Improved tracing and observability support
  - Enhanced type safety across all modules

### Changed
- All plugins now share the same version number as the core framework
- Improved documentation and README files for all packages

## [0.3.0] - 2025-12-15

### Added
- Initial public release of Genkit Python SDK
- Core framework (`genkit`)
- Model plugins: Anthropic, Google GenAI, Ollama, Vertex AI, xAI, DeepSeek
- Telemetry plugins: AWS, Google Cloud, Firebase
- Utility plugins: Flask, MCP, Evaluators, Dev Local Vectorstore

[Unreleased]: https://github.com/firebase/genkit/compare/py-v0.4.0...HEAD
[0.4.0]: https://github.com/firebase/genkit/compare/py-v0.3.0...py-v0.4.0
[0.3.0]: https://github.com/firebase/genkit/releases/tag/py-v0.3.0
