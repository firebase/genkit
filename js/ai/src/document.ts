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
import type { Embedding } from './embedder';

const EmptyPartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
  data: z.unknown().optional(),
  metadata: z.record(z.unknown()).optional(),
  custom: z.record(z.unknown()).optional(),
  reasoning: z.never().optional(),
  resource: z.never().optional(),
});

/**
 * Zod schema for a text part.
 */
export const TextPartSchema = EmptyPartSchema.extend({
  /** The text of the message. */
  text: z.string(),
});

/**
 * Zod schema for a reasoning part.
 */
export const ReasoningPartSchema = EmptyPartSchema.extend({
  /** The reasoning text of the message. */
  reasoning: z.string(),
});

/**
 * Text part.
 */
export type TextPart = z.infer<typeof TextPartSchema>;

/**
 * Zod schema of media.
 */
export const MediaSchema = z.object({
  /** The media content type. Inferred from data uri if not provided. */
  contentType: z.string().optional(),
  /** A `data:` or `https:` uri containing the media content.  */
  url: z.string(),
});

/**
 * Zod schema of a media part.
 */
export const MediaPartSchema = EmptyPartSchema.extend({
  media: MediaSchema,
});

/**
 * Media part.
 */
export type MediaPart = z.infer<typeof MediaPartSchema>;

/**
 * Zod schema of a tool request.
 */
export const ToolRequestSchema = z.object({
  /** The call id or reference for a specific request. */
  ref: z.string().optional(),
  /** The name of the tool to call. */
  name: z.string(),
  /** The input parameters for the tool, usually a JSON object. */
  input: z.unknown().optional(),
});
export type ToolRequest = z.infer<typeof ToolRequestSchema>;

/**
 * Zod schema of a tool request part.
 */
export const ToolRequestPartSchema = EmptyPartSchema.extend({
  /** A request for a tool to be executed, usually provided by a model. */
  toolRequest: ToolRequestSchema,
});

/**
 * Tool part.
 */
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;

/**
 * Zod schema of a tool response.
 */
export const ToolResponseSchema = z.object({
  /** The call id or reference for a specific request. */
  ref: z.string().optional(),
  /** The name of the tool. */
  name: z.string(),
  /** The output data returned from the tool, usually a JSON object. */
  output: z.unknown().optional(),
});
export type ToolResponse = z.infer<typeof ToolResponseSchema>;

/**
 * Zod schema of a tool response part.
 */
export const ToolResponsePartSchema = EmptyPartSchema.extend({
  /** A provided response to a tool call. */
  toolResponse: ToolResponseSchema,
});

/**
 * Tool response part.
 */
export type ToolResponsePart = z.infer<typeof ToolResponsePartSchema>;

/**
 * Zod schema of a data part.
 */
export const DataPartSchema = EmptyPartSchema.extend({
  data: z.unknown(),
});

/**
 * Data part.
 */
export type DataPart = z.infer<typeof DataPartSchema>;

/**
 * Zod schema of a custom part.
 */
export const CustomPartSchema = EmptyPartSchema.extend({
  custom: z.record(z.any()),
});

/**
 * Custom part.
 */
export type CustomPart = z.infer<typeof CustomPartSchema>;

/**
 * Zod schema of a resource part.
 */
export const ResourcePartSchema = EmptyPartSchema.extend({
  resource: z.object({
    uri: z.string(),
  }),
});

/**
 * Resource part.
 */
export type ResourcePart = z.infer<typeof ResourcePartSchema>;

export const PartSchema = z.union([TextPartSchema, MediaPartSchema]);
export type Part = z.infer<typeof PartSchema>;

// We need both metadata and embedMetadata because they can
// contain the same fields (e.g. video start/stop) with different values.
export const DocumentDataSchema = z.object({
  content: z.array(PartSchema),
  metadata: z.record(z.string(), z.any()).optional(),
});
export type DocumentData = z.infer<typeof DocumentDataSchema>;

function deepCopy<T>(value: T): T {
  if (value === undefined) {
    return value;
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

/**
 * Document represents document content along with its metadata that can be embedded, indexed or
 * retrieved. Each document can contain multiple parts (for example text and an image)
 */
export class Document implements DocumentData {
  content: Part[];
  metadata?: Record<string, any>;

  constructor(data: DocumentData) {
    this.content = deepCopy(data.content);
    this.metadata = deepCopy(data.metadata);
  }

  static fromText(text: string, metadata?: Record<string, any>) {
    return new Document({
      content: [{ text }],
      metadata,
    });
  }

  // Construct a Document from a single media item
  static fromMedia(
    url: string,
    contentType?: string,
    metadata?: Record<string, unknown>
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
    });
  }

  // Construct a Document from content
  static fromData(
    data: string,
    dataType?: string,
    metadata?: Record<string, unknown>
  ) {
    if (dataType === 'text') {
      return this.fromText(data, metadata);
    }
    return this.fromMedia(data, dataType, metadata);
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
    return {
      content: deepCopy(this.content),
      metadata: deepCopy(this.metadata),
    } as DocumentData;
  }

  /**
   * Embedders may return multiple embeddings for a single document.
   * But storage still requires a 1:1 relationship. So we create an
   * array of Documents from a single document - one per embedding.
   * @param embeddings The embeddings to create the documents from.
   * @returns an array of documents based on this document and the embeddings.
   */
  getEmbeddingDocuments(embeddings: Embedding[]): Document[] {
    const documents: Document[] = [];
    for (const embedding of embeddings) {
      const jsonDoc = this.toJSON();
      if (embedding.metadata) {
        if (!jsonDoc.metadata) {
          jsonDoc.metadata = {};
        }
        jsonDoc.metadata.embedMetadata = embedding.metadata;
      }
      documents.push(new Document(jsonDoc));
    }
    checkUniqueDocuments(documents);
    return documents;
  }
}

// Unique documents are important because we key
// our vector storage on the Md5 hash of the JSON.stringify(document)
// So if we have multiple duplicate documents with
// different embeddings, we will either skip or overwrite
// those entries and lose embedding information.
// Export and boolean return value for testing only.
export function checkUniqueDocuments(documents: Document[]): boolean {
  const seen = new Set();
  for (const doc of documents) {
    const serialized = JSON.stringify(doc);
    if (seen.has(serialized)) {
      console.warn(
        'Warning: embedding documents are not unique. Are you missing embed metadata?'
      );
      return false;
    }
    seen.add(serialized);
  }
  return true;
}
