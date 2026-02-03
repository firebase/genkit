# Changelog

All notable changes to the Genkit Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-02-03

### Added

#### New Plugins

* **AWS Bedrock Plugin** (`genkit-plugin-aws-bedrock`): Support for AWS Bedrock models
* **AWS Telemetry Plugin** (`genkit-plugin-aws`): AWS X-Ray OTLP exporter with SigV4 signing
* **Azure OpenAI Plugin** (`genkit-plugin-msfoundry`): Microsoft Azure OpenAI integration
* **Cloudflare Workers AI Plugin** (`genkit-plugin-cf-ai`): Cloudflare Workers AI models
* **DeepSeek Plugin** (`genkit-plugin-deepseek`): DeepSeek model provider
* **xAI Plugin** (`genkit-plugin-xai`): xAI/Grok model support with plugin config
* **Anthropic Plugin** (`genkit-plugin-anthropic`): Full Anthropic Claude model support
* **MCP Plugin** (`genkit-plugin-mcp`): Model Context Protocol integration
* **Evaluator Metrics Plugin**: ANSWER\_RELEVANCY, FAITHFULNESS, MALICIOUSNESS metrics
* **AIM Telemetry**: Firebase and observability metrics support

#### Core Framework Features

* **DAP (Direct Action Protocol)**: New protocol for direct action invocation
* **Session Management**: `ai.chat()` API with session support and Streamlit demos
* **Background Model Support**: Dynamic model discovery and background actions
* **Reranker Support**: Initial implementation of reranker functionality
* **Resource Support**: `define_resource` for MCP plugin integration
* **Prompt Loading**: Directory and file-based prompt loading matching JS SDK
* **Handlebars Partials**: `define_partial` for reusable prompt templates
* **Output Formats**: Array, enum, and JSONL output formats for JS parity
* **Embedder/Retriever References**: Support matching JS SDK patterns
* **ModelReference**: Standardized model reference support
* **Action Latency Tracking**: Centralized performance monitoring

#### Developer Experience

* **Python 3.14 Support**: Full compatibility with Python 3.14
* **Type Safety Improvements**: Integrated `ty` and `pyrefly` type checkers
* **Release Automation**: Comprehensive scripts (`bin/release_check`, `bin/bump_version`)
* **Consistency Checks**: Automated package consistency validation
* **Security Scanning**: `pysentry-rs` integration for security checks
* **Hot Reloading**: Watchdog-based auto-reloading for samples
* **TODO Linting**: Automated issue creation for TODO comments

#### Samples & Documentation

* **New Samples**: tool-interrupt, short-n-long, media-models-demo, chat samples
* **Streamlit Demos**: Interactive session management demonstrations
* **Run Script Standardization**: Central script for running samples with `genkit start`
* **Rich Tracebacks**: Improved error output in samples

### Changed

* **PluginV2 Refactor**: Major plugin architecture improvements
* **Async-First Architecture**: Removed sync base in favor of async-only
* **Pydantic Model Aliasing**: Fixed aliasing issues in models
* **Reflection API**: Improved multi-runtime handling and health checks
* **Dev UI Defaults**: Better default configurations
* **Model Upgrades**: Updated to Gemini 2.5 models across samples
* **Import Cleanup**: PEP 8 compliant in-function import organization
* **CI Consolidation**: Every commit is now release-worthy

### Fixed

* **Race Condition**: Fixed dev server startup race condition
* **Telemetry**: Real-time telemetry and trace ID formatting fixes
* **Windows Support**: File-safe timestamp format for runtime files
* **Structured Output**: Fixed generation for DeepSeek models
* **Image Encoding**: Resolved image encoding issues
* **Media Parts**: Fixed encoded media parts in google-genai responses
* **Schema Handling**: Support for complex schemas in Gemini
* **Type Errors**: Resolved all `ty`, `pyrefly`, and `pyright` type errors
* **Test Coverage**: Re-enabled disabled tests and improved coverage
* **Dependency Issues**: Fixed evaluator plugin imports and StrEnum compatibility
* **Sample Fixes**: Numerous fixes across google-genai, ollama, menu, prompt, and other samples
* **Ruff Security Warnings**: Addressed code quality warnings

### Security

* **Ruff Security Audit**: Fixed all security-related linting warnings
* **License Compliance**: Fixed license headers in all configuration files
* **pyproject.toml**: Resolved license deprecation warnings

## [0.4.0] - 2026-02-02

### Added

* **Telemetry Plugins**
  * `genkit-plugin-azure`: Azure Application Insights integration
  * `genkit-plugin-cf`: Generic OTLP export for Cloudflare and other backends
  * `genkit-plugin-observability`: Unified presets for Sentry, Honeycomb, Datadog, Grafana Cloud, Axiom

* **Model Provider Plugins**
  * `genkit-plugin-mistral`: Mistral AI models (Large, Small, Codestral, Pixtral)
  * `genkit-plugin-huggingface`: Hugging Face Inference API with 17+ inference providers

* **Core Framework**
  * Improved tracing and observability support
  * Enhanced type safety across all modules

### Changed

* All plugins now share the same version number as the core framework
* Improved documentation and README files for all packages

## [0.3.0] - 2025-12-15

### Added

* Initial public release of Genkit Python SDK
* Core framework (`genkit`)
* Model plugins: Anthropic, Google GenAI, Ollama, Vertex AI, xAI, DeepSeek
* Telemetry plugins: AWS, Google Cloud, Firebase
* Utility plugins: Flask, MCP, Evaluators, Dev Local Vectorstore

[Unreleased]: https://github.com/firebase/genkit/compare/py-v0.5.0...HEAD

[0.5.0]: https://github.com/firebase/genkit/compare/genkit-python@0.4.0...py-v0.5.0

[0.4.0]: https://github.com/firebase/genkit/compare/py-v0.3.0...genkit-python@0.4.0

[0.3.0]: https://github.com/firebase/genkit/releases/tag/py-v0.3.0
