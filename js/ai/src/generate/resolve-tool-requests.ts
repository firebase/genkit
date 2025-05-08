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
  GenerateResponseData,
  MessageData,
  Part,
  ToolRequestPart,
  ToolResponsePart,
} from '../model.js';
import { isPromptAction } from '../prompt.js';
import {
  ToolAction,
  ToolInterruptError,
  ToolRunOptions,
  isToolRequest,
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
    if (
      e instanceof ToolInterruptError ||
      // There's an inexplicable case when the above type check fails, only in tests.
      (e as Error).name === 'ToolInterruptError'
    ) {
      const ie = e as ToolInterruptError;
      logger.debug(
        `tool '${toolMap[part.toolRequest?.name].__action.name}' triggered an interrupt${ie.metadata ? `: ${JSON.stringify(ie.metadata)}` : ''}`
      );
      const interrupt = {
        toolRequest: part.toolRequest,
        metadata: { ...part.metadata, interrupt: ie.metadata || true },
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

function findCorrespondingToolRequest(
  parts: Part[],
  part: ToolRequestPart | ToolResponsePart
): ToolRequestPart | undefined {
  const name = part.toolRequest?.name || part.toolResponse?.name;
  const ref = part.toolRequest?.ref || part.toolResponse?.ref;

  return parts.find(
    (p) => p.toolRequest?.name === name && p.toolRequest?.ref === ref
  ) as ToolRequestPart | undefined;
}

function findCorrespondingToolResponse(
  parts: Part[],
  part: ToolRequestPart | ToolResponsePart
): ToolResponsePart | undefined {
  const name = part.toolRequest?.name || part.toolResponse?.name;
  const ref = part.toolRequest?.ref || part.toolResponse?.ref;

  return parts.find(
    (p) => p.toolResponse?.name === name && p.toolResponse?.ref === ref
  ) as ToolResponsePart | undefined;
}

async function resolveResumedToolRequest(
  rawRequest: GenerateActionOptions,
  part: ToolRequestPart,
  toolMap: Record<string, ToolAction>
): Promise<{
  toolRequest?: ToolRequestPart;
  toolResponse?: ToolResponsePart;
  interrupt?: ToolRequestPart;
}> {
  if (part.metadata?.pendingOutput) {
    const { pendingOutput, ...metadata } = part.metadata;
    const toolResponse = {
      toolResponse: {
        name: part.toolRequest.name,
        ref: part.toolRequest.ref,
        output: pendingOutput,
      },
      metadata: { ...metadata, source: 'pending' },
    };

    // strip pendingOutput from metadata when returning
    return stripUndefinedProps({
      toolResponse,
      toolRequest: { ...part, metadata },
    });
  }

  // if there's a corresponding reply, append it to toolResponses
  const providedResponse = findCorrespondingToolResponse(
    rawRequest.resume?.respond || [],
    part
  );
  if (providedResponse) {
    const toolResponse = providedResponse;

    // remove the 'interrupt' but leave a 'resolvedInterrupt'
    const { interrupt, ...metadata } = part.metadata || {};
    return stripUndefinedProps({
      toolResponse,
      toolRequest: {
        ...part,
        metadata: { ...metadata, resolvedInterrupt: interrupt },
      },
    });
  }

  // if there's a corresponding restart, execute then add to toolResponses
  const restartRequest = findCorrespondingToolRequest(
    rawRequest.resume?.restart || [],
    part
  );
  if (restartRequest) {
    const { response, interrupt, preamble } = await resolveToolRequest(
      rawRequest,
      restartRequest,
      toolMap
    );

    if (preamble) {
      throw new GenkitError({
        status: 'INTERNAL',
        message: `Prompt tool '${restartRequest.toolRequest.name}' executed inside 'restart' resolution. This should never happen.`,
      });
    }

    // if there's a new interrupt, return it
    if (interrupt) return { interrupt };

    if (response) {
      const toolResponse = response;

      // remove the 'interrupt' but leave a 'resolvedInterrupt'
      const { interrupt, ...metadata } = part.metadata || {};
      return stripUndefinedProps({
        toolResponse,
        toolRequest: {
          ...part,
          metadata: { ...metadata, resolvedInterrupt: interrupt },
        },
      });
    }
  }

  throw new GenkitError({
    status: 'INVALID_ARGUMENT',
    message: `Unresolved tool request '${part.toolRequest.name}${part.toolRequest.ref ? `#${part.toolRequest.ref}` : ''}' was not handled by the 'resume' argument. You must supply replies or restarts for all interrupted tool requests.'`,
  });
}

/** Amends message history to handle `resume` arguments. Returns the amended history. */
export async function resolveResumeOption(
  registry: Registry,
  rawRequest: GenerateActionOptions
): Promise<{
  revisedRequest?: GenerateActionOptions;
  interruptedResponse?: GenerateResponseData;
  toolMessage?: MessageData;
}> {
  if (!rawRequest.resume) return { revisedRequest: rawRequest }; // no-op if no resume option
  const toolMap = toToolMap(await resolveTools(registry, rawRequest.tools));

  const messages = rawRequest.messages;
  const lastMessage = messages.at(-1);

  if (
    !lastMessage ||
    lastMessage.role !== 'model' ||
    !lastMessage.content.find((p) => p.toolRequest)
  ) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message: `Cannot 'resume' generation unless the previous message is a model message with at least one tool request.`,
    });
  }

  const toolResponses: ToolResponsePart[] = [];
  let interrupted = false;

  lastMessage.content = await Promise.all(
    lastMessage.content.map(async (part) => {
      if (!isToolRequest(part)) return part;
      const resolved = await resolveResumedToolRequest(
        rawRequest,
        part,
        toolMap
      );
      if (resolved.interrupt) {
        interrupted = true;
        return resolved.interrupt;
      }

      toolResponses.push(resolved.toolResponse!);
      return resolved.toolRequest!;
    })
  );

  if (interrupted) {
    // TODO: figure out how to make this trigger an interrupt response.
    return {
      interruptedResponse: {
        finishReason: 'interrupted',
        finishMessage:
          'One or more tools triggered interrupts while resuming generation. The model was not called.',
        message: lastMessage,
      },
    };
  }

  const numToolRequests = lastMessage.content.filter(
    (p) => !!p.toolRequest
  ).length;
  if (toolResponses.length !== numToolRequests) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message: `Expected ${numToolRequests} tool responses but resolved to ${toolResponses.length}.`,
      detail: { toolResponses, message: lastMessage },
    });
  }

  const toolMessage: MessageData = {
    role: 'tool',
    content: toolResponses,
    metadata: {
      resumed: rawRequest.resume.metadata || true,
    },
  };

  return stripUndefinedProps({
    revisedRequest: {
      ...rawRequest,
      resume: undefined,
      messages: [...messages, toolMessage],
    },
    toolMessage,
  });
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
      const { response, interrupt } = await resolveToolRequest(
        rawRequest,
        p,
        toolMap
      );

      // this means that it interrupted *again* after the restart
      if (interrupt) return interrupt;
      return toPendingOutput(p, response!);
    })
  );
}
