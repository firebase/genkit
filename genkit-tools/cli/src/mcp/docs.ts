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

import { record } from '@genkit-ai/tools-common/utils';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp';
import { ContentBlock } from '@modelcontextprotocol/sdk/types';
import { existsSync, mkdirSync, readFileSync, renameSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import { Readable } from 'node:stream';
import os from 'os';
import path from 'path';
import z from 'zod';
import { version } from '../utils/version';
import { McpRunToolEvent } from './analytics.js';
import { enrichToolDescription } from './utils.js';

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

  const listSchema = {
    language: z
      .enum(['js', 'go', 'python'])
      .describe('Which language to list docs for (default js); type: string.')
      .default('js'),
  };

  server.registerTool(
    'list_genkit_docs',
    {
      title: 'List Genkit Docs',
      description: enrichToolDescription(
        'Use this to see a list of available Genkit documentation files. Returns `filePaths` that can be passed to `read_genkit_docs`.',
        listSchema
      ),
      inputSchema: listSchema,
    },
    async ({ language }) => {
      await record(new McpRunToolEvent('list_genkit_docs'));
      const lang = language || 'js';

      const fileList = Object.keys(documents)
        .filter((file) => file.startsWith(lang))
        .sort();

      const output =
        `Genkit Documentation Index (${lang}):\n\n` +
        fileList
          .map((file) => {
            const doc = documents[file];
            let summary = ` - FilePath: ${file}\n   Title: ${doc.title}\n`;
            if (doc.description) {
              summary += `   Description: ${doc.description}\n`;
            }
            if (doc.headers) {
              summary += `   Headers:\n     ${doc.headers.split('\n').join('\n     ')}\n`;
            }
            return summary;
          })
          .join('\n') +
        `\n\nUse 'search_genkit_docs' to find specific topics. Copy the 'FilePath' values to 'read_genkit_docs' to read content.`;

      return {
        content: [{ type: 'text', text: output }],
      };
    }
  );

  const searchSchema = {
    query: z
      .string()
      .describe('Keywords to search for in documentation; type: string.'),
    language: z
      .enum(['js', 'go', 'python'])
      .describe('Which language to search docs for (default js); type: string.')
      .default('js'),
  };

  server.registerTool(
    'search_genkit_docs',
    {
      title: 'Search Genkit Docs',
      description: enrichToolDescription(
        'Use this to search the Genkit documentation using keywords. Returns ranked results with `filePaths` for `read_genkit_docs`. Warning: Generic terms (e.g. "the", "and") may return false positives; use specific technical terms (e.g. "rag", "firebase", "context").',
        searchSchema
      ),
      inputSchema: searchSchema,
    },
    async ({ query, language }) => {
      await record(new McpRunToolEvent('search_genkit_docs'));
      const lang = language || 'js';
      const terms = query
        .toLowerCase()
        .split(/\s+/)
        .filter((t) => t.length > 2); // Filter out short words to reduce noise

      const results = Object.keys(documents)
        .filter((file) => file.startsWith(lang))
        .map((file) => {
          const doc = documents[file];
          let score = 0;
          const title = doc.title.toLowerCase();
          const desc = (doc.description || '').toLowerCase();
          const headers = (doc.headers || '').toLowerCase();

          terms.forEach((term) => {
            if (title.includes(term)) score += 10;
            if (desc.includes(term)) score += 5;
            if (headers.includes(term)) score += 3;
            if (file.includes(term)) score += 5;
          });

          return { file, doc, score };
        })
        .filter((r) => r.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 10); // Top 10

      if (results.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: `No results found for "${query}" in ${lang} docs. Try broader keywords or use 'list_genkit_docs' to see all files.`,
            },
          ],
        };
      }

      const output =
        `Found ${results.length} matching documents for "${query}":\n\n` +
        results
          .map((r) => {
            let summary = `### ${r.doc.title}\n**FilePath**: ${r.file}\n`;
            if (r.doc.description)
              summary += `**Description**: ${r.doc.description}\n`;
            return summary;
          })
          .join('\n') +
        `\n\nCopy the 'FilePath' values to 'read_genkit_docs' to read content.`;

      return {
        content: [{ type: 'text', text: output }],
      };
    }
  );

  const readSchema = {
    filePaths: z
      .array(z.string())
      .describe(
        'The `filePaths` of the docs to read. Obtain these exactly from `list_genkit_docs` or `search_genkit_docs` (e.g. "js/overview.md"); type: string[].'
      ),
  };

  server.registerTool(
    'read_genkit_docs',
    {
      title: 'Read Genkit Docs',
      description: enrichToolDescription(
        'Use this to read the full content of specific Genkit documentation files. You must provide `filePaths` from the list/search tools.',
        readSchema
      ),
      inputSchema: readSchema,
    },
    async ({ filePaths }) => {
      await record(new McpRunToolEvent('read_genkit_docs'));

      const content = [] as ContentBlock[];

      // filePaths is required by Zod schema, but check length just in case
      if (!filePaths || !filePaths.length) {
        return {
          content: [
            {
              type: 'text',
              text: 'No filePaths provided. Please provide an array of file paths.',
            },
          ],
          isError: true,
        };
      }

      for (const file of filePaths) {
        if (documents[file]) {
          content.push({ type: 'text', text: documents[file]?.text });
        } else {
          content.push({
            type: 'text',
            text: `Document not found: ${file}. Please check the path using list_genkit_docs.`,
          });
        }
      }

      return { content };
    }
  );
}
