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

import { MessageData } from '@genkit-ai/ai/model';

export const sampleMenuHistory: MessageData[] = [
  {
    role: 'user',
    content: [
      {
        text: 'Suggest a single menu item title of a truck themed restaurant',
      },
    ],
  },
  {
    role: 'model',
    content: [
      {
        text: '"Blazing Burnout Burger"',
      },
    ],
  },
  {
    role: 'user',
    content: [
      {
        text: "That's pretty good, but suggest another one that's spicier",
      },
    ],
  },
  {
    role: 'model',
    content: [
      {
        text: '"Redline Reaper Wrap"',
      },
    ],
  },
];
