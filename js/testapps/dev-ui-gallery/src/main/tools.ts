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

import { defineTool } from '@genkit-ai/ai/tool';
import * as z from 'zod';

defineTool(
  {
    name: 'getWeather',
    description: 'Get the weather for the given location.',
    inputSchema: z.object({ city: z.string() }),
    outputSchema: z.object({
      temperatureF: z.number(),
      conditions: z.string(),
    }),
  },
  async (input) => {
    return {
      temperatureF: 70,
      conditions: 'sunny',
    };
  }
);

defineTool(
  {
    name: 'getTime',
    description: 'Get the current time',
    inputSchema: z.object({ timezone: z.string().optional() }),
    outputSchema: z.object({ time: z.number() }),
  },
  async (input) => {
    return { time: Date.now() };
  }
);
