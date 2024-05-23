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

//
// IMPORTANT: Keep this file in sync with genkit/ai/src/document.ts!
//

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
