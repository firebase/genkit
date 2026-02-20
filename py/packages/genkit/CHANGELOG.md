# Changelog

## 0.6.0 (2026-02-17)

### Features

- **py**: support api_key in generation config (6a1c7f1, #4552) — @huangjeff5
- **py**: pass span_id in on_trace_start and set X-Genkit-Span-Id header (ac23a14, #4511) — @Yesudeep Mangalapilly
- **py/genkit**: complete DAP integration with registry (c541f48, #4459) — @Yesudeep Mangalapilly

### Bug Fixes

- Path fix for logging (ae654d8, #4642) — @Niraj Nepal
- **py/core**: redact data URIs in generate debug logs (1cd9c7b, #4609) — @Yesudeep Mangalapilly
- **genkit**: add framework classifiers, Changelog URL, pin pillow>=12.1.1 (15871a3, #4584) — @Yesudeep Mangalapilly
- **py/ai**: pass input.default from dotprompt to DevUI reflection API (d30c89a, #4538) — @Yesudeep Mangalapilly
- **py/core**: guard RealtimeSpanProcessor.export() against ConnectionError (d9fb7a1, #4549) — @Yesudeep Mangalapilly
- **genkit**: handle graceful SIGTERM shutdown in dev_runner (f2961f1, #4597) — @Yesudeep Mangalapilly
- **py**: fix Dev UI error handling for invalid api key (726ba70, #4576) — @Elisa Shen
- **py**: fix dotprompt deadlock (148f230, #4567) — @Elisa Shen
- **py/core**: raise GenkitError when arun_raw receives None input but requires validation (82ae707, #4519) — @Yesudeep Mangalapilly
- **py/core**: prevent infinite recursion in create_prompt_from_file() (c3a35f7, #4495) — @Yesudeep Mangalapilly
- **py/core**: add dropped_* property overrides to RedactedSpan (58a43ad, #4494) — @Yesudeep Mangalapilly
- **py/genkit**: add explicit Transfer-Encoding: chunked to standard action response (db54cf5, #4514) — @Yesudeep Mangalapilly
- **py/genkit**: migrate GranianAdapter to embed.Server API (7995962, #4502) — @Yesudeep Mangalapilly
- **py/web**: improve ASGI type compatibility with Protocol-based types (f712988, #4460) — @Yesudeep Mangalapilly
- **py**: fixed broken sample and lint errors of multi-server (2ec87b4, #4434) — @Elisa Shen
- **py/typing**: respect additionalProperties from JSON schema (09fbe22, #4451) — @Yesudeep Mangalapilly
- **py**: Display schemas for file-based prompts in Dev UI (e5471c8, #4435) — @huangjeff5

### Reverts

- dap (9263f2f, #4469) — @Yesudeep Mangalapilly

All notable changes to `genkit` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

- See the [workspace CHANGELOG](../../CHANGELOG.md) for a comprehensive list of changes.

[Unreleased]: https://github.com/firebase/genkit/compare/genkit-python@0.5.0...HEAD
[0.5.0]: https://github.com/firebase/genkit/releases/tag/genkit-python@0.5.0
