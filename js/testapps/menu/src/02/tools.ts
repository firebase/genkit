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

import { defineTool } from 'genkit';
import * as z from 'zod';
import { MenuItemSchema } from '../types.js';

import menuData from '../../data/menu.json' assert { type: 'json' };

export const menuTool = defineTool(
  {
    name: 'todaysMenu',
    description: "Use this tool to retrieve all the items on today's menu",
    inputSchema: z.object({}),
    outputSchema: z.object({
      menuData: z
        .array(MenuItemSchema)
        .describe('A list of all the items on the menu'),
    }),
  },
  async () => Promise.resolve({ menuData: menuData })
);
