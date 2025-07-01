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

import { multimodalEmbedding001 } from '@genkit-ai/vertexai';
import fileTypeChecker from 'file-type-checker';
import fs from 'fs';
import { Document } from 'genkit';
import { mongoIndexerRef, mongoRetrieverRef } from 'genkitx-mongodb';
import { chunk } from 'llm-chunk';
import { PDFDocument, PDFRawStream } from 'pdf-lib';
import pdf from 'pdf-parse';
import {
  MONGODB_DB_NAME,
  MONGODB_DOCUMENT_COLLECTION_NAME,
} from '../../common/config.js';
import { ai } from '../../common/genkit.js';
import {
  AnswerOutputSchema,
  DocumentIndexInput,
  DocumentIndexInputSchema,
  QuestionInput,
  QuestionInputSchema,
} from '../../common/types.js';
import { getFilePath } from '../../common/utils.js';
import { documentPrompt } from './document-prompt.js';

const dbName = MONGODB_DB_NAME;
const collectionName = MONGODB_DOCUMENT_COLLECTION_NAME;
const embedder = multimodalEmbedding001;

const chunkingConfig = {
  minLength: 800, // number of minimum characters into chunk
  maxLength: 1000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

async function extractImages(filePath: string): Promise<Document[]> {
  const imgDocs: Document[] = [];
  const pdfDoc = await PDFDocument.load(fs.readFileSync(filePath));
  const indirectObjects = pdfDoc.context.enumerateIndirectObjects();
  for (const [ref, obj] of indirectObjects) {
    if (obj instanceof PDFRawStream) {
      const detectedFileInfo = fileTypeChecker.detectFile(obj.contents);
      if (
        detectedFileInfo?.mimeType &&
        detectedFileInfo?.mimeType.startsWith('image/')
      ) {
        const base64 = Buffer.from(obj.contents).toString('base64');
        imgDocs.push(Document.fromMedia(base64, detectedFileInfo.mimeType));
      }
    }
  }
  return imgDocs;
}

async function extractText(filePath: string) {
  const dataBuffer = fs.readFileSync(filePath);
  const data = await pdf(dataBuffer);
  return data.text;
}

export const documentIndexerFlow = ai.defineFlow(
  {
    name: 'Document - Indexer Flow',
    inputSchema: DocumentIndexInputSchema,
  },
  async (input: DocumentIndexInput) => {
    let documents: Document[] = [];

    const filePath = getFilePath('document', input.name + '.pdf');

    const pdfTxt = await ai.run('extract-text', () => extractText(filePath));

    const chunks = await ai.run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const imageDocs = await ai.run('extract-images', () =>
      extractImages(filePath)
    );

    const textDocs: Document[] = chunks.map((text: string) => {
      return Document.fromText(text, { filePath });
    });
    documents = imageDocs.concat(textDocs);

    await ai.index({
      indexer: mongoIndexerRef('indexer'),
      documents,
      options: {
        dbName,
        collectionName,
        embeddingField: 'embedding',
        embedder,
        dataTypeField: 'documentType',
        metadataField: 'documentMetadata',
      },
    });

    return {
      answer: `Indexed ${documents.length} documents`,
    };
  }
);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function makeDataUrl(media: unknown) {
  if (isObject(media)) {
    if (
      typeof media.contentType === 'string' &&
      media.contentType.length > 0 &&
      typeof media.url === 'string' &&
      media.url.length > 0
    ) {
      return `data:${media.contentType};base64,${media.url}`;
    } else {
      throw new Error(
        'Failed to make data URL. Invalid or missing contentType or url'
      );
    }
  }
  throw new Error(
    'Failed to make data URL. Unexpected media type: ' + typeof media
  );
}

export const documentRetrieverFlow = ai.defineFlow(
  {
    name: 'Document - Retriever Flow',
    inputSchema: QuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input: QuestionInput, { sendChunk }) => {
    const docs = (await ai.retrieve({
      retriever: mongoRetrieverRef('retriever'),
      query: input.question,
      options: {
        dbName,
        collectionName,
        embedder,
        vectorSearch: {
          index: 'document_vector_index',
          path: 'embedding',
          exact: false,
          numCandidates: 10,
          limit: 3,
        },
        dataTypeField: 'documentType',
        metadataField: 'documentMetadata',
      },
    })) as Document[];

    return {
      answer: await documentPrompt(
        {
          question: input.question,
          text: docs.filter((d) => d.text?.length).map((d) => d.text),
          media: docs
            .filter(
              (d) => d.media[0]?.url?.length && d.media[0]?.contentType?.length
            )
            .map((d) => {
              return {
                dataUrl: makeDataUrl(d.media[0]),
              };
            }),
        },
        {
          onChunk: (c) => sendChunk(c.text),
        }
      ).then((r) => r.text),
    };
  }
);
