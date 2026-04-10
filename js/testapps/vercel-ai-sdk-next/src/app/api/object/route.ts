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

import { objectHandler } from '@genkit-ai/vercel-ai-sdk';
import { notificationsFlow } from '@/genkit/object';

/**
 * useObject endpoint.
 *
 * The objectHandler adapter:
 * 1. Parses any JSON from the POST body and passes it as flow input
 * 2. Streams raw text/plain JSON fragments from the flow's streamingCallback
 *
 * useObject reassembles the fragments incrementally and updates the
 * partial object in the UI as the stream arrives.
 *
 * Client usage:
 *   const { object, submit, isLoading } = useObject({
 *     api: '/api/object',
 *     schema: NotificationsSchema,
 *   });
 *   submit({ topic: 'weather' });
 */
export const POST = objectHandler(notificationsFlow);
