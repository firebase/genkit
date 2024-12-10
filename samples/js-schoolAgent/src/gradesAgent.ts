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

import { ai } from './genkit.js';
import { getRecentGrades } from './tools.js';
import { agentDescription, agentPrompt } from './util.js';

const tools = [getRecentGrades, 'routingAgent'];
const specialization = 'grades';

const toolNames: string[] = tools.map((item) => {
  if (typeof item === 'string') {
    return item;
  } else {
    return item.name;
  }
});

export const gradesAgent = ai.definePrompt(
  {
    name: `${specialization}Agent`,
    description: agentDescription(specialization, toolNames),
    tools,
  },
  ` {{ role "system"}}
${agentPrompt(specialization)}

Guidelines:
- Parents may only view grades for their own students
- Always verify the student belongs to the parent before sharing grade information
- Be encouraging and positive when discussing grades
- If asked about non-grade related topics, transfer back to the info agent
- Format grade information in a clear, easy-to-read manner

{{ userContext @state }}
  `
);
