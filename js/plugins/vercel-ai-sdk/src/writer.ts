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
 * Re-export the AI SDK's stream response factory so consumers don't need to
 * import `ai` directly.
 *
 * `createUIMessageStream`  — creates a `ReadableStream<UIMessageChunk>`; pass
 *                            an `execute` callback that receives a `UIMessageStreamWriter`.
 * `createUIMessageStreamResponse` — wraps the stream in a properly-headered
 *                            `text/event-stream` `Response` (includes the
 *                            required `x-vercel-ai-ui-message-stream: v1` header).
 * `createTextStreamResponse` — creates a `text/plain` streaming `Response`
 *                            for `useCompletion({ streamProtocol: 'text' })`.
 */
export {
  createUIMessageStream,
  createUIMessageStreamResponse,
  createTextStreamResponse,
  type UIMessageStreamWriter,
} from 'ai';
