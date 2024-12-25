import {
  GenerateResponse,
  GenerateResponseChunk,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  Genkit,
  MessageData,
  Part,
  Session,
  ToolAction,
  ToolArgument,
  ToolConfig,
  ToolRequestPart,
  z,
} from 'genkit';
import { Chat, ChatGenerateOptions, ChatOptions } from '../../../ai/lib/chat';
import { SessionOptions } from '../../../ai/lib/session';

export function initAgents(ai: Genkit) {
  return new Agents(ai);
}

export type AgentAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> = ToolAction<I, O> & {
  __agentOptions: DefineAgentOptions<I, O>;
};

export type InterruptAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> = ToolAction<I, O> & {
  __interruptOptions: DefineInterruptOptions<I, O>;
};

export interface DefineAgentOptions<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> {
  /** Unique name of the tool to use as a key in the registry. */
  name: string;
  /** Description of the tool. This is passed to the model to help understand what the tool is used for. */
  description: string;
  instructions?: string | Part[] | MessageData[];
  tools?: ToolArgument[];
  config?: any;
  toolChoice?: 'auto' | 'required' | 'none';
  onStart?: (messages: MessageData[]) => MessageData[];
  onFinish?: (messages: MessageData[]) => MessageData[];
}

export interface DefineInterruptOptions<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> extends ToolConfig<I, O> {}

export type StartSessionOptions<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S,
> = SessionOptions<S> & {
  agent: AgentAction<I, O>;
  input?: z.infer<I>;
};

export class Agents {
  constructor(private ai: Genkit) {}

  defineAgent<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    options: DefineAgentOptions<I, O>
  ): AgentAction<I, O> {
    const tool = this.ai.defineTool(
      {
        name: options.name,
        description: options.description,
      },
      async () => this.ai.interrupt()
    ) as AgentAction<I, O>;
    tool.__agentOptions = options;
    return tool;
  }

  defineInterrupt<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    options: DefineInterruptOptions<I, O>
  ): InterruptAction<I, O> {
    const tool = this.ai.defineTool(
      options,
      async () => this.ai.interrupt()
    ) as InterruptAction<I, O>;
    tool.__interruptOptions = options;
    return tool;
  }

  startSession<I extends z.ZodTypeAny, O extends z.ZodTypeAny, S>(
    options: StartSessionOptions<I, O, S>
  ): AgentSession<I, O, S> {
    return new AgentSession(this.ai, this.ai.createSession(options), options);
  }
}

export class AgentSession<I extends z.ZodTypeAny, O extends z.ZodTypeAny, S>
  implements Pick<Chat, 'send' | 'sendStream'>
{
  private currentThread: string;
  private currentChat: Chat;
  private currentAgent: AgentAction<any, any>;

  constructor(
    readonly ai: Genkit,
    readonly session: Session<S>,
    options: StartSessionOptions<I, O, S>
  ) {
    this.currentThread = options.agent.__action.name;
    this.currentAgent = options.agent;
    this.currentChat = this.session.chat(
      this.currentThread,
      this.renderChatOptions(options.agent, options.input, [])
    );
  }

  async resume(input: any): Promise<GenerateResponse<z.infer<O>>> {
    const interruptedAt = (this.session.sessionData?.state as any)?.[
      '__interrupted_at'
    ] as ToolRequestPart;
    if (!interruptedAt) {
      throw new Error('This session was not interrupted, so cannot be resumed');
    }
    return this.send([
      {
        toolResponse: {
          name: interruptedAt.toolRequest.name,
          ref: interruptedAt.toolRequest.ref,
          output: input,
        },
      },
    ]);
  }

  async send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    const response = await this.currentChat.send(options);
    if (response.toolRequests) {
      for (const req of response.toolRequests) {
        const tool = await this.ai.registry.lookupAction(
          `/tool/${req.toolRequest.name}`
        );
        if ((tool as AgentAction<any, any>).__agentOptions) {
          if (!this.session.sessionData!.threads) {
            this.session.sessionData!.threads = {};
          }
          if (!this.session.sessionData!.threads['main']) {
            this.session.sessionData!.threads['main'] = [];
          }
          this.session.sessionData!.threads['main'].push(
            ...this.transformExit()
          );
          const nextAgent = tool as AgentAction<any, any>;
          this.currentThread = nextAgent.__action.name;
          this.currentChat = this.session.chat(this.currentThread, {
            ...this.renderChatOptions(
              nextAgent,
              req.toolRequest.input as any,
              this.session?.sessionData?.threads?.[this.currentThread]
            ),
            messages: this.session.sessionData?.threads?.['main'] ?? [],
          });
          this.currentAgent = nextAgent;
          await this.session.updateState({
            ...this.session.state,
            __agent_currentThread: this.currentThread,
          } as any);
          return this.send(`transferred to ${this.currentThread}`);
        }
        if ((tool as InterruptAction<any, any>).__interruptOptions) {
          await this.session.updateState({
            ...this.session.state,
            __interrupted_at: req,
          } as any);
          return response;
        }
      }
    }
    return response;
  }

  private transformExit(): MessageData[] {
    if (this.currentAgent.__agentOptions.onFinish) {
      return this.currentAgent.__agentOptions.onFinish(
        this.currentChat.messages
      );
    }
    return this.currentChat.messages;
  }

  private renderChatOptions(
    agent: AgentAction<any, any>,
    input: any | undefined,
    history: MessageData[] | undefined
  ): ChatOptions {
    return {
      system: agent.__agentOptions.instructions,
      config: agent.__agentOptions.config,
      tools: agent.__agentOptions.tools,
      toolChoice: agent.__agentOptions.toolChoice,
    };
  }

  async sendStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | GenerateStreamOptions<O, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    const { response, stream } = await this.session
      .chat(this.currentThread)
      .sendStream(options);

    let enqueuer: ReadableStreamDefaultController<any>;
    let readableStream = new ReadableStream({
      start(controller) {
        enqueuer = controller;
      },
    });

    async function* chunkStream(): AsyncIterable<GenerateResponseChunk> {
      const reader = readableStream.getReader();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        yield value;
      }
    }

    return {
      response,
      get stream() {
        return chunkStream();
      },
    };
  }
}
