# Release: Genkit Python SDK v0.5.0

## Overview

This is a **major release** of the Genkit Python SDK with **178 commits** and **680 files changed** over **8 months** since v0.4.0 (May 2025). This release represents the most significant update to the Python SDK to date, adding extensive new model providers, telemetry integrations, core framework features, and substantial improvements to type safety and developer experience.

## Impact Summary

| Category | Impact | Migration Required |
|----------|--------|-------------------|
| **New Model Plugins** | 🟢 High - 7 new providers | No (additive) |
| **New Telemetry Plugins** | 🟢 High - 3 new providers | No (additive) |
| **Core Features** | 🟢 High - DAP, rerankers, Dotprompt | No (additive) |
| **PluginV2 Refactor** | 🟡 Medium | Yes - plugin authors |
| **Async-First Architecture** | 🟡 Medium | Yes - if using sync APIs |
| **Type Safety** | 🟢 High | No (stricter checks) |
| **Security Enhancements** | 🟢 High | No (automatic) |
| **Python 3.14 Support** | 🟢 High | No (additive) |
| **Performance** | 🟢 High | No (automatic) |

## What's New

### New Model Provider Plugins (7)

| Plugin | Provider | Key Features |
|--------|----------|--------------|
| `genkit-plugin-anthropic` | Anthropic | Claude models (Opus, Sonnet, Haiku) |
| `genkit-plugin-aws-bedrock` | AWS Bedrock | Claude, Titan, Llama via AWS |
| `genkit-plugin-msfoundry` | Azure OpenAI | Microsoft Foundry integration |
| `genkit-plugin-cf-ai` | Cloudflare | Workers AI models |
| `genkit-plugin-deepseek` | DeepSeek | DeepSeek models with structured output |
| `genkit-plugin-xai` | xAI | Grok models |
| `genkit-plugin-mistral` | Mistral AI | Large, Small, Codestral, Pixtral |
| `genkit-plugin-huggingface` | Hugging Face | 17+ inference providers |

### New Telemetry Plugins (3)

| Plugin | Provider | Key Features |
|--------|----------|--------------|
| `genkit-plugin-aws` | AWS X-Ray | SigV4 signing, OTLP export |
| `genkit-plugin-aim` | AIM/Firebase | Firebase observability integration |
| `genkit-plugin-google-cloud` | GCP | Full parity with JS/Go SDKs |

### Core Framework Features

- **Dynamic Action Provider (DAP)**: Factory pattern for runtime action creation
- **Rerankers**: Initial reranker implementation for RAG pipelines
- **Background Models**: Dynamic model discovery and background action support
- **Resource Support**: Full MCP resource management
- **Evaluator Metrics**: ANSWER_RELEVANCY, FAITHFULNESS, MALICIOUSNESS
- **Output Formats**: Array, enum, JSONL formats (JS SDK parity)
- **Pydantic Output**: Return typed Pydantic instances from generation

### Dotprompt Integration (via [google/dotprompt](https://github.com/google/dotprompt))

- **Dotpromptz 0.1.5**: Latest version with type-safe schema fields
- **Python 3.14 Support**: PyO3/maturin ABI compatibility for Rust-based Handlebars engine
- **Directory/File Prompt Loading**: Automatic prompt discovery matching JS SDK
- **Handlebars Partials**: `define_partial` for template reuse
- **Render Methods**: `render_system_prompt` and `render_user_prompt`
- **Callable Support**: Prompts can be used directly as callables
- **Security**: Cycle detection prevents infinite recursion, path traversal hardening (CWE-22)
- **Helper Parity**: Consistent Handlebars helper behavior across all runtimes
- **Release Pipeline**: Automated PyPI publishing, release time reduced from 30 min to 2 min

## Breaking Changes

### 1. PluginV2 Refactor (#4132)

**Impact**: Plugin authors need to update their plugins.

**Before**:
```python
class MyPlugin(Plugin):
    def __init__(self, config):
        self.config = config
```

**After**:
```python
class MyPlugin(PluginV2):
    def __init__(self, config):
        super().__init__(config)
        # Use standardized registration pattern
```

### 2. Async-First Architecture (#4244)

**Impact**: Sync base classes removed. All operations are now async.

**Before**:
```python
result = flow.run_sync(input)  # No longer available
```

**After**:
```python
result = await flow.run(input)  # Use async/await
# Or use asyncio.run() at entry points
```

### 3. Embed API Refactor (#4269)

**Impact**: `embed/embed_many` API updated for JS parity.

**Before**:
```python
# Old API signature
```

**After**:
```python
# New API matches JS SDK patterns
```

## Type Safety Improvements

