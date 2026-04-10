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

/**
 * @genkit-ai/vercel-ai-sdk
 *
 * Adapter helpers that make Genkit flows work as backends for the Vercel AI
 * SDK UI hooks: `useChat()`, `useCompletion()`, and `useObject()`.
 *
 * Each handler returns a standard `(req: Request) => Promise<Response>` that
 * can be dropped into any framework that follows the Fetch API conventions —
 * Next.js App Router, Hono, SvelteKit, etc.
 */

export { chatHandler, type ChatHandlerOptions } from './chat.js';
export {
  completionHandler,
  type CompletionHandlerOptions,
} from './completion.js';
export {
  toGenkitMessages,
  type UIMessage,
  type UIMessagePart,
} from './convert.js';
export { toFlowOutput, toStreamChunks } from './generate.js';
export { objectHandler, type ObjectHandlerOptions } from './object.js';
export {
  FlowOutputSchema,
  MessagesSchema,
  StreamChunkSchema,
  type FlowOutput,
  type Messages,
  type StreamChunk,
} from './schema.js';
