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

import { googleAI } from '@genkit-ai/googleai';
import { createMcpManager } from '@genkit-ai/mcp';
import { genkit, z } from 'genkit';
import { logger } from 'genkit/logging';

// Turn off safety checks for evaluation so that the LLM as an evaluator can
// respond appropriately to potentially harmful content without error.
export const PERMISSIVE_SAFETY_SETTINGS: any = {
  safetySettings: [
    {
      category: 'HARM_CATEGORY_HATE_SPEECH',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_HARASSMENT',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
      threshold: 'BLOCK_NONE',
    },
  ],
};

export const ai = genkit({
  plugins: [googleAI()],
});

logger.setLogLevel('debug'); // Set the logging level to debug for detailed output

export const clientManager = createMcpManager({
  name: 'test-mcp-manager',
  mcpServers: {
    'git-client': {
      command: 'uvx',
      args: ['mcp-server-git'],
    },
  },
});

ai.defineFlow('ask', async () => {
  const { text } = await ai.generate({
    model: googleAI.model('gemini-2.5-pro-preview-03-25'),
    prompt: 'summarize last 5 commits in `/Users/pavelj/genkit/genkit/`',
    tools: await clientManager.getActiveTools(ai),
  });

  console.log(text);
});

// MCP Controls
export const controlMcp = ai.defineFlow(
  {
    name: 'controlMcp',
    inputSchema: z.object({
      action: z.enum([
        'RECONNECT',
        'REENABLE',
        'DISABLE',
        'DISCONNECT',
      ] as const),
      clientId: z.string().optional(),
    }),
    outputSchema: z.string(),
  },
  async ({ action, clientId }) => {
    const id = clientId ?? 'git-client';
    switch (action) {
      case 'DISABLE':
        await clientManager.disable(id);
        break;
      case 'DISCONNECT':
        await clientManager.disconnect(id);
        break;
      case 'RECONNECT':
        await clientManager.reconnect(id);
        break;
      case 'REENABLE':
        await clientManager.reenable(id);
        break;
    }
    return action;
  }
);
