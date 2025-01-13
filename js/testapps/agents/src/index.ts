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

import { createInterface } from 'node:readline/promises';
import { ai } from './genkit.js';
import {
  getRecentGrades,
  reportAbsence,
  reportTardy,
  searchEvents,
  upcomingHolidays,
} from './tools.js';
import { AgentState } from './types.js';
import { EXAMPLE_USER_CONTEXT } from './data.js';

ai.defineHelper(
  'userContext',
  (state: AgentState) => `=== User Context

- The current parent user is ${state?.parentName}
- The current date and time is: ${new Date().toString()}

=== Registered students of the current user

${state?.students.map((s) => ` - ${s.name}, student id: ${s.id} grade: ${s.grade}, activities: \n${s.activities.map((a) => `   - ${a}`).join('\n')}`).join('\n\n')}`
);

export const gradesAgent = ai.defineChatAgent({
  name: `gradesAgent`,
  description: `Transfer to this agent when the user asks about attendance. Do not mention that you are transferring, just do it.`,
  tools: [getRecentGrades, 'infoAgent'],
  instructions: `
You are Bell, a helpful attendance assistance agent for Sparkyville High School. 
A parent has been referred to you to handle a grades-related concern. 
Use the tools available to you to assist the parent.

Guidelines:
- Parents may only view grades for their own students
- Always verify the student belongs to the parent before sharing grade information
- Be encouraging and positive when discussing grades
- If asked about non-grade related topics, transfer back to the info agent
- Format grade information in a clear, easy-to-read manner

{{ userContext @state }}
  `,
});

export const attendanceAgent = ai.defineChatAgent({
  name: `attendanceAgent`,
  description: 'transfer to this agent when the user asks questions about attendance-related concerns like tardies or absences. do not mention that you are transferring, just do it',
  tools: [reportAbsence, reportTardy, 'infoAgent'],
  instructions: `
You are Bell, a helpful attendance assistance agent for Sparkyville High School. You are talking directly to the parent. 
A parent has been referred to you to handle a attendance-related concern. 
Use the tools available to you to assist the parent.

- Parents may only report absences for their own students.
- If you are unclear about any of the fields required to report an absence or tardy, request clarification before using the tool.
- If the parent asks about anything other than attendance-related concerns that you can handle, transfer to the info agent.

 {{ userContext @state }}
  `,
});

const infoAgent = ai.defineChatAgent({
  name: 'infoAgent',
  description: `This agent helps with answering inquiries and requests.`,
  instructions: `You are Bell, the friendly AI office receptionist at Sparkyville High School.
  
  Your job is to help answer inquiries from parents. Parents may ask you school-related questions, request grades or test scores,
  or call in to let you know their child will be late or absent. 

  You have some specialized agents in different departments that you can transfer to. 

  1. Grades Agent - This agent can provide informtion about previous scores for assignments and tests.
  2. Attendance Agent - This agent can help with attendance requests, such as marking a student as late/tardy or absent.

  Use the information below and any tools made available to you to respond to the parent's requests.
  
  If the parent has an inquiry that you do not know the answer to, do NOT make the answer up. Simply let them know that you cannot help them,
  and direct them to call the office directly where a human will be able to help them.

  === Frequently Asked Questions

  - Classes begin at 8am, students are dismissed at 3:30pm
  - Parking permits are issued on a first-come first-serve basis beginning Aug 1

  {{ userContext @state }}
`,
  tools: [searchEvents, attendanceAgent, gradesAgent, upcomingHolidays],
});

const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

(async () => {
  const session = ai.createSession({
    initialState: EXAMPLE_USER_CONTEXT,
  });
  const chat = session.chat(infoAgent);
  while (true) {
    const input = await rl.question('say: ');
    const { text } = await chat.send(input);
    console.log(JSON.stringify(session.toJSON(), undefined, 2));
    console.log(text);
  }
})();
