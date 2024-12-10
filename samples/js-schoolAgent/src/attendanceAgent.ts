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
import { agentDescription, agentPrompt } from './util.js';

const tools = [reportAbsence, reportTardy, 'routingAgent'];
const specialization = 'attendance';

const toolNames: string[] = tools.map((item) => {
  if (typeof item === 'string') {
    return item;
  } else {
    return item.name;
  }
});

export const attendanceAgent = ai.definePrompt(
  {
    name: `${specialization}Agent`,
    description: agentDescription(specialization, toolNames),
    tools,
  },
  ` {{ role "system"}}
${agentPrompt(specialization)}

- Parents may only report absences for their own students.
- If you are unclear about any of the fields required to report an absence or tardy, request clarification before using the tool.
- If the parent asks about anything other than attendance-related concerns that you can handle, transfer to the info agent.

 {{ userContext @state }}
  `
);
