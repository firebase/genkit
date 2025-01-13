import { Action, z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { MessageData, Part } from './model';
import { ToolAction, ToolArgument, defineTool, interruptTool } from './tool';

export interface DefineAgentOptions<
  I extends z.ZodTypeAny
> {
  /** Unique name of the tool to use as a key in the registry. */
  name: string;
  /** Description of the tool. This is passed to the model to help understand what the tool is used for. */
  description: string;
  instructions: string | Part | Part[];
  inputSchema?: I,
  tools?: ToolArgument[];
  config?: any;
  toolChoice?: 'auto' | 'required' | 'none';
  onStart?: (messages: MessageData[]) => MessageData[];
  onFinish?: (messages: MessageData[]) => MessageData[];
}

export type AgentAction<
  I extends z.ZodTypeAny,
> = ToolAction<I, z.ZodVoid> & {
  __agentOptions: DefineAgentOptions<I>;
  __agentType: 'tool' | 'chat';
};

export function defineAgent<I extends z.ZodTypeAny>(
  registry: Registry,
  options: DefineAgentOptions<I>
): AgentAction<I> {
  const tool = defineTool(
    registry,
    {
      name: options.name,
      description: options.description,
      metadata: agentMetadata(options),
    },
    async () => interruptTool()
  ) as AgentAction<I>;
  tool.__agentOptions = options;
  tool.__agentType = 'tool';
  return tool;
}

export function defineChatAgent<I extends z.ZodTypeAny>(
  registry: Registry,
  options: DefineAgentOptions<I>
): AgentAction<I> {
  const tool = defineTool(
    registry,
    {
      name: options.name,
      description: options.description,
      metadata: agentMetadata(options),
    },
    async () => interruptTool()
  ) as AgentAction<I>;
  tool.__agentOptions = options;
  tool.__agentType = 'chat';
  return tool;
}

function agentMetadata<I extends z.ZodTypeAny>(
  options: DefineAgentOptions<I>
): Record<string, any> {
  return {
    agentMetadata: {
      name: options.name,
      instructions: options.instructions,
      description: options.description,
      toolChoice: options.toolChoice,
      tools: options?.tools?.map((t) => {
        if (typeof t === 'string') {
          return t;
        }
        if ((t as Action).__action) {
          return (t as Action).__action.name;
        }
        throw 'unsupported tool type';
      }),
      config: options.config,
    },
  };
}
