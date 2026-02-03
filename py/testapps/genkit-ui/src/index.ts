/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @aspect/genkit-ui
 *
 * Beautiful Angular components for AI-powered applications.
 *
 * Genkit UI provides portable, self-contained components that can be
 * used across multiple applications with minimal setup.
 *
 * Features:
 * - Chat interface components (ChatBox, MessageList, ChatInput, etc.)
 * - Theme utilities (LanguageSelector, ThemeSelector)
 * - CSS variable fallback pattern for portability
 * - Full i18n and RTL support
 * - Voice input/output via Web Speech API
 * - Markdown rendering with syntax highlighting
 *
 * Usage::
 *
 *     import { ChatBoxComponent } from '@aspect/genkit-ui/chat';
 *     import { ThemeSelectorComponent } from '@aspect/genkit-ui/theme';
 *
 * @packageDocumentation
 */

// Re-export all modules
export * from './chat';
export * from './theme';
