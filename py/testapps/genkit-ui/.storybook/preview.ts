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

import type { Preview } from '@storybook/angular';
import { applicationConfig } from '@storybook/angular';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { importProvidersFrom, APP_INITIALIZER } from '@angular/core';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

// Apply global styles for Storybook
import '../src/theme/styles.css';

// Mock translations for standalone library Storybook
const TRANSLATIONS: Record<string, Record<string, unknown>> = {
    en: {
        chat: {
            placeholder: 'Ask Genkit Chat',
            sendMessage: 'Send message',
            voiceInput: 'Voice input',
            stopRecording: 'Stop recording',
            addFiles: 'Add files',
            greeting: 'Hello',
        },
        toolbar: {
            settings: 'Settings',
            tools: 'Tools',
            stream: 'Streaming responses',
            markdown: 'Render markdown',
            safe: 'Content safety',
        },
        actions: {
            copy: 'Copy to clipboard',
            readAloud: 'Read aloud',
            goodResponse: 'Good response',
            badResponse: 'Bad response',
            more: 'More',
        },
        theme: {
            label: 'Theme',
            system: 'System',
            light: 'Light',
            dark: 'Dark',
        },
    },
};

// Custom translation loader for Storybook
class MockTranslateLoader extends TranslateLoader {
    override getTranslation(lang: string): Observable<Record<string, unknown>> {
        return of(TRANSLATIONS[lang] || TRANSLATIONS['en']);
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
                { name: 'light', value: '#fafafa' },
                { name: 'dark', value: '#1a1c1e' },
            ],
        },
    },
    initialGlobals: {
        backgrounds: {
            value: 'light',
        },
    },
};

export default preview;
