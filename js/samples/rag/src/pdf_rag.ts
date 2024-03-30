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

import { generate } from '@genkit-ai/ai';
import { Document, index, retrieve } from '@genkit-ai/ai/retriever';
import { defineFlow, run } from '@genkit-ai/flow';
import {
  devLocalIndexerRef,
  devLocalRetrieverRef,
} from '@genkit-ai/plugin-dev-local-vectorstore';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
import { chunk } from 'llm-chunk';
import path from 'path';
import * as z from 'zod';
import { augmentedPrompt } from './prompt';

export const pdfChatRetriever = devLocalRetrieverRef('pdfQA');

export const pdfChatIndexer = devLocalIndexerRef('pdfQA');

// Define a simple RAG flow, we will evaluate this flow
export const pdfQA = defineFlow(
  {
    name: 'pdfQA',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: pdfChatRetriever,
      query,
      options: { k: 3 },
    });

    return augmentedPrompt
      .generate({
        input: {
          question: query,
          context: docs.map((d) => d.text()),
        },
      })
      .then((r) => r.text());
  }
);

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

// Define a flow to index documents into the "vector store"
// genkit flow:run indexPdf '"35650.pdf"'
export const indexPdf = defineFlow(
  {
    name: 'indexPdf',
    inputSchema: z.string().describe('PDF file path'),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () => extractText(filePath));

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const documents: Document[] = chunks.map((text) => {
      return Document.fromText(text, { filePath });
    });

    await index({
      indexer: pdfChatIndexer,
      documents,
    });
  }
);

async function extractText(filePath: string): Promise<string> {
  const pdfjsLib = await import('pdfjs-dist');
  let doc = await pdfjsLib.getDocument(filePath).promise;

  let pdfTxt = '';
  const numPages = doc.numPages;
  for (let i = 1; i <= numPages; i++) {
    let page = await doc.getPage(i);
    let content = await page.getTextContent();
    let strings = content.items.map((item) => {
      const str: string = (item as any).str;
      return str === '' ? '\n' : str;
    });

    pdfTxt += '\n\npage ' + i + '\n\n' + strings.join('');
  }
  return pdfTxt;
}

// genkit flow:run synthesizeQuestions '"35650.pdf"' --output synthesizedQuestions.json
// genkit flow:batchRun pdfQA synthesizedQuestions.json --output batchinput_small_out.json
export const synthesizeQuestions = defineFlow(
  {
    name: 'synthesizeQuestions',
    inputSchema: z.string().describe('PDF file path'),
    outputSchema: z.array(z.string()),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () => extractText(filePath));

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const questions: string[] = [];
    for (let i = 0; i < chunks.length; i++) {
      const qResponse = await generate({
        model: geminiPro,
        prompt: {
          text: `Generate one question about the text below: ${chunks[i]}`,
        },
      });
      questions.push(qResponse.text());
    }
    return questions;
  }
);
