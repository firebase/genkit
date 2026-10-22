/**
 * Copyright 2025 Google LLC
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

import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  statSync,
} from 'node:fs';
import { writeFile } from 'node:fs/promises';
import { Readable } from 'node:stream';
import os from 'os';
import path from 'path';
import { version } from './version';

export const DOCS_URL =
  process.env.GENKIT_DOCS_BUNDLE_URL ??
  'https://genkit.dev/docs-bundle-experimental.json';

export const DOCS_BUNDLE_FILE_PATH = path.resolve(
  os.homedir(),
  '.genkit',
  'docs',
  version,
  'bundle.json'
);

export async function maybeDownloadDocsBundle() {
  if (existsSync(DOCS_BUNDLE_FILE_PATH)) {
    const stats = statSync(DOCS_BUNDLE_FILE_PATH);
    const DOCS_TTL = 1000 * 60 * 60 * 24 * 7; // 1 week
    if (Date.now() - stats.mtimeMs < DOCS_TTL) {
      return;
    }
  }
  const response = await fetch(DOCS_URL);
  if (response.status !== 200) {
    throw new Error(
      'Failed to download genkit docs bundle. Try again later or/and report the issue.\n\n' +
        DOCS_URL
    );
  }
  const stream = Readable.fromWeb(response.body as any);

  mkdirSync(path.dirname(DOCS_BUNDLE_FILE_PATH), { recursive: true });

  await writeFile(DOCS_BUNDLE_FILE_PATH + '.pending', stream);
  renameSync(DOCS_BUNDLE_FILE_PATH + '.pending', DOCS_BUNDLE_FILE_PATH);
}

export interface Doc {
  title: string;
  description?: string;
  text: string;
  lang: string;
  headers: string;
}

export function resolveDocField(value: unknown, lang?: string): string {
  if (typeof value === 'string') {
    return value;
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    if (lang && typeof record[lang] === 'string') {
      return record[lang] as string;
    }
    if (typeof record.default === 'string') {
      return record.default;
    }
    const firstString = Object.values(record).find(
      (v): v is string => typeof v === 'string'
    );
    if (firstString !== undefined) {
      return firstString;
    }
  }
  return '';
}

export function normalizeDoc(doc: Doc, fallbackLang?: string): Doc {
  const lang = resolveDocField(doc.lang) || fallbackLang || 'js';
  const description = resolveDocField(doc.description, lang);
  return {
    ...doc,
    lang,
    title: resolveDocField(doc.title, lang),
    description: description || undefined,
    text: resolveDocField(doc.text, lang),
    headers: resolveDocField(doc.headers, lang),
  };
}

export async function loadDocs(): Promise<Record<string, Doc>> {
  await maybeDownloadDocsBundle();
  const rawDocs = JSON.parse(
    readFileSync(DOCS_BUNDLE_FILE_PATH, { encoding: 'utf8' })
  ) as Record<string, Doc>;
  const normalized: Record<string, Doc> = {};
  for (const [file, doc] of Object.entries(rawDocs)) {
    const fallbackLang = file.split('/')[0];
    normalized[file] = normalizeDoc(doc, fallbackLang);
  }
  return normalized;
}

const STOP_WORDS = new Set(['and', 'the', 'for']);

function filterCommonWords(term: string) {
  return term.length > 2 && !STOP_WORDS.has(term);
}

export function searchDocs(
  documents: Record<string, Doc>,
  query: string,
  lang: string
) {
  const terms = query.toLowerCase().split(/\s+/).filter(filterCommonWords);

  const TITLE_SCORE = 10;
  const DESC_SCORE = 5;
  const HEADERS_SCORE = 3;
  const FILE_PATH_SCORE = 5;

  const results = Object.keys(documents)
    .filter((file) => file.startsWith(lang))
    .map((file) => {
      const doc = documents[file];
      let score = 0;
      const title = doc.title.toLowerCase();
      const desc = (doc.description || '').toLowerCase();
      const headers = (doc.headers || '').toLowerCase();

      terms.forEach((term) => {
        if (title.includes(term)) score += TITLE_SCORE;
        if (desc.includes(term)) score += DESC_SCORE;
        if (headers.includes(term)) score += HEADERS_SCORE;
        if (file.includes(term)) score += FILE_PATH_SCORE;
      });

      return { file, doc, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score);

  return results;
}
