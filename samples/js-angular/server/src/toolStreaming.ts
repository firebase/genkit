import {
  GenerateOptions,
  GenerateResponse,
  ToolAction,
  defineTool,
  generate
} from '@genkit-ai/ai';
import { MessageData } from '@genkit-ai/ai/model';
import { StreamingCallback } from '@genkit-ai/core';
import { defineFlow } from '@genkit-ai/flow';
import { gemini15ProPreview } from '@genkit-ai/vertexai';
import * as z from 'zod';

const jokeSubjectGenerator = defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'this tool can be called to generate a subject for a joke',
    inputSchema: z.object({ dummy: z.string() }),
    outputSchema: z.object({ subject: z.string() }),
  },
  async () => {
    await new Promise((r) => setTimeout(r, 2000));
    return { subject: 'banana' };
  }
);

export const streamToolCalling = defineFlow(
  {
    name: 'streamToolCalling',
    outputSchema: z.string(),
  },
  async (_, streamingCallback) => {
    let history: MessageData[] = [
      {
        role: 'system',
        content: [
          {
            text: 'use the available tools if you need to, for example as joke subject',
          },
        ],
      },
    ];

    const tools: Record<string, ToolAction> = {
      jokeSubjectGenerator,
    };

    let prompt: GenerateOptions['prompt'] = `tell me a joke`;
    let iteration = 0;
    while (true) {
      const response: GenerateResponse = await generate({
        model: gemini15ProPreview,
        tools: Object.values(tools),
        prompt,
        returnToolRequests: true,
        history,
        streamingCallback: wrapModelStream(
          `model call ${iteration}`,
          streamingCallback
        ),
      });
      history = response.toHistory();
      if (response.toolRequests().length > 0) {
        const toolRequest = response.toolRequests()[0].toolRequest;
        if (!tools[toolRequest.name]) {
          throw new Error(`unknown tool toolRequest.name`);
        }
        const tool = tools[toolRequest.name];
        if (streamingCallback) {
          streamingCallback({ label: `tool ${toolRequest.name}`, toolRequest });
        }
        const toolResponse = await tool(toolRequest.input);
        if (streamingCallback) {
          streamingCallback({
            label: `tool ${toolRequest.name}`,
            toolRequest,
            toolResponse,
          });
        }
        prompt = {
          toolResponse: {
            name: toolRequest.name,
            ref: toolRequest.ref,
            output: toolResponse,
          },
        };
      } else {
        return response.text();
      }
      iteration++;
    }
  }
);

function wrapModelStream(
  label: string,
  streamingCallback: StreamingCallback<any> | undefined
): StreamingCallback<any> | undefined {
  if (!streamingCallback) return undefined;
  return (data: any) => streamingCallback({ label, llmChunk: data });
}
