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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit as initAgenkit, z } from 'genkit';
import { GoogleAuth } from 'google-auth-library';
import { google } from 'googleapis';
import { createInterface } from 'node:readline/promises';
import { initAgents } from './agents.js';

var service = google.youtube('v3');
const client = new GoogleAuth();

const genkit = initAgenkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

genkit.defineFlow('research', async () => {
  const resp = await service.search.list({
    auth: client.fromAPIKey(process.env.YOUTUBE_API_KEY!) as any,
    part: ['snippet'],
    q: 'genai agent',
    maxResults: 10,
  });
  return resp.data;
});

const gablorkenTool = genkit.defineTool(
  {
    name: 'gablorkenTool',
    description: 'use when need to calculate a gablorken',
    inputSchema: z.object({
      value: z.number(),
    }),
    outputSchema: z.number(),
  },
  async (input) => {
    return Math.pow(input.value, 3) + 1.407;
  }
);

const ai = initAgents(genkit);

ai.defineInterrupt({
  name: 'pewpew',
  description: 'can be used to calculate pewpew value',
  inputSchema: z.object({
    value: z.number(),
  }),
});

const infoAgent = ai.defineAgent({
  name: 'infoAgent',
  description: `This agent helps with answering inquiries and requests.`,
  tools: ['attendanceAgent', gablorkenTool, 'pewpew'],
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
`,
});

const attendanceAgent = ai.defineAgent({
  name: `attendanceAgent`,
  description: `Transfer to this agent when the user asks about attendance. Do not mention that you are transferring, just do it.`,
  tools: ['infoAgent'],
  instructions: `
You are Bell, a helpful attendance assistance agent for Sparkyville High School. 
A parent has been referred to you to handle a attendance related concern. 
Use the tools available to you to assist the parent.

- Parents may only report absences for their own students.
- If you are unclear about any of the fields required to report an absence or tardy, request clarification before using the tool.
- If the parent asks about anything other than attendance-related concerns that you can handle, transfer to the info agent.
  `,
});

const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

async () => {
  const session = ai.startSession({
    agent: infoAgent,
  });

  while (true) {
    const input = await rl.question('say: ');
    const { text, messages } = await session.send(input);
    console.log(' = = = = = = = = = ');
    console.log(text);
    console.log(' = = = = = = = = = ');
    console.log(' - - - - - - -  - - - -  - - - -- - -');
    messages.forEach((m) => {
      console.log(m.role + ': ' + m.content.map((c) => c.text).join(' '));
    });
    console.log(' - - - - - - -  - - - -  - - - -- - -');
  }
};

(async () => {
  const session = ai.startSession({
    agent: infoAgent,
  });
  let resp = await session.send('what a pewpew of 26');
  console.log(' - - - - -', JSON.stringify(resp.finishReason, undefined, 2));

  resp = await session.resume({value: 88});
  console.log(resp.text);
})();

const escalate = ai.defineInterrupt({
  name: 'escalate',
  description: 'use this agent when user inquiry does not fall into predefined categories',
  inputSchema: z.object({
    inquirySummary: z.string().describe("brief summary of the user's request"),
  }),
});

ai.defineAgent({
  name: 'supportTriageAgent',
  description: 'triages incoming requests and transfers to an appropriate specialist',
  instructions: '{{ role "system" }} triage user request and call the specialized tool',
  tools: [refundAgent, generalInquiryAgent, escalate],
  toolChoice: 'required',
})