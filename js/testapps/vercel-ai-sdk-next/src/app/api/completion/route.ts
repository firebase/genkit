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

import { completionFlow } from '@/genkit/completion';
import { completionHandler } from '@genkit-ai/vercel-ai-sdk';

/**
 * useCompletion endpoint — SSE data-stream mode (default).
 *
 * The completionHandler adapter:
 * 1. Reads { prompt: string } from the POST body
 * 2. Streams text/typed chunks as Vercel AI SDK data-stream SSE events
 *
 * Client usage:
 *   const { completion, input, handleInputChange, handleSubmit } = useCompletion({
 *     api: '/api/completion',
 *   });
 *
 * To use plain text streaming instead, set streamProtocol: 'text' in
 * both completionHandler options and the useCompletion client options.
 */
export const POST = completionHandler(completionFlow);
