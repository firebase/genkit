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

import { provideHttpClient, withFetch } from '@angular/common/http';
import { APP_INITIALIZER, importProvidersFrom } from '@angular/core';
import { provideAnimations } from '@angular/platform-browser/animations';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import type { Preview } from '@storybook/angular';
import { applicationConfig } from '@storybook/angular';
import { type Observable, of } from 'rxjs';

// Complete mock translations for Storybook (copied from en.json)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
// biome-ignore lint/suspicious/noExplicitAny: Mock data
const TRANSLATIONS: Record<string, any> = {
  en: {
    app: {
      title: 'Genkit Chat',
      newChat: 'New chat',
      version: 'Preview',
    },
    nav: {
      chat: 'Chat',
      compare: 'Compare',
      settings: 'Settings',
      demoUser: 'Demo User',
    },
    chat: {
      placeholder: 'Ask Genkit Chat',
      sendMessage: 'Send message',
      voiceInput: 'Voice input',
      stopRecording: 'Stop recording',
      addFiles: 'Add files',
      addMoreFiles: 'Add more files',
      uploadFiles: 'Upload files',
      googleDrive: 'Add from Drive',
      camera: 'Camera',
      removeFile: 'Remove',
      disclaimer: 'Genkit Chat may display inaccurate info. Double-check its responses.',
      greeting: 'Hello',
      greetingSubtitle: 'How can I help you today?',
      clearInput: 'Clear',
    },
    attach: {
      photos: 'Photos',
      audio: 'Audio',
      video: 'Video',
      pdf: 'PDF',
      code: 'Import code',
    },
    toolbar: {
      settings: 'Settings',
      tools: 'Tools',
      stream: 'Streaming responses',
      markdown: 'Render markdown',
      safe: 'Content safety',
      enabled: 'Enabled',
      disabled: 'Disabled',
    },
    settings: {
      clearPreferences: 'Clear preferences',
    },
    actions: {
      copy: 'Copy to clipboard',
      readAloud: 'Read aloud',
      goodResponse: 'Good response',
      badResponse: 'Bad response',
      more: 'More',
      edit: 'Edit',
      delete: 'Delete',
      remove: 'Remove',
      clearAll: 'Clear all',
    },
    queue: {
      queued: 'Queued',
      sendAll: 'Send all',
      clearAll: 'Clear all',
      sendNow: 'Send now',
    },
    model: {
      selectModel: 'Select model',
      searchModels: 'Search models...',
      noModelsFound: 'No models found',
      categories: {
        gemini: 'Gemini',
        claude: 'Claude',
        openai: 'OpenAI',
        ollama: 'Ollama',
        other: 'Other',
      },
    },
    quickActions: {
      createImage: 'Create image',
      writeAnything: 'Write a poem',
      helpMeLearn: 'Help me learn',
      createVideo: 'Create video',
      stayOrganized: 'Stay organized',
    },
    theme: {
      label: 'Theme',
      system: 'System',
      light: 'Light',
      dark: 'Dark',
    },
    language: {
      label: 'Language',
      select: 'Select language',
      searchLanguages: 'Search languages...',
      noLanguagesFound: 'No languages found',
    },
    help: {
      label: 'Help & resources',
      documentation: 'Documentation',
      github: 'GitHub',
    },
    auth: {
      signIn: 'Sign in',
      signOut: 'Sign out',
      account: 'Account',
      connectDrive: 'Connect Google Drive',
    },
    safety: {
      flagged: 'Content flagged',
      warning: 'This content may be harmful',
    },
    errors: {
      fileTooLarge: 'File "{name}" is too large (max {size})',
      maxAttachments: 'Maximum {count} attachments allowed',
      invalidFileType: 'File type not supported',
    },
  },
};

// Custom translation loader for Storybook
class MockTranslateLoader extends TranslateLoader {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // biome-ignore lint/suspicious/noExplicitAny: Library override
  override getTranslation(lang: string): Observable<any> {
    return of(TRANSLATIONS[lang] || TRANSLATIONS.en);
  }
}

// Initialize translations synchronously
function initTranslations(translate: TranslateService) {
  return () => {
    translate.setDefaultLang('en');
    translate.use('en');
    return Promise.resolve();
  };
}

const preview: Preview = {
  decorators: [
    applicationConfig({
      providers: [
        provideAnimations(),
        provideHttpClient(withFetch()),
        importProvidersFrom(
          TranslateModule.forRoot({
            defaultLanguage: 'en',
            loader: {
              provide: TranslateLoader,
              useClass: MockTranslateLoader,
            },
          })
        ),
        {
          provide: APP_INITIALIZER,
          useFactory: initTranslations,
          deps: [TranslateService],
          multi: true,
        },
      ],
    }),
  ],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#ffffff' },
        { name: 'dark', value: '#1a1a2e' },
        { name: 'surface', value: '#f5f5f5' },
      ],
    },
    docs: {
      toc: true,
    },
  },
  tags: ['autodocs'],
};

export default preview;
