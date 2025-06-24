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

import type { Message, ToolRequestPart } from 'genkit';
import { createInterface } from 'node:readline';
import { ai } from './genkit.js';
import { routingAgent } from './routingAgent.js';

const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

const EXAMPLE_USER_CONTEXT = {
  parentId: 4112,
  parentName: 'Francis Smith',
  students: [
    {
      id: 3734,
      name: 'Evelyn Smith',
      grade: 9,
      activities: ['Choir', 'Drama Club'],
    },
    { id: 9433, name: 'Evan Smith', grade: 11, activities: ['Chess Club'] },
  ],
};

// ANSI color codes for terminal output
const COLORS = {
  BELL: '\x1b[33m',
  PROMPT: '\x1b[36m',
  RESET: '\x1b[0m',
};

// Helper to print colored text
function printColored(prefix: string, text: string, color: string) {
  console.log(`${color}${prefix}>${COLORS.RESET}`, text);
}

// Get initial greeting from AI
async function getGreeting() {
  const { text } = await ai.generate(
    'Come up with a short friendly greeting for yourself talking to a parent as Bell, the helpful AI assistant for parents of Sparkyville High School. Feel free to use emoji.'
  );
  return text;
}

// Process and display the chat response stream
async function handleChatResponse(
  stream: AsyncIterable<{ text: string }>,
  response: Promise<any>,
  startMessageCount: number
) {
  console.log();
  process.stdout.write(`${COLORS.BELL}bell>${COLORS.RESET} `);

  for await (const chunk of stream) {
    process.stdout.write(chunk.text);
  }

  // Extract and display tools used
  const toolsUsed = (await response).messages
    .slice(startMessageCount)
    .filter((m: Message) => m.role === 'model')
    .flatMap((m: Message) =>
      m.content
        .filter((p) => !!p.toolRequest)
        .map(
          (p) =>
            `${p.toolRequest?.name}(${JSON.stringify(p.toolRequest?.input)})`
        )
    )
    .filter((t: ToolRequestPart) => !!t);

  console.log('\nTools Used:', toolsUsed);
}

// Main chat loop
async function handleUserInput(chat: any): Promise<void> {
  return new Promise((resolve) => {
    rl.question(`\n${COLORS.PROMPT}prompt>${COLORS.RESET} `, async (input) => {
      try {
        const startMessageCount = chat.messages.length;
        const { stream, response } = await chat.sendStream(input);
        await handleChatResponse(stream, response, startMessageCount);
        resolve();
      } catch (e) {
        console.log('Error:', e);
        resolve();
      }
    });
  });
}

async function main() {
  const chat = ai
    .createSession({ initialState: EXAMPLE_USER_CONTEXT })
    .chat(routingAgent);

  const greeting = await getGreeting();
  console.log();
  printColored('bell', greeting, COLORS.BELL);

  while (true) {
    await handleUserInput(chat);
  }
}

setTimeout(main, 0);
