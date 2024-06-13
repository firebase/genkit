import { defineTool } from '@genkit-ai/ai';
import { MessageData } from '@genkit-ai/ai/model';
import { gemini15FlashPreview } from '@genkit-ai/vertexai';
import { z } from 'zod';
import { HistoryStore, defineAgent } from './agent';

const weatherTool = defineTool(
  {
    name: 'weatherTool',
    description: 'use this tool to display weather',
    inputSchema: z.object({
      date: z
        .string()
        .describe('date (use datePicker tool if user did not specify)'),
      location: z.string().describe('location (ZIP, city, etc.)'),
    }),
    outputSchema: z.string().optional(),
  },
  async () => undefined
);

const datePicker = defineTool(
  {
    name: 'datePicker',
    description:
      'user can use this UI tool to enter a date (prefer this over asking the user to enter the date manually)',
    inputSchema: z.object({
      ignore: z.string().describe('ignore this (set to undefined)').optional(),
    }),
    outputSchema: z.string().optional(),
  },
  async () => undefined
);

export const chatbotFlow = defineAgent({
  name: 'chatbotFlow',
  model: gemini15FlashPreview,
  tools: [weatherTool, datePicker],
  returnToolRequests: true,
  systemPrompt:
    'You are a helpful agent. You have the personality of Agent Smith from Matrix. ' +
    'There are tools/functions at your disposal, ' +
    'feel free to call them. If you think a tool/function can help but you do ' +
    'not have sufficient context make sure to ask clarifying questions.',
  historyStore: inMemoryStore(),
});


const chatHistory: Record<string, MessageData[]> = {};

function inMemoryStore(): HistoryStore {
  return {
    async load(id: string): Promise<MessageData[] | undefined> {
      return chatHistory[id];
    },
    async save(id: string, history: MessageData[]) {
      chatHistory[id] = history;
    },
  };
}
