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

import * as z from 'zod';

export const AnalyticsInfoSchema = z.union([
  z.object({ enabled: z.literal(false) }),
  z.object({
    enabled: z.literal(true),
    property: z.string(),
    measurementId: z.string(),
    apiSecret: z.string(),
    clientId: z.string(),
    sessionId: z.string(),
    debug: z.object({
      debugMode: z.boolean(),
      validateOnly: z.boolean(),
    }),
  }),
]);

export type AnalyticsInfo = z.infer<typeof AnalyticsInfoSchema>;
