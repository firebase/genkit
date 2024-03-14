//
// IMPORTANT: Keep this file in sync with genkit/ai/src/retrievers.ts!
//
import { z } from 'zod';

const BaseDocumentSchema = z.object({
  metadata: z.record(z.string(), z.any()).optional(),
});

export const TextDocumentSchema = BaseDocumentSchema.extend({
  content: z.string(),
});
export type TextDocument = z.infer<typeof TextDocumentSchema>;
