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

import { attendanceAgent } from './attendanceAgent';
import { ai } from './genkit';
import { searchEvents, upcomingHolidays } from './tools.js';

export const infoAgent = ai.definePrompt(
  {
    name: 'infoAgent',
    description:
      'transfer to this agent for general school information including holidays, events, FAQs, and school handbook policies. do not mention you are transferring, just do it',
    tools: [searchEvents, attendanceAgent, upcomingHolidays],
  },
  `You are Bell, a helpful assistant that provides information to parents of Sparkyville High School students. Use the information below and any tools made available to you to respond to the parent's requests.
  
=== Frequently Asked Questions

- Classes begin at 8am, students are dismissed at 3:30pm
- Parking permits are issued on a first-come first-serve basis beginning Aug 1

{{userContext @state }}
`
);
