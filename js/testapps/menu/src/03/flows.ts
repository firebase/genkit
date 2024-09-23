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

import { geminiPro } from '@genkit-ai/vertexai';
import { generate } from 'genkit/ai';
import { run } from 'genkit/flow';
import { MessageData } from 'genkit/model';
import { ai } from '../index.js';

import {
  ChatHistoryStore,
  ChatSessionInputSchema,
  ChatSessionOutputSchema,
} from './chats.js';
import { s03_chatPreamblePrompt } from './prompts.js';

// Load the menu data from a JSON file.
import menuData from '../../data/menu.json' assert { type: 'json' };

// Render the preamble prompt that seeds our chat history.
const preamble: Array<MessageData> = s03_chatPreamblePrompt.renderMessages({
  menuData: menuData,
  question: '',
});

// A simple local storage for chat session history.
// You should probably actually use Firestore for this.
const chatHistoryStore = new ChatHistoryStore(preamble);

// Define a flow which generates a response to each question.

export const s03_multiTurnChatFlow = ai.defineFlow(
  {
    name: 's03_multiTurnChat',
    inputSchema: ChatSessionInputSchema,
    outputSchema: ChatSessionOutputSchema,
  },
  async (input) => {
    // First fetch the chat history. We'll wrap this in a run block.
    // If we were going to a database for the history,
    // we might want to have that db result captured in the trace.
    let history = await run('fetchHistory', async () =>
      chatHistoryStore.read(input.sessionId)
    );

    // Generate the response
    const llmResponse = await generate({
      model: geminiPro,
      history: history,
      prompt: {
        text: input.question,
      },
    });

    // Add the exchange to the history store and return it
    history = llmResponse.toHistory();
    chatHistoryStore.write(input.sessionId, history);
    return {
      sessionId: input.sessionId,
      history: history,
    };
  }
);
