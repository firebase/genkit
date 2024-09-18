/**
 * Copyright 2024 Google LLC
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

import { index } from '@genkit-ai/ai';
import { Document } from '@genkit-ai/ai/retriever';
import { run } from '@genkit-ai/core';
import { devLocalIndexerRef } from '@genkit-ai/dev-local-vectorstore';
import { readFile } from 'fs/promises';
import { chunk } from 'llm-chunk';
import path from 'path';
import pdf from 'pdf-parse';
import * as z from 'zod';
import { genkit } from './index.js';

// Create a reference to the configured local indexer.
export const menuPdfIndexer = devLocalIndexerRef('menuQA');

// Create chunking config for indexing a pdf of a menu
// See full options in https://www.npmjs.com/package/llm-chunk
const chunkingConfig = {
  minLength: 1000,
  maxLength: 2000,
  splitter: 'sentence',
  overlap: 100,
  delimiters: '',
} as any;

// Define a flow to index documents into the "vector store"
// genkit flow:run indexMenu '"./docs/.pdf"'
export const indexMenu = genkit.defineFlow(
  {
    name: 'indexMenu',
    inputSchema: z.string().describe('PDF file path'),
    outputSchema: z.void(),
  },
  async (filePath: string) => {
    filePath = path.resolve(filePath);

    // Read the pdf.
    const pdfTxt = await run('extract-text', () =>
      extractTextFromPdf(filePath)
    );

    // Divide the pdf text into segments.
    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    // Convert chunks of text into documents to store in the index.
    const documents = chunks.map((text) => {
      return Document.fromText(text, { filePath });
    });

    // Add documents to the index.
    await index({
      indexer: menuPdfIndexer,
      documents,
    });
  }
);

async function extractTextFromPdf(filePath: string) {
  const pdfFile = path.resolve(filePath);
  const dataBuffer = await readFile(pdfFile);
  const data = await pdf(dataBuffer);
  return data.text;
}
