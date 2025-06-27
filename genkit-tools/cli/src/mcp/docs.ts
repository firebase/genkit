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

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp';
import { ContentBlock } from '@modelcontextprotocol/sdk/types';
import { existsSync, mkdirSync, readFileSync, renameSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import { Readable } from 'node:stream';
import os from 'os';
import path from 'path';
import z from 'zod';
import { version } from '../utils/version';

const DOCS_URL =
  process.env.GENKIT_DOCS_BUNDLE_URL ??
  'http://genkit.dev/docs-bundle-experimental.json';

const DOCS_BUNDLE_FILE_PATH = path.resolve(
  os.homedir(),
  '.genkit',
  'docs',
  version,
  'bundle.json'
);

async function maybeDownloadDocsBundle() {
  if (existsSync(DOCS_BUNDLE_FILE_PATH)) {
    return;
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

interface Doc {
  title: string;
  description?: string;
  text: string;
  lang: string;
  headers: string;
}

export async function defineDocsTool(server: McpServer) {
  await maybeDownloadDocsBundle();
  const documents = JSON.parse(
    readFileSync(DOCS_BUNDLE_FILE_PATH, { encoding: 'utf8' })
  ) as Record<string, Doc>;

  server.registerTool(
    'lookup_genkit_docs',
    {
      title: 'Genkit Docs',
      description:
        'Use this to look up documentation for the Genkit AI framework.',
      inputSchema: {
        language: z
          .enum(['js', 'go', 'python'])
          .describe('which language these docs are for (default js).')
          .default('js'),
        files: z
          .array(z.string())
          .describe(
            'Specific docs files to look up. If empty or not specified an index will be returned. Always lookup index first for exact file names.'
          )
          .optional(),
      },
    },
    async ({ language, files }) => {
      const content = [] as ContentBlock[];
      if (!language) {
        language = 'js';
      }

      if (!files || !files.length) {
        content.push({
          type: 'text',
          text:
            Object.keys(documents)
              .filter((file) => file.startsWith(language))
              .map((file) => {
                let fileSummary = ` - File: ${file}\n   Title: ${documents[file].title}\n`;
                if (documents[file].description) {
                  fileSummary += `   Description: ${documents[file].description}\n`;
                }
                if (documents[file].headers) {
                  fileSummary += `   Headers:\n     ${documents[file].headers.split('\n').join('\n     ')}\n`;
                }
                return fileSummary;
              })
              .join('\n') +
            `\n\nIMPORTANT: if doing anything more than basic model calling, look up "${language}/models.md" file, it contains important details about how to work with models.\n\n`,
        });
      } else {
        for (const file of files) {
          if (documents[file]) {
            content.push({ type: 'text', text: documents[file]?.text });
          } else {
            content.push({ type: 'text', text: `${file} not found` });
          }
        }
      }

      return { content };
    }
  );
}
