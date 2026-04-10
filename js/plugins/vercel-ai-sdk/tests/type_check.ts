/**
 * Copyright 2026 Google LLC
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
 * This file is NOT a runtime test — it only exercises compile-time type checks.
 * Run: npx tsc --noEmit -p tests/tsconfig.typecheck.json
 *
 * Every line marked @ts-expect-error MUST produce a type error.
 * If tsc passes with zero errors this file is working correctly.
 */

import { z, type Action } from 'genkit/beta';
import { chatHandler } from '../src/chat.js';
import { completionHandler } from '../src/completion.js';
import { objectHandler } from '../src/object.js';
import { MessagesSchema, StreamChunkSchema } from '../src/schema.js';

// ---- chatHandler: correct usage (should compile) -------------------------
declare const goodChat: Action<
  typeof MessagesSchema,
  any,
  typeof StreamChunkSchema
>;
chatHandler(goodChat);

// ---- chatHandler: wrong inputSchema --------------------------------------
declare const badChatInput: Action<z.ZodString, any, typeof StreamChunkSchema>;
// @ts-expect-error inputSchema must accept Messages (not string)
chatHandler(badChatInput);

// ---- chatHandler: wrong inputSchema (number) -----------------------------
declare const badChatNumber: Action<z.ZodNumber, any, typeof StreamChunkSchema>;
// @ts-expect-error inputSchema must accept Messages (not number)
chatHandler(badChatNumber);

// ---- completionHandler: correct usage (should compile) -------------------
declare const goodCompletion: Action<
  z.ZodString,
  any,
  typeof StreamChunkSchema
>;
completionHandler(goodCompletion);

// ---- completionHandler: wrong inputSchema --------------------------------
declare const badCompInput: Action<
  z.ZodObject<any>,
  any,
  typeof StreamChunkSchema
>;
// @ts-expect-error inputSchema must accept string (not object)
completionHandler(badCompInput);

// ---- objectHandler: correct usage (should compile) -----------------------
declare const goodObject: Action<z.ZodTypeAny, z.ZodTypeAny, z.ZodString>;
objectHandler(goodObject);

// objectHandler accepts any input schema, so no wrong-input test needed.
// The stream schema constraint (must produce strings) is enforced at runtime.
