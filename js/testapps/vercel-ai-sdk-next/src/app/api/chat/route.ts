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

import { chatHandler } from '@genkit-ai/vercel-ai-sdk';
import { chatFlow } from '@/genkit/chat';

/**
 * useChat endpoint.
 *
 * The chatHandler adapter:
 * 1. Parses the UIMessage[] from the request body
 * 2. Converts them to Genkit MessageData[] via toGenkitMessages()
 * 3. Streams the flow output as Vercel AI SDK data-stream SSE events
 *
 * Client usage:
 *   const { messages, input, handleInputChange, handleSubmit } = useChat({
 *     api: '/api/chat',
 *   });
 */
export const POST = chatHandler(chatFlow);