This release integrates **three type checkers** for comprehensive coverage:

- **ty** (Astral/Ruff): Fast, strict checking - 0 errors
- **pyrefly** (Meta): Additional coverage - 0 errors  
- **pyright** (Microsoft): Industry standard - 0 errors

All packages now pass all three type checkers with zero errors.

## Security Enhancements

- **Ruff Security Audit**: All S-rules (Bandit) warnings addressed
- **SigV4 Signing**: AWS X-Ray exporter uses proper AWS authentication
- **Path Traversal Hardening**: CWE-22 vulnerability fix in Dotprompt
- **PySentry Integration**: Continuous vulnerability scanning in CI
- **License Compliance**: All configuration files have proper headers

## Critical Fixes

- **Race Condition**: Dev server startup race condition resolved (#4225)
- **Thread Safety**: Per-event-loop HTTP client caching prevents event loop binding errors (#4419, #4429)
- **Infinite Recursion**: Cycle detection in Handlebars partial resolution (via Dotprompt)
- **Structured Output**: DeepSeek model structured output generation (#4374)
- **JSON Schema**: None type handling per JSON Schema spec (#4247)

## Performance

- **Per-Event-Loop HTTP Client Caching**: Reuses HTTP connections within event loops, prevents connection overhead
- **Dotprompt Release Pipeline**: Reduced from 30 minutes to 2 minutes (15x faster)
- **CI Consolidation**: Single workflow, every commit is release-worthy
- **ty Type Checker**: Faster type checking than pyright alone

## Developer Experience

- **Hot Reloading**: [Watchdog](https://github.com/gorakhargosh/watchdog)-based autoreloading for all samples
- **Sample Improvements**: Consistent run scripts, browser auto-open, rich tracebacks
- **TODO Linting**: Automated GitHub issue creation for TODOs
- **Release Automation**: `bin/release_check`, `bin/bump_version` scripts
- **Consistency Checks**: `bin/check_consistency` validates all packages

## Migration Guide

### For Application Developers

1. **Update imports** if you were using internal APIs
2. **Use async/await** for all Genkit operations
3. **Test with Python 3.10+** (3.14 now supported)

### For Plugin Developers

1. **Migrate to PluginV2** base class
2. **Follow new registration pattern** in plugin docs
3. **Run `bin/lint`** to verify type safety

## Testing

All 22 plugins and 40+ samples have been tested. CI runs on Python 3.10, 3.11, 3.12, 3.13, and 3.14.

## Contributors

This release includes contributions from **17 developers** across **191 PRs**. Thank you to everyone who contributed!

| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| **Yesudeep Mangalapilly** | 91 | 93 | Core framework, type safety (ty/pyrefly/pyright), AWS/Azure/Cloudflare plugins, CI/CD, security |
| **Elisa Shen** | 42 | 42 | Resource support, sample fixes, model config updates, prompt samples |
| **Abraham J. Lázaro** | 11 | 8 | Model Garden plugin, Ollama improvements, Gemini schema support |
| **Pavel Jbanov** | 10 | 7 | Reflection API, embedders, background actions, Gemini upgrades |
| **Niraj Nepal** | 9 | 9 | Anthropic plugin, DeepSeek plugin, xAI plugin, AIM telemetry, ModelGarden |
| **huangjeff5** | 7 | 7 | PluginV2 refactor, type safety, Pydantic output, real-time telemetry |
| **Hendrik Martina** | 7 | 7 | Evaluator metrics, OpenAI compat plugin, Dotprompt render methods |
| **ssbushi** | 6 | 2 | Evaluator plugins with simple evaluators |
| **shrutip90** | 1 | 1 | ResourcePartSchema exports |
| **Ty Schlichenmeyer** | 1 | 1 | Type annotations |
| **Sahdev Garg** | 1 | 1 | Go SDK background action support |
| **Michael Doyle** | 1 | 1 | PNPM build scripts |
| **Marcel Folaron** | 1 | 1 | Named generates feature |
| **Madhav** | 1 | 1 | Windows support (file-safe timestamps) |
| **Junhyuk Han** | 1 | 1 | Typo fixes |
| **CorieW** | 1 | - | Community contribution |

**[google/dotprompt](https://github.com/google/dotprompt) Contributors** (Dotprompt integration):

| Contributor | PRs | Key Contributions |
|-------------|-----|-------------------|
| **MengqinShen** | 42 | CI/CD pipeline improvements, package publishing, release automation |
| **Zereker** | 1 | Go closure fix preventing template sharing |

## Full Changelog

See [CHANGELOG.md](py/CHANGELOG.md) for the complete list of changes.
