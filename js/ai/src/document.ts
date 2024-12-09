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

import { z } from '@genkit-ai/core';
import { Embedding } from './embedder';

const EmptyPartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
});

export const TextPartSchema = EmptyPartSchema.extend({
  /** The text of the document. */
  text: z.string(),
});
export type TextPart = z.infer<typeof TextPartSchema>;

export const MediaPartSchema = EmptyPartSchema.extend({
  media: z.object({
    /** The media content type. Inferred from data uri if not provided. */
    contentType: z.string().optional(),
    /** A `data:` or `https:` uri containing the media content.  */
    url: z.string(),
  }),
});
export type MediaPart = z.infer<typeof MediaPartSchema>;

export const PartSchema = z.union([TextPartSchema, MediaPartSchema]);
export type Part = z.infer<typeof PartSchema>;

// We need both metadata and embedMetadata because they can
// contain the same fields (e.g. video start/stop) with different values.
export const DocumentDataSchema = z.object({
  content: z.array(PartSchema),
  metadata: z.record(z.string(), z.any()).optional(),
  embedMetadata: z.record(z.string(), z.unknown()).optional(),
});
export type DocumentData = z.infer<typeof DocumentDataSchema>;

/**
 * Document represents document content along with its metadata that can be embedded, indexed or
 * retrieved. Each document can contain multiple parts (for example text and an image)
 */
export class Document implements DocumentData {
  content: Part[];
  metadata?: Record<string, any>;
  embedMetadata?: Record<string, unknown>;

  constructor(data: DocumentData) {
    this.content = data.content as Part[];
    this.metadata = data.metadata as Record<string, any>;
    this.embedMetadata = data.embedMetadata as Record<string, unknown>;
  }

  static fromText(
    text: string,
    metadata?: Record<string, any>,
    embedMetadata?: Record<string, unknown>
  ) {
    return new Document({
      content: [{ text }],
      metadata,
      embedMetadata,
    });
  }

  // Construct a Document from a single media item
  static fromMedia(
    url: string,
    contentType?: string,
    metadata?: Record<string, unknown>,
    embedMetadata?: Record<string, unknown>
  ) {
    return new Document({
      content: [
        {
          media: {
            contentType,
            url,
          },
        },
      ],
      metadata,
      embedMetadata,
    });
  }

  // Construct a Document from content
  static fromData(
    data: string,
    dataType?: string,
    metadata?: Record<string, unknown>,
    embedMetadata?: Record<string, unknown>
  ) {
    if (dataType === 'text') {
      return this.fromText(data, metadata, embedMetadata);
    }
    return this.fromMedia(data, dataType, metadata, embedMetadata);
  }

  /**
   * Concatenates all `text` parts present in the document with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  get text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  /**
   * Media array getter.
   * @returns the array of media parts.
   */
  get media(): { url: string; contentType?: string }[] {
    return this.content
      .filter((part) => part.media && !part.text)
      .map((part) => part.media!);
  }

  /**
   * Gets the first item in the document. Either text or media url.
   */
  get data(): string {
    //
    if (this.text) {
      return this.text;
    }
    if (this.media) {
      return this.media[0].url;
    }
    return '';
  }

  /**
   * Gets the contentType of the data that is returned by data()
   */
  get dataType(): string | undefined {
    if (this.text) {
      return 'text';
    }
    if (this.media && this.media[0].contentType) {
      return this.media[0].contentType;
    }
    return undefined;
  }

  toJSON(): DocumentData {
    let jsonDoc: DocumentData = {
      content: this.content,
      metadata: this.metadata,
    };
    if (this.embedMetadata) {
      jsonDoc.embedMetadata = this.embedMetadata;
    }
    return jsonDoc;
  }

  /**
   * Embedders may return multiple embeddings for a single document.
   * But storage still requires a 1:1 relationship. So we create an
   * array of Documents from a single document - one per embedding.
   * @param embeddings The embeddings to create the documents from.
   * @returns an array of documents based on this document and the embeddings.
   */
  getEmbeddingDocuments(embeddings: Embedding[]): Document[] {
    if (embeddings.length === 1) {
      // Already 1:1, we don't need to construct anything.
      return [this];
    }
    let documents: Document[] = [];
    for (const embedding of embeddings) {
      let jsonDoc = this.toJSON();
      jsonDoc.embedMetadata = embedding.embedMetadata;
      documents.push(new Document(jsonDoc));
    }
    checkUniqueDocuments(documents);
    return documents;
  }
}

function checkUniqueDocuments(documents: Document[]) {
  const seen = new Set();
  for (const doc of documents) {
    const serialized = JSON.stringify(doc);
    if (seen.has(serialized)) {
      console.warn(
        'Warning: embeddings are not unique. Are you missing embed metadata?'
      );
    }
    seen.add(serialized);
  }
}
