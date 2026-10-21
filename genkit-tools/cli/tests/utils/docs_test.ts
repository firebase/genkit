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
 */

import { describe, expect, it } from '@jest/globals';
import {
  Doc,
  normalizeDoc,
  resolveDocField,
  searchDocs,
} from '../../src/utils/docs';

describe('docs utils', () => {
  describe('resolveDocField', () => {
    it('returns plain strings directly', () => {
      expect(resolveDocField('Plain description', 'js')).toBe(
        'Plain description'
      );
    });

    it('resolves language-specific entry from a localized object map', () => {
      const localized = {
        default: 'Build an Angular app powered by Genkit.',
        js: 'Add Genkit to an Angular app with SSR server routes.',
        go: 'Connect an Angular UI to your Genkit Go backend.',
      };
      expect(resolveDocField(localized, 'js')).toBe(
        'Add Genkit to an Angular app with SSR server routes.'
      );
      expect(resolveDocField(localized, 'go')).toBe(
        'Connect an Angular UI to your Genkit Go backend.'
      );
    });

    it('falls back to default or first string when language key is missing', () => {
      expect(
        resolveDocField(
          { default: 'Default summary', js: 'JS summary' },
          'rust'
        )
      ).toBe('Default summary');
      expect(resolveDocField({ py: 'Python summary' }, 'rust')).toBe(
        'Python summary'
      );
      expect(resolveDocField(undefined, 'js')).toBe('');
      expect(resolveDocField(null, 'js')).toBe('');
    });
  });

  describe('normalizeDoc & searchDocs', () => {
    const sampleDocs: Record<string, Doc> = {
      'js/app-frameworks/angular.md': {
        title: 'Angular',
        description: {
          default: 'Build an Angular app powered by Genkit.',
          js: 'Add Genkit to an Angular app with SSR server routes.',
          go: 'Connect an Angular UI to your Genkit Go backend.',
        } as unknown as string,
        text: '# Angular guide',
        lang: 'js',
        headers: 'Setup\nServer Routes',
      },
      'go/app-frameworks/angular.md': {
        title: 'Angular',
        description: {
          default: 'Build an Angular app powered by Genkit.',
          js: 'Add Genkit to an Angular app with SSR server routes.',
          go: 'Connect an Angular UI to your Genkit Go backend.',
        } as unknown as string,
        text: '# Go Angular guide',
        lang: 'go',
        headers: 'Setup\nGo Backend',
      },
      'js/flows.md': {
        title: 'Defining Flows',
        description: 'Learn how to define and run Genkit flows.',
        text: '# Flows',
        lang: 'js',
        headers: 'Basic Flows\nStreaming',
      },
    };

    it('normalizes language-keyed description objects into strings', () => {
      const normalized = normalizeDoc(
        sampleDocs['js/app-frameworks/angular.md'],
        'js'
      );
      expect(normalized.description).toBe(
        'Add Genkit to an Angular app with SSR server routes.'
      );
    });

    it('searches across normalized docs with object descriptions without throwing', () => {
      const normalizedDocs = Object.fromEntries(
        Object.entries(sampleDocs).map(([file, doc]) => [
          file,
          normalizeDoc(doc, file.split('/')[0]),
        ])
      );
      const jsResults = searchDocs(normalizedDocs, 'SSR', 'js');
      expect(jsResults).toHaveLength(1);
      expect(jsResults[0].file).toBe('js/app-frameworks/angular.md');
      expect(jsResults[0].doc.description).toBe(
        'Add Genkit to an Angular app with SSR server routes.'
      );

      const goResults = searchDocs(normalizedDocs, 'backend', 'go');
      expect(goResults).toHaveLength(1);
      expect(goResults[0].file).toBe('go/app-frameworks/angular.md');
      expect(goResults[0].doc.description).toBe(
        'Connect an Angular UI to your Genkit Go backend.'
      );
    });
  });
});
