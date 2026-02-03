# Changelog

All notable changes to the genkit testapps will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **genkit-ui library**: Shared Angular component library (`@genkit-ai/genkit-ui`)
  - ChatBoxComponent - Complete chat interface
  - MessageListComponent - Message display with markdown
  - WelcomeScreenComponent - Animated greeting carousel
  - ChatInputComponent - Input with attachments and voice
  - ModelSelectorComponent - Searchable model dropdown
  - PromptQueueComponent - Queue with drag-and-drop
  - ThemeSelectorComponent - Dark/light/system theme toggle
  - LanguageSelectorComponent - i18n language picker

- **Testing infrastructure**
  - Vitest configuration with 11% coverage (target: 80%)
  - Pure utility functions extracted for testability
  - 322 passing tests across 16 test files

- **Production tooling**
  - Biome for linting and formatting
  - License-checker for dependency license verification
  - GitHub Actions CI workflow with lint, test, security, and build jobs

- **Utility modules** (`app/core/utils/`)
  - `chat.utils.ts` - Queue operations, message creation
  - `model.utils.ts` - Model filtering, searching, grouping
  - `markdown.utils.ts` - Math symbol substitution, HTML escaping
  - `theme.utils.ts` - Dark mode logic, localStorage
  - `preferences.utils.ts` - Preferences management, storage

### Changed
- Refactored services to use pure utility functions for better testability
- Updated Storybook to v10.x for Angular 21 compatibility

### Fixed
- Type exports using `export type` for `isolatedModules` compatibility
- SpeechRecognition type declarations for Web Speech API

## [0.0.1] - 2025-02-03

### Added
- Initial genkit-chat demo application
- Angular 21 frontend with Material Design
- Python FastAPI backend with Genkit integration
- Multi-provider model support (Google AI, Anthropic, OpenAI, Ollama)
- Real-time streaming responses via SSE
- Content safety with TensorFlow.js toxicity detection
- Internationalization with 9 languages including RTL support
- Voice input via Web Speech API
