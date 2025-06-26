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
import { reportAbsence, reportTardy } from './tools.js';
import { agentDescription } from './util.js';

const tools = [reportAbsence, reportTardy, 'routingAgent'];
const specialization = 'attendance';

const toolNames: string[] = tools.map((item) => {
  if (typeof item === 'string') {
    return item;
  } else {
    return item.__action.name;
  }
});

export const attendanceAgent = ai.definePrompt(
  {
    name: `${specialization}Agent`,
    description: agentDescription(specialization, toolNames),
    tools,
  },
  ` {{ role "system"}}

You are Bell, a helpful attendance assistance agent for Sparkyville High School. 
A parent has been referred to you to handle a ${specialization}-related concern. 
Use the tools available to you to assist the parent.

- Parents may only report absences for their own students.
- If you are unclear about any of the fields required to report an absence or tardy, request clarification before using the tool.
- If the parent asks about anything other than attendance-related concerns that you can handle, transfer to the info agent.

 {{ userContext @state }}
  `
);
