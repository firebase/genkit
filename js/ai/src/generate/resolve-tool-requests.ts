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

import { GenkitError, stripUndefinedProps } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import {
  GenerateActionOptions,
  MessageData,
  ToolRequestPart,
  ToolResponsePart,
} from '../model.js';
import { isPromptAction } from '../prompt.js';
import {
  ToolAction,
  ToolInterruptError,
  ToolRunOptions,
  resolveTools,
} from '../tool.js';

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

function toRunOptions(part: ToolRequestPart): ToolRunOptions {
  const out: ToolRunOptions = { metadata: part.metadata };
  if (part.metadata?.resumed) out.resumed = part.metadata.resumed;
  return out;
}

export function toPendingOutput(
  part: ToolRequestPart,
  response: ToolResponsePart
): ToolRequestPart {
  return {
    ...part,
    metadata: {
      ...part.metadata,
      pendingOutput: response.toolResponse.output,
    },
  };
}

export async function resolveToolRequest(
  rawRequest: GenerateActionOptions,
  part: ToolRequestPart,
  toolMap: Record<string, ToolAction>,
  runOptions?: ToolRunOptions
): Promise<{
  response?: ToolResponsePart;
  interrupt?: ToolRequestPart;
  preamble?: GenerateActionOptions;
}> {
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
    const preamble = await tool(part.toolRequest.input);
    const response = {
      toolResponse: {
        name: part.toolRequest.name,
        ref: part.toolRequest.ref,
        output: `transferred to ${part.toolRequest.name}`,
      },
    };

    return { preamble, response };
  }

  // otherwise, execute the tool and catch interrupts
  try {
    const output = await tool(part.toolRequest.input, toRunOptions(part));
    const response = stripUndefinedProps({
      toolResponse: {
        name: part.toolRequest.name,
        ref: part.toolRequest.ref,
        output,
      },
    });

    return { response };
  } catch (e) {
    if (e instanceof ToolInterruptError) {
      logger.debug(
        `tool '${toolMap[part.toolRequest?.name].__action.name}' triggered an interrupt${e.metadata ? `: ${JSON.stringify(e.metadata)}` : ''}`
      );
      const interrupt = {
        toolRequest: part.toolRequest,
        metadata: { ...part.metadata, interrupt: e.metadata || true },
      };

      return { interrupt };
    }

    throw e;
  }
}

/**
 * resolveToolRequests is responsible for executing the tools requested by the model for a single turn. it
 * returns either a toolMessage to append or a revisedModelMessage when an interrupt occurs, and a transferPreamble
 * if a prompt tool is called
 */
export async function resolveToolRequests(
  registry: Registry,
  rawRequest: GenerateActionOptions,
  generatedMessage: MessageData
): Promise<{
  revisedModelMessage?: MessageData;
  toolMessage?: MessageData;
  transferPreamble?: GenerateActionOptions;
}> {
  const toolMap = toToolMap(await resolveTools(registry, rawRequest.tools));

  const responseParts: ToolResponsePart[] = [];
  let hasInterrupts: boolean = false;
  let transferPreamble: GenerateActionOptions | undefined;

  const revisedModelMessage = {
    ...generatedMessage,
    content: [...generatedMessage.content],
  };

  await Promise.all(
    revisedModelMessage.content.map(async (part, i) => {
      if (!part.toolRequest) return; // skip non-tool-request parts

      const { preamble, response, interrupt } = await resolveToolRequest(
        rawRequest,
        part as ToolRequestPart,
        toolMap
      );

      if (preamble) {
        if (transferPreamble) {
          throw new GenkitError({
            status: 'INVALID_ARGUMENT',
            message: `Model attempted to transfer to multiple prompt tools.`,
          });
        }

        transferPreamble = preamble;
      }

      // this happens for preamble or normal tools
      if (response) {
        responseParts.push(response!);
        revisedModelMessage.content.splice(
          i,
          1,
          toPendingOutput(part, response)
        );
      }

      if (interrupt) {
        revisedModelMessage.content.splice(i, 1, interrupt);
        hasInterrupts = true;
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

export async function resolveRestartedTools(
  registry: Registry,
  rawRequest: GenerateActionOptions
): Promise<ToolRequestPart[]> {
  const toolMap = toToolMap(await resolveTools(registry, rawRequest.tools));
  const lastMessage = rawRequest.messages.at(-1);
  if (!lastMessage || lastMessage.role !== 'model') return [];

  const restarts = lastMessage.content.filter(
    (p) => p.toolRequest && p.metadata?.resumed
  ) as ToolRequestPart[];

  return await Promise.all(
    restarts.map(async (p) => {
      const { response, interrupt, preamble } = await resolveToolRequest(
        rawRequest,
        p,
        toolMap
      );
      if (preamble) {
        throw new GenkitError({
          status: 'INTERNAL',
          message: `Prompt tool '${p.toolRequest.name}' executed inside restart resolution. This should never happen.`,
        });
      }

      // this means that it interrupted *again* after the restart
      if (interrupt) return interrupt;
      return toPendingOutput(p, response!);
    })
  );
}
