/**
 * Copyright 2025 Google LLC
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

import { GenkitError, stripUndefinedProps, z } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { MessageData, ToolRequestPart, ToolResponsePart } from '../model.js';
import { isPromptAction } from '../prompt.js';
import { ToolAction, ToolInterruptError, resolveTools } from '../tool.js';
import { GenerateUtilParamSchema } from './action.js';

export function toToolMap(tools: ToolAction[]): Record<string, ToolAction> {
  assertValidToolNames(tools);
  const out: Record<string, ToolAction> = {};
  for (const tool of tools) {
    const name = tool.__action.name;
    const shortName = name.substring(name.lastIndexOf('/') + 1);
    out[shortName] = tool;
  }
  return out;
}

/** Ensures that each tool has a unique name. */
export function assertValidToolNames(tools: ToolAction[]) {
  const nameMap: Record<string, string> = {};
  for (const tool of tools) {
    const name = tool.__action.name;
    const shortName = name.substring(name.lastIndexOf('/') + 1);
    if (nameMap[shortName]) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `Cannot provide two tools with the same name: '${name}' and '${nameMap[shortName]}'`,
      });
    }
    nameMap[shortName] = name;
  }
}

/**
 * resolveToolRequests is responsible for executing the tools requested by the model for a single turn. it
 * returns either a toolMessage to append or a revisedModelMessage when an interrupt occurs, and a transferPreamble
 * if a prompt tool is called
 */
export async function resolveToolRequests(
  registry: Registry,
  rawRequest: z.infer<typeof GenerateUtilParamSchema>,
  generatedMessage: MessageData
): Promise<{
  revisedModelMessage?: MessageData;
  toolMessage?: MessageData;
  transferPreamble?: z.infer<typeof GenerateUtilParamSchema>;
}> {
  const toolMap = toToolMap(await resolveTools(registry, rawRequest.tools));
  const toolRequests = generatedMessage.content.filter(
    (p) => !!p.toolRequest
  ) as ToolRequestPart[];

  const responseParts: ToolResponsePart[] = [];
  let hasInterrupts: boolean = false;
  let transferPreamble: z.infer<typeof GenerateUtilParamSchema> | undefined;

  const revisedModelMessage = {
    ...generatedMessage,
    content: [...generatedMessage.content],
  };

  await Promise.all(
    toolRequests.map(async (part, i) => {
      const tool = toolMap[part.toolRequest.name];
      if (!tool) {
        throw new GenkitError({
          status: 'NOT_FOUND',
          message: `Tool ${part.toolRequest.name} not found`,
          detail: { request: rawRequest },
        });
      }

      // if it's a prompt action, go ahead and render the preamble
      if (isPromptAction(tool)) {
        if (transferPreamble)
          throw new GenkitError({
            status: 'INVALID_ARGUMENT',
            message: `Model attempted to transfer to multiple prompt tools.`,
          });
        transferPreamble = await tool(part.toolRequest.input);
        responseParts.push({
          toolResponse: {
            name: part.toolRequest.name,
            ref: part.toolRequest.ref,
            output: `transferring to ${part.toolRequest.name}`,
          },
        });
        return;
      }

      // otherwise, execute the tool and catch interrupts
      try {
        const output = await tool(part.toolRequest.input, {});
        const responsePart = stripUndefinedProps({
          toolResponse: {
            name: part.toolRequest.name,
            ref: part.toolRequest.ref,
            output,
          },
        });
        revisedModelMessage.content.splice(i, 1, {
          ...part,
          metadata: { ...part.metadata, pendingToolResponse: responsePart },
        });
        responseParts.push(responsePart);
      } catch (e) {
        if (e instanceof ToolInterruptError) {
          logger.debug(
            `tool '${toolMap[part.toolRequest?.name].__action.name}' triggered an interrupt${e.metadata ? `: ${JSON.stringify(e.metadata)}` : ''}`
          );
          revisedModelMessage.content.splice(i, 1, {
            toolRequest: part.toolRequest,
            metadata: { ...part.metadata, interrupt: e.metadata || true },
          });
          hasInterrupts = true;
          return;
        }

        throw e;
      }
    })
  );

  if (hasInterrupts) {
    return { revisedModelMessage };
  }

  return {
    toolMessage: { role: 'tool', content: responseParts },
    transferPreamble,
  };
}
