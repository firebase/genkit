import { defineTool, generate } from '@genkit-ai/ai';
import { MessageData } from '@genkit-ai/ai/model';
import { defineFlow } from '@genkit-ai/flow';
import { gemini15ProPreview } from '@genkit-ai/vertexai';
import { z } from 'zod';

const chatHistory: Record<string, MessageData[]> = {};

const InputSchema = z.object({
  id: z.string(),
  text: z.string().optional(),
  toolResponse: z
    .object({
      name: z.string(),
      ref: z.string().optional(),
      output: z.unknown().optional(),
    })
    .optional(),
});

const OutputSchema = z.object({
  text: z.string().optional(),
  toolRequest: z
    .object({
      name: z.string(),
      ref: z.string().optional(),
      input: z.unknown().optional(),
    })
    .optional(),
});

const weatherTool = defineTool(
  {
    name: 'weatherTool',
    description: 'use this tool to display weather',
    inputSchema: z.object({
      date: z.string().describe('date (use datePicker tool if user did not specify)'),
      location: z.string().describe('location (ZIP, city, etc.)',
    )}),
    outputSchema: z.string().optional(),
  },
  async () => undefined
);

const datePicker = defineTool(
  {
    name: 'datePicker',
    description: 'user can use this UI tool to enter a date (prefer this over asking the user to enter the date manually)',
    inputSchema: z.object({ignore: z.string().describe('ignore this (set to undefined)').optional()}),
    outputSchema: z.string().optional(),
  },
  async () => undefined
);

export const chatbotFlow = defineFlow(
  {
    name: 'chatbotFlow',
    inputSchema: InputSchema,
    outputSchema: OutputSchema,
    streamSchema: OutputSchema
  },
  async (input, streamingCallback) => {
    let prompt = input.text
      ? input.text
      : input.toolResponse
        ? { toolResponse: input.toolResponse }
        : undefined;
    if (!prompt) {
      throw 'prompt missing';
    }
    const history = await loadChatState(input.id);
    let toolCallSent = false;
    const resp = await generate({
      prompt,
      history,
      model: gemini15ProPreview,
      tools: [weatherTool, datePicker],
      returnToolRequests: true,
      streamingCallback: (chunk) => {
        if (!streamingCallback) return;
        if (!toolCallSent) {
          if (chunk.toolRequests().length > 0) {
            toolCallSent = true;
            streamingCallback({
              toolRequest: chunk.toolRequests()[0].toolRequest
            });
          } else if (chunk.text()) {
            streamingCallback({
              text: chunk.text()
            });
          }
        }
      },
    });
    await saveChatState(input.id, resp.toHistory());
    return resp.text()
      ? { text: resp.text() }
      : { toolRequest: resp.toolRequests()[0].toolRequest };
  }
);

async function loadChatState(id: string): Promise<MessageData[] | undefined> {
  if (!chatHistory[id]) {
    return [
      {
        role: 'system',
        content: [
          {
            text:
              'You are a helpful, chatty agent. There are tools/functions at your disposal, ' +
              'feel free to call them. If you think a tool/function can help but you do ' +
              'not have sufficient context feel free to ask clarifying questions.',
          },
        ],
      },
    ];
  }
  return chatHistory[id];
}

async function saveChatState(id: string, history: MessageData[]) {
  chatHistory[id] = history;
}
