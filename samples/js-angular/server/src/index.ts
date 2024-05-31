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

import {
  GenerateOptions,
  GenerateResponse,
  ToolAction,
  defineTool,
  generate,
  generateStream,
} from '@genkit-ai/ai';
import { MessageData } from '@genkit-ai/ai/model';
import { StreamingCallback, configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import { gemini15ProPreview, vertexAI } from '@genkit-ai/vertexai';
import { Allow, parse } from 'partial-json';
import * as z from 'zod';

configureGenkit({
  plugins: [vertexAI()],
  logLevel: 'error',
  enableTracingAndMetrics: true,
});

const GameCharactersSchema = z.object({
  characters: z
    .array(
      z
        .object({
          name: z.string().describe('Name of a character'),
          abilities: z
            .array(z.string())
            .describe('Various abilities (strength, magic, archery, etc.)'),
        })
        .describe('Game character')
    )
    .describe('Characters'),
});

export const streamCharacters = defineFlow(
  {
    name: 'streamCharacters',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: GameCharactersSchema,
  },
  async (count, streamingCallback) => {
    if (!streamingCallback) {
      throw new Error('this flow only works in streaming mode');
    }

    const { response, stream } = await generateStream({
      model: gemini15ProPreview,
      output: {
        schema: GameCharactersSchema,
      },
      config: {
        temperature: 1,
      },
      prompt: `Respond as JSON only. Generate ${count} different RPG game characters.`,
    });

    let buffer = '';
    for await (const chunk of stream()) {
      buffer += chunk.content[0].text!;
      if (buffer.length > 10) {
        streamingCallback(parse(maybeStripMarkdown(buffer), Allow.ALL));
      }
    }

    return (await response()).text();
  }
);

const jokeSubjectGenerator = defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'this tool can be called to generate a subject for a joke',
    inputSchema: z.object({ dummy: z.string() }),
    outputSchema: z.object({ subject: z.string() }),
  },
  async () => {
    return { subject: 'banana' };
  }
);

export const toolCaller = defineFlow(
  {
    name: 'toolCaller',
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

const markdownRegex = /^\s*(```json)?((.|\n)*?)(```)?\s*$/i;
function maybeStripMarkdown(withMarkdown: string) {
  const mdMatch = markdownRegex.exec(withMarkdown);
  if (!mdMatch) {
    return withMarkdown;
  }
  return mdMatch[2];
}

startFlowsServer();
