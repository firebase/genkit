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

import { z } from 'genkit';

export const cacheConfigSchema = z.union([
  z.boolean(),
  z.object({ ttlSeconds: z.number().optional() }).passthrough(),
]);

export type CacheConfig = z.infer<typeof cacheConfigSchema>;

export const cacheConfigDetailsSchema = z.object({
  cacheConfig: cacheConfigSchema,
  endOfCachedContents: z.number(),
});

export type CacheConfigDetails = z.infer<typeof cacheConfigDetailsSchema>;
