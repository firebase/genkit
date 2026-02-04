# Changelog

All notable changes to the Genkit Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-02-04

This is a major release with **178 commits** and **680 files changed** over **8 months**
since 0.4.0 (May 2025), representing the most significant update to the Genkit Python SDK to date.

### Impact Summary

| Category | Impact Level | Description |
|----------|-------------|-------------|
| **New Plugins** | 🟢 High | 7 new model providers and 3 new telemetry plugins |
| **Core Features** | 🟢 High | DAP, rerankers, background models, Dotprompt integration |
| **Type Safety** | 🟡 Medium | Comprehensive type checking with ty/pyrefly/pyright |
| **Breaking Changes** | 🟡 Medium | PluginV2 refactor requires migration |
| **Developer Experience** | 🟢 High | Hot reloading, improved samples, better docs |
| **Security** | 🟢 High | Ruff audit, PySentry scanning, SigV4 signing |
| **Performance** | 🟢 High | Per-event-loop HTTP caching, release pipeline 15x faster |

### Added

#### New Model Provider Plugins
- **`genkit-plugin-anthropic`**: Full Anthropic Claude model support (#3919)
- **`genkit-plugin-aws-bedrock`**: AWS Bedrock integration for Claude, Titan, Llama models (#4389)
- **`genkit-plugin-msfoundry`**: Azure OpenAI (Microsoft Foundry) support (#4383)
- **`genkit-plugin-cf-ai`**: Cloudflare Workers AI models (#4405)
- **`genkit-plugin-deepseek`**: DeepSeek models with structured output (#4051)
- **`genkit-plugin-xai`**: xAI (Grok) models with plugin config (#4001, #4289)
- **`genkit-plugin-mistral`**: Mistral AI models (Large, Small, Codestral, Pixtral) (#4406)
- **`genkit-plugin-huggingface`**: Hugging Face Inference API with 17+ providers (#4406)

#### New Telemetry Plugins
- **`genkit-plugin-aws`**: AWS X-Ray telemetry with SigV4 signing (#4390, #4402)
- **`genkit-plugin-aim`**: AIM telemetry for Firebase observability (#4386, #3826)
- **`genkit-plugin-google-cloud`**: GCP telemetry parity with JS/Go implementations (#4281)

#### Core Framework Features
- **Dynamic Action Provider (DAP)**: Factory pattern for runtime action creation (#4377)
- **Rerankers**: Initial reranker implementation for RAG pipelines (#4065)
- **Background Models**: Dynamic model discovery and background action support (#4327)
- **Resource Support**: Full resource management with MCP integration (#4204, #4048)
- **Evaluator Metrics**: ANSWER_RELEVANCY, FAITHFULNESS, MALICIOUSNESS metrics (#3806)
- **MCP Plugin**: Model Context Protocol integration with tests (#4054)
- **Retriever/Embedder References**: Reference support matching JS SDK (#3922, #3936)
- **Output Formats**: Array, enum, and JSONL formats for JS parity (#4230)
- **Pydantic Output**: Return Pydantic instances when output schema passed (#4413)

#### Dotprompt Integration (via [google/dotprompt](https://github.com/google/dotprompt))
- **Dotpromptz 0.1.5**: Upgraded to latest version with type-safe schema fields
- **Python 3.14 Support**: PyO3/maturin ABI compatibility for Rust-based Handlebars engine
- **Directory/File Prompt Loading**: Automatic prompt discovery matching JS SDK (#3955, #3971)
- **Handlebars Partials**: `define_partial` for template reuse (#4088)
- **Render System Prompts**: `render_system_prompt` and `render_user_prompt` methods (#3503, #3705)
- **Callable Support**: Prompts can now be used as callables (#4053)
- **Cycle Detection**: Partial resolution with cycle detection prevents infinite recursion
- **Path Traversal Hardening**: Security fix for CWE-22 vulnerability
- **Helper Parity**: Consistent Handlebars helper behavior across all runtimes
- **Release Pipeline**: Automated PyPI publishing, release time reduced from 30 min to 2 min

#### Developer Experience
- **Hot Reloading**: [Watchdog](https://github.com/gorakhargosh/watchdog)-based autoreloading for all samples (#4268)
- **Security Scanning**: PySentry-rs integration in hooks and CI (#4273)
- **TODO Linting**: Automated issue creation for TODO comments (#4376)
- **Centralized Action Latency**: Built-in performance tracking (#4267)
- **Sample Improvements**: Preamble scripts, browser auto-open, rich tracebacks (#4375, #4373)
- **Release Automation**: `bin/release_check`, `bin/bump_version` scripts
- **Consistency Checks**: `bin/check_consistency` for package validation

#### Type Safety Improvements
- **ty Integration**: Stricter, faster type checking from Astral (#4094)
- **pyrefly Integration**: Meta's type checker for additional coverage (#4316)
- **pyright Enforcement**: Full Microsoft type checking (#4310)
- **Comprehensive Fixes**: Zero type errors across all packages (#4249-4260, #4270)

#### Documentation
- **Module Docstrings**: Terminology tables and ASCII data flow diagrams (#4322)
- **GEMINI.md Updates**: Test file naming, import guidelines, TODO format (#4381, #4393, #4397)
- **Sample Documentation**: Testing notes for all samples (#4294)
- **HTTP Client Guidelines**: Event loop binding best practices (#4430)
- **Roadmap**: Plugin API conformance analysis (#4431)

#### Samples & Demos
- **New Samples**: tool-interrupt, short-n-long, media-models-demo, prompt samples
- **Run Script Standardization**: Central script for running samples with `genkit start`
- **Rich Tracebacks**: Improved error output in samples

### Changed

#### Breaking Changes
- **PluginV2 Refactor**: Major plugin architecture update - existing plugins may need migration (#4132)
  - Plugins now use a standardized registration pattern
  - Configuration options are more consistent across plugins
- **Async-First Architecture**: Removed sync base, fully async by default (#4244)
- **Embed API**: Refactored `embed/embed_many` for JS parity (#4269)

#### Improvements
- **Python 3.14 Support**: Full compatibility with Python 3.14 (#3947)
- **Gemini 2.5/3.0 Upgrade**: Default models updated to Gemini 2.5/3.0 (#3771, #4277)
- **Dotpromptz 0.1.5**: Latest template engine with improved features (#4324)
- **PEP 8 Compliance**: All in-function imports moved to top-level (#4396-4400)
- **CI Consolidation**: Single workflow, every commit is release-worthy (#4410)
- **Reflection API**: Improved multi-runtime handling and health checks
- **Dev UI Defaults**: Better default configurations

### Fixed

#### Critical Fixes
- **Race Condition**: Dev server startup race condition resolved (#4225)
- **Thread Safety**: Per-event-loop HTTP client caching prevents event loop binding errors (#4419, #4429)
- **Infinite Recursion**: Cycle detection in Handlebars partial resolution (via Dotprompt)
- **Real-Time Telemetry**: Trace ID formatting and streaming fixes (#4285)
- **Structured Output**: DeepSeek model structured output generation (#4374)
- **JSON Schema**: None type handling per JSON Schema spec (#4247)
- **Windows Support**: File-safe timestamp format for runtime files (#3727)

#### Model/Plugin Fixes
- **Gemini Models**: Various bug fixes (#4432)
- **TTS/Veo Models**: System prompt support in model config (#4411)
- **Google GenAI**: Model config and README updates (#4306, #4323)
- **Ollama**: Sample fixes and model server management (#4133, #4227)
- **Embedders**: Reflection health check fixes (#3969)
- **Complex Schemas**: Support for complex schemas in Gemini (#3049)

#### Sample Fixes
- Extensive sample fixes across all demos (#4122-4418)
- System prompt fields added to all Gemini samples (#4391)
- Missing dependencies resolved (#4282)
- Consistent `genkit start` usage (#4226)
- GCloud auto-setup for Vertex AI samples (#4427)

#### Type Errors
- Resolved all `ty`, `pyrefly`, and `pyright` type errors
- Re-enabled disabled tests and improved coverage
- Fixed evaluator plugin imports and StrEnum compatibility

### Security

- **Ruff Security Audit**: Addressed all security and code quality warnings (#4409)
- **SigV4 Signing**: AWS X-Ray OTLP exporter now uses proper AWS signatures (#4402)
- **Path Traversal Hardening**: CWE-22 vulnerability fix in Dotprompt (via google/dotprompt)
- **License Compliance**: Fixed license headers in all configuration files (#3930)
- **PySentry Integration**: Continuous security vulnerability scanning (#4273)

### Performance

- **Per-Event-Loop HTTP Client Caching**: Reuses HTTP connections within event loops, prevents connection overhead
- **Dotprompt Release Pipeline**: Reduced from 30 minutes to 2 minutes (15x faster)
- **CI Consolidation**: Single workflow, every commit is release-worthy (#4410)
- **ty Type Checker**: Faster type checking than pyright alone (#4094)

### Deprecated

- Sync API base classes are removed in favor of async-first architecture

---

## [0.4.0] - 2025-05-26

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

## [0.3.0] - 2025-04-08

### Added

- Initial public release of Genkit Python SDK
- Core framework (`genkit`)
- Model plugins: Anthropic, Google GenAI, Ollama, Vertex AI, xAI, DeepSeek
- Telemetry plugins: AWS, Google Cloud, Firebase
- Utility plugins: Flask, MCP, Evaluators, Dev Local Vectorstore

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/compare/genkit-python@0.4.0...genkit-python@0.5.0
[0.4.0]: https://github.com/firebase/genkit/compare/genkit-python@0.3.0...genkit-python@0.4.0
[0.3.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.3.0
