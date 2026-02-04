# Release: Genkit Python SDK v0.5.0

## Overview

This is a **major release** of the Genkit Python SDK with **178 commits** and **680 files changed** over **8 months** since v0.4.0 (May 2025). This release represents the most significant update to the Python SDK to date, adding extensive new model providers, telemetry integrations, core framework features, and substantial improvements to type safety and developer experience.

## Impact Summary

| Category | Impact | Migration Required |
|----------|--------|-------------------|
| **New Model Plugins** | 🟢 High - 7 new providers | No (additive) |
| **New Telemetry Plugins** | 🟢 High - 3 new providers | No (additive) |
| **Core Features** | 🟢 High - rerankers, Dotprompt, tool calling | No (additive) |
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
| `genkit-plugin-amazon-bedrock` | AWS Bedrock | Claude, Titan, Llama via AWS |
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
| `genkit-plugin-observability` | Third-party | Sentry, Honeycomb, Datadog |
| `genkit-plugin-google-cloud` | GCP | Full parity with JS/Go SDKs |

### Core Framework Features

- **Agentive Tool Calling**: Define tools with `@ai.tool()` decorator for AI agents
- **Rerankers**: Initial reranker implementation for RAG pipelines
- **Background Models**: Dynamic model discovery and background action support
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

This release includes contributions from **13 developers** across **188 PRs**. Thank you to everyone who contributed!

| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| [**@yesudeep**](https://github.com/yesudeep) | 91 | 93 | **Core**: async-first architecture (#4244), Genkit class methods (#4274), embed/embed_many API refactor (#4269), centralized action latency (#4267), array/enum/jsonl output formats (#4230). **Plugins**: AWS Bedrock (#4389), AWS X-Ray with SigV4 (#4390, #4402), Azure OpenAI (#4383), Cloudflare Workers AI (#4405), Mistral AI (#4406), Hugging Face (#4406), GCP telemetry (#4281). **Type Safety**: ty integration (#4094), pyrefly (#4316), pyright (#4310), comprehensive fixes (#4249-4270). **DevEx**: hot reloading (#4268), per-event-loop HTTP caching (#4419, #4429), PySentry security (#4273), TODO linting (#4376), CI consolidation (#4410), session/chat API (#4278, #4275), background models (#4327), docs (#4322, #4393, #4430). **Samples**: 20+ sample fixes and improvements (#4283, #4373, #4375, #4427). |
| [**@MengqinShen**](https://github.com/MengqinShen) (Elisa Shen) | 42 | 42 | **Core**: Resource support implementation (#4204). **Samples**: menu sample fixes (#4239, #4403), short-n-long (#4404), tool-interrupt (#4408), prompt sample (#4223, #4183), ollama-hello (#4133), genai-image (#4122, #4234), code-execution (#4134), anthropic sample (#4131). **Models**: Google GenAI model config (#4306), TTS/Veo model config (#4411), Gemini bug fixes (#4432), system prompt fields (#4391, #4418). **Docs**: README updates (#4323), multi-round flow logic (#4137). |
| [**@AbeJLazaro**](https://github.com/AbeJLazaro) | 11 | 8 | **Plugins**: Model Garden resolve/list actions (#3040), Ollama resolve action (#2972), type coverage and tests (#3011). **Fixes**: Gemini complex schema support (#3049), Firestore plugin naming (#3085), evaluator plugin requirements (#3166), optional dependencies setup (#3012). **Tests**: Model Garden tests (#3083). |
| [**@pavelgj**](https://github.com/pavelgj) | 10 | 7 | **Core**: Reflection API multi-runtime support (#3970), health check fixes (#3969). **Fixes**: Embedders reflection (#3969), Gemini version upgrades to 2.5 (#3909). |
| [**@zarinn3pal**](https://github.com/zarinn3pal) | 9 | 9 | **Plugins**: Anthropic (#3919), DeepSeek (#4051, structured output fix #4374), xAI/Grok (#4001, config #4289), ModelGarden (#2568). **Telemetry**: GCP telemetry for Firebase observability (#3826, #4386). **Samples**: OpenAI Compat tools (#3684). |
| [**@huangjeff5**](https://github.com/huangjeff5) | 7 | 7 | **Core**: PluginV2 refactor with new registration pattern (#4132), type safety improvements (#4310), Pydantic output instances (#4413), session/chat refactor (#4321). **Telemetry**: Real-time telemetry and trace ID formatting (#4285). |
| [**@hendrixmar**](https://github.com/hendrixmar) | 7 | 7 | **Evaluators**: ANSWER_RELEVANCY, FAITHFULNESS, MALICIOUSNESS metrics (#3806), ModelReference support (#3949, #3951). **Plugins**: OpenAI compat list_actions (#3240), resolve_method (#3055). **Dotprompt**: render_system_prompt (#3503), render_user_prompt (#3705). |
| [**@ssbushi**](https://github.com/ssbushi) | 6 | 2 | **Evaluators**: Simple evaluators plugin (#2835). **Docs**: MkDocs API reference updates (#2852), genkit-tools model optional (#3918). |
| [**@shrutip90**](https://github.com/shrutip90) | 1 | 1 | **Types**: ResourcePartSchema exports via genkit-tools (#3239). |
| [**@schlich**](https://github.com/schlich) | 1 | 1 | **Types**: Type annotations for ai module. |
| [**@ktsmadhav**](https://github.com/ktsmadhav) | 1 | 1 | **Fixes**: Windows support with file-safe timestamp format (#3727). |
| [**@junhyukhan**](https://github.com/junhyukhan) | 1 | 1 | **Docs**: Typo fixes. |
| [**@CorieW**](https://github.com/CorieW) | 1 | 1 | Community contribution. |

**[google/dotprompt](https://github.com/google/dotprompt) Contributors** (Dotprompt Python integration):

| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| [**@yesudeep**](https://github.com/yesudeep) | 50+ | 100+ | **Rust Engine**: dotpromptz-handlebars with PyO3/maturin (#365), Python 3.14 ABI support, Rust Handlebars runtime. **Features**: Cycle detection in partial resolution, path traversal hardening (CWE-22), directory/file prompt loading (#3955, #3971), Handlebars partials (#4088), callable prompts (#4053). **Build**: Bazel rules_dart/rules_flutter, release pipeline 15x faster (30min→2min), maturin wheel builds. **IDE**: Monaco syntax highlighting, CodeMirror 6 integration, Storybook demos. **Polyglot**: Python, Go, Dart, Rust, TypeScript implementations. |
| [**@MengqinShen**](https://github.com/MengqinShen) | 42 | 45 | **CI/CD**: GitHub Actions workflows for Python package publishing, automated release-please, dotpromptz PyPI releases (0.1.2-0.1.5), handlebarrz releases, wheel artifact management. |
| [**@Zereker**](https://github.com/Zereker) | 1 | 1 | **Go**: Closure fix preventing template sharing between instances. |

## Full Changelog

See [CHANGELOG.md](py/CHANGELOG.md) for the complete list of changes.
