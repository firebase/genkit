/**
 * @license
 *
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

/**
 * A client library for remotely invoking deployed flows and other actions (e.g. models).
 *
 * ```ts
 * import { defineRemoteAction } from 'genkit/beta/client';
 *
 * const myFlow = defineRemoteAction({
 *   url: 'http://.../myFlow',
 *   inputSchema: z.object({ foo: z.string() }),
 *   outputSchema: z.string(),
 *   streamSchema: z.string(),
 * });
 *
 * const { stream } = myFlow.stream(
 *   { foo: 'bar' },
 *   { headers: { authentication: getAuthToken() } }
 * );
 *
 * for await (const chunk of stream) {
 *   console.log(chunk);
 * }
 * ```
 *
 * @module
 */

export {
  RemoteAction,
  StreamingResponse,
  defineRemoteAction,
  runFlow,
  streamFlow,
} from './client.js';
