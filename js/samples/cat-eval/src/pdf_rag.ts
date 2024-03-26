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

import { generate } from '@genkit-ai/ai/generate';
import { Document, index, retrieve } from '@genkit-ai/ai/retrievers';
import { flow, run } from '@genkit-ai/flow';
import {
  devLocalIndexerRef,
  devLocalRetrieverRef,
} from '@genkit-ai/plugin-dev-local-vectorstore';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
import { chunk } from 'llm-chunk';
import path from 'path';
import * as z from 'zod';

export const pdfChatRetriever = devLocalRetrieverRef('pdfQA');

export const pdfChatIndexer = devLocalIndexerRef('pdfQA');

function ragTemplate({
  context,
  question,
}: {
  context: string;
  question: string;
}) {
  return `Use the following pieces of context to answer the question at the end.
 If you don't know the answer, just say that you don't know, don't try to make up an answer.

${context}
Question: ${question}
Helpful Answer:`;
}

// Define a simple RAG flow, we will evaluate this flow
export const pdfQA = flow(
  {
    name: 'pdfQA',
    input: z.string(),
    output: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: pdfChatRetriever,
      query,
      options: { k: 3 },
    });
    console.log(docs);

    const augmentedPrompt = ragTemplate({
      question: query,
      context: docs.map((d) => d.text()).join('\n\n'),
    });
    const llmResponse = await generate({
      model: geminiPro,
      prompt: { text: augmentedPrompt },
    });
    return llmResponse.text();
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
// genkit flow:run indexPdf '"./docs/sfspca-cat-adoption-handbook-2023.pdf"'
export const indexPdf = flow(
  {
    name: 'indexPdf',
    input: z.string().describe('PDF file path'),
    output: z.void(),
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

// genkit flow:run synthesizeQuestions '"./docs/sfspca-cat-adoption-handbook-2023.pdf"' --output synthesizedQuestions.json
export const synthesizeQuestions = flow(
  {
    name: 'synthesizeQuestions',
    input: z.string().describe('PDF file path'),
    output: z.array(z.string()),
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
