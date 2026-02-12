/**
 * Copyright 2026 Google LLC
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

import { googleAI } from '@genkit-ai/google-genai';
import {
  GenerateResponse,
  genkit,
  MessageData,
  ResumeOptions,
  ToolRequestPart,
} from 'genkit';
import * as path from 'path';
import * as readline from 'readline';
import {
  fallback,
  filesystem,
  retry,
  skills,
  toolApproval,
} from '../src/index.js';

const ai = genkit({
  plugins: [googleAI()],
});

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function ask(question: string): Promise<string> {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function main() {
  const skillsDir = path.resolve(__dirname, 'skills');
  const workspaceDir = path.resolve(__dirname, 'workspace');

  console.log('--- Coding Agent ---');
  console.log('Type your request. To exit, type "exit".');

  const messages: MessageData[] = [
    {
      role: 'system',
      content: [
        {
          text:
            'You are a helpful coding agent. Very terse but thoughful and careful.' +
            `Your working directory is in ${workspaceDir}, you are not allowed to access anything outside it.\n
        Use skills. ALWAYS start by analyzing the current state of the workspace, there might be something already there.`,
        },
      ],
    },
  ];

  while (true) {
    const input = await ask('\n> ');
    if (input.trim().toLowerCase() === 'exit') {
      break;
    }

    try {
      let resume: ResumeOptions | undefined = undefined;
      let currentMessages = messages;
      let response: GenerateResponse;

      while (true) {
        response = await ai.generate({
          model: googleAI.model('gemini-3-pro-preview'),
          prompt: resume ? undefined : input,
          messages: currentMessages,
          use: [
            toolApproval({ approved: ['read_file', 'list_files'] }),
            skills({ skillsDirectory: skillsDir }),
            filesystem({ rootDirectory: workspaceDir }),
            retry({ maxRetries: 2 }),
            fallback({
              models: [googleAI.model('gemini-3-flash-preview')],
            }),
          ],
          resume,
        });

        if (response.finishReason !== 'interrupted') {
          break;
        }

        if (!response.interrupts || response.interrupts.length === 0) {
          console.error('Interrupted but no interrupt record found.');
          break;
        }

        const approvedInterrupts: ToolRequestPart[] = [];
        for (const interrupt of response.interrupts) {
          console.log('\n*** Tool Approval Required ***');
          console.log('Tool:', interrupt.toolRequest?.name);
          console.log(
            'Input:',
            JSON.stringify(interrupt.toolRequest?.input, null, 2)
          );

          const approval = await ask('Approve? (y/N): ');
          if (approval.toLowerCase() === 'y') {
            interrupt.metadata = {
              ...interrupt.metadata,
              'tool-approved': true,
            };
            approvedInterrupts.push(interrupt);
          }
        }

        if (approvedInterrupts.length > 0) {
          console.log('Resuming...');
          resume = { restart: approvedInterrupts };
          currentMessages = response.messages;
        } else {
          console.log('Tool denied.');
          break;
        }
      }

      console.log('\nAI Response:\n' + response.text);

      if (response.messages) {
        messages.length = 0;
        messages.push(...response.messages);
      }
    } catch (e: any) {
      console.error('Error during generation:', e.message);
    }
  }

  rl.close();
}

main().catch(console.error);
