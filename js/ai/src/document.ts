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

import z from 'zod';

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

export const DocumentDataSchema = z.object({
  content: z.array(PartSchema),
  metadata: z.record(z.string(), z.any()).optional(),
});
export type DocumentData = z.infer<typeof DocumentDataSchema>;

/**
 * Document represents document content along with its metadata that can be embedded, indexed or
 * retrieved. Each document can contain multiple parts (for example text and an image)
 */
export class Document implements DocumentData {
  content: Part[];
  metadata?: Record<string, any>;

  constructor(data: DocumentData) {
    this.content = data.content;
    this.metadata = data.metadata;
  }

  static fromText(text: string, metadata?: Record<string, any>) {
    return new Document({
      content: [{ text }],
      metadata,
    });
  }

  /**
   * Concatenates all `text` parts present in the document with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  /**
   * Returns the first media part detected in the document. Useful for extracting
   * (for example) an image.
   * @returns The first detected `media` part in the document.
   */
  media(): { url: string; contentType?: string } | null {
    return this.content.find((part) => part.media)?.media || null;
  }

  toJSON(): DocumentData {
    return {
      content: this.content,
      metadata: this.metadata,
    };
  }
}
