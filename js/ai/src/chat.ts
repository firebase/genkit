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

import { StreamingCallback, z } from '@genkit-ai/core';
import { runInNewSpan } from '@genkit-ai/core/tracing';
import { AgentAction } from './agent.js';
import {
  GenerateOptions,
  GenerateResponse,
  GenerateResponseChunk,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  MessageData,
  Part,
  generate,
  generateStream,
  tagAsPreamble,
} from './index.js';
import {
  AgentState,
  AgentThreadsSessionState,
  BaseGenerateOptions,
  Session,
  SessionData,
  SessionStore,
  runWithSession,
} from './session.js';
import { InterruptAction } from './tool.js';

export const MAIN_THREAD = 'main';

export type ChatGenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = GenerateOptions<O, CustomOptions> & {
  agent?: AgentAction<z.ZodTypeAny>;
};

export type ChatOptions<I = undefined, S = any> = BaseGenerateOptions & {
  store?: SessionStore<S>;
  sessionId?: string;
  input?: I;
};

/**
 * Chat encapsulates a statful execution environment for chat.
 * Chat session executed within a session in this environment will have acesss to
 * session convesation history.
 *
 * ```ts
 * const ai = genkit({...});
 * const chat = ai.chat(); // create a Chat
 * let response = await chat.send('hi, my name is Genkit');
 * response = await chat.send('what is my name?'); // chat history aware conversation
 * ```
 */
export class Chat {
  private requestBase?: BaseGenerateOptions;
  readonly sessionId: string;
  private _messages?: MessageData[];
  private threadName: string;
  private agentState?: AgentState;

  constructor(
    readonly session: Session,
    requestBase: BaseGenerateOptions,
    options: {
      id: string;
      thread: string;
      messages?: MessageData[];
      agentState?: AgentState;
    }
  ) {
    this.sessionId = options.id;
    this.threadName = options.thread;
    this.requestBase = requestBase;
    this._messages = (options.messages ?? []).concat(
      requestBase.messages ?? []
    );
    this.agentState = options.agentState;
  }

  private async lookupCurrentAgent(): Promise<AgentAction<any> | undefined> {
    if (!this.agentState?.agentName) {
      return undefined;
    }
    return (await this.session.registry.lookupAction(
      `/tool/${this.agentState.agentName}`
    )) as AgentAction<any>;
  }

  private currentAgentThread(): string {
    return `${this.threadName}__${this.agentState!.agentName}`;
  }

  async send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    console.log(
      ' - - - -  - - - -  - - - -  - - - -  - - - -  - - - -  - - - -  - - - -  send',
      JSON.stringify(options)
    );
    const resp = await this._send(options);
    await this.session.flushState();
    console.log(
      'post flush state: ',
      JSON.stringify(this.session.toJSON(), undefined, 2)
    );
    return resp;
  }

  private async _send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    if (!this.agentState) {
      return this.rawSend(options);
    }

    const currentAgent = await this.lookupCurrentAgent();
    if (!currentAgent) {
      throw new Error(`Unable to resolve ${this.agentState!.agentName}`);
    }

    let resolveOptions: ChatGenerateOptions<O, CustomOptions>;
    if (typeof options === 'string' || Array.isArray(options)) {
      resolveOptions = {
        prompt: options,
      };
    } else {
      resolveOptions = options;
    }
    let currentChat = this.session.chat(
      this.currentAgentThread(),
      await this.renderChatOptions(
        currentAgent!,
        this.agentState?.agentInput,
        this.session?.toJSON()?.threads?.[this.currentAgentThread()] ?? []
      )
    );

    const response = await currentChat.rawSend({
      ...resolveOptions,
      returnToolRequests: true,
    });
    if (response.toolRequests) {
      // TODO: first process tool calls, then chat agent transfers.
      for (const req of response.toolRequests) {
        const tool = await this.session.registry.lookupAction(
          `/tool/${req.toolRequest.name}`
        );
        if ((tool as AgentAction<any>).__agentOptions) {
          currentChat = await this.transferToAgent(
            tool as AgentAction<any>,
            currentAgent,
            currentChat,
            req.toolRequest.input
          );
          return currentChat.send(`transferred to ${req.toolRequest.name}`);
        } else if ((tool as InterruptAction<any>).__interruptOptions) {
          this.session.updateState({
            ...this.session.state,
            __interrupted_at: req,
          } as any);
          return response;
        } else {
          return currentChat.rawSend({
            messages: [
              {
                role: 'tool',
                content: [
                  {
                    toolResponse: {
                      name: req.toolRequest.name,
                      ref: req.toolRequest.ref,
                      output: await this.session.run(() =>
                        tool(req.toolRequest.input)
                      ),
                    },
                  },
                ],
              },
            ],
          });
        }
      }
    }
    return response;
  }

  private async transferToAgent(
    nextAgent: AgentAction<any>,
    oldAgent: AgentAction<any>,
    oldChat: Chat,
    input: any
  ): Promise<Chat> {
    const sessionData = this.session.toJSON() ?? ({} as SessionData<any>);
    if (!sessionData.threads) {
      sessionData.threads = {};
    }
    if (!sessionData.threads[this.threadName]) {
      sessionData.threads[this.threadName] = [];
    }
    // chat agents are "exited" on each transfer -- only one chat agent at a time
    if (oldAgent.__agentType === 'chat') {
      this.exitAgent(sessionData, oldAgent, oldChat);
      this.session.updateState({
        ...this.session.state,
        __agentState: {
          ...this.session.state.__agentState,
          [this.threadName]: {
            agentName: nextAgent.__agentOptions.name,
            agentInput: input,
          } as AgentState,
          [`${this.threadName}__${nextAgent.__agentOptions.name}`]: {
            agentName: nextAgent.__agentOptions.name,
            agentInput: input,
            parentThreadName: this.threadName,
          } as AgentState,
        },
      } as AgentThreadsSessionState & any);
      return this.session.chat(
        this.currentAgentThread(),
        await this.renderChatOptions(
          nextAgent,
          input,
          this.session?.toJSON()?.threads?.[this.threadName]
        )
      );
    }
    const toolAgentThreadName = `${this.currentAgentThread()}__${nextAgent.__agentOptions.name}`;
    this.session.updateState({
      ...this.session.state,
      __agentState: {
        ...this.session.state.__agentState,
        [toolAgentThreadName]: {
          agentName: nextAgent.__agentOptions.name,
          agentInput: input,
          parentThreadName: this.currentAgentThread(),
        } as AgentState,
      },
    } as AgentThreadsSessionState & any);
    return this.session.chat(
      toolAgentThreadName,
      await this.renderChatOptions(
        nextAgent,
        input,
        this.session?.toJSON()?.threads?.[this.currentAgentThread()]
      )
    );
  }

  private exitAgent(
    sessionData: SessionData<any>,
    oldAgent: AgentAction<any>,
    oldChat: Chat
  ) {
    console.log(
      '## # # ## # ## #  # # # exit agent to',
      this.agentState?.parentThreadName
    );
    if (this.agentState?.parentThreadName) {
      sessionData.threads?.[this.agentState?.parentThreadName].push(
        ...this.transformExit(oldChat, oldAgent)
      );
    }
  }

  private transformExit(
    currentChat: Chat,
    currentAgent: AgentAction<any>
  ): MessageData[] {
    const prefilter = stripPreamble(currentChat.messages);
    if (currentAgent.__agentOptions.onFinish) {
      return currentAgent.__agentOptions.onFinish(prefilter);
    }
    return prefilter;
  }

  private async renderChatOptions(
    agent: AgentAction<any>,
    input: any | undefined,
    history: MessageData[] | undefined
  ): Promise<ChatOptions> {
    const preamble: MessageData[] = [];
    if (typeof agent.__agentOptions.instructions === 'string') {
      console.log('context: ', this.session.toJSON()?.state);
      const prompt = await this.session.registry.dotprompt.render(
        agent.__agentOptions.instructions,
        {
          input,
          context: { state: this.session.toJSON()?.state },
        }
      );
      if (
        !prompt.messages ||
        prompt.messages.length === 0 ||
        prompt.messages.length > 1
      ) {
        throw new Error('instructions must only be a single message.');
      }
      preamble.push({
        role: 'system',
        content: prompt.messages[0].content,
      });
    } else {
      preamble.push({
        role: 'system',
        content: Array.isArray(agent.__agentOptions.instructions)
          ? agent.__agentOptions.instructions
          : [agent.__agentOptions.instructions],
      });
    }
    const opts: ChatOptions = {
      ...this.requestBase,
      config: { ...this.requestBase?.config, ...agent.__agentOptions.config },
      tools: agent.__agentOptions.tools,
      toolChoice:
        agent.__agentOptions.toolChoice ?? this.requestBase?.toolChoice,
      messages: tagAsPreamble(preamble)!.concat(stripPreamble(history) ?? []),
    };
    console.log('= = = = rendered options', JSON.stringify(opts, undefined, 2));
    return opts;
  }

  private async rawSend<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    console.log(' - -rawSend: ', JSON.stringify(options, undefined, 2));
    return runWithSession(this.session.registry, this.session, () =>
      runInNewSpan(
        this.session.registry,
        { metadata: { name: 'send' } },
        async () => {
          let resolvedOptions: ChatGenerateOptions<O, CustomOptions>;
          let streamingCallback:
            | StreamingCallback<GenerateResponseChunk>
            | undefined = undefined;

          // string
          if (typeof options === 'string') {
            resolvedOptions = {
              prompt: options,
            } as ChatGenerateOptions<O, CustomOptions>;
          } else if (Array.isArray(options)) {
            // Part[]
            resolvedOptions = {
              prompt: options,
            } as ChatGenerateOptions<O, CustomOptions>;
          } else {
            resolvedOptions = options as ChatGenerateOptions<O, CustomOptions>;
            streamingCallback =
              resolvedOptions.onChunk ?? resolvedOptions.streamingCallback;
          }
          let request: GenerateOptions = {
            ...this.requestBase,
            ...resolvedOptions,
            messages: (this.messages ?? []).concat(
              resolvedOptions.messages ?? []
            ),
          };
          let response = await generate(this.session.registry, {
            ...request,
            onChunk: streamingCallback,
          });
          this.updateMessages(this.maybeTagWithCurrentAgent(response.messages));
          return response;
        }
      )
    );
  }

  private maybeTagWithCurrentAgent(msgs: MessageData[]): MessageData[] {
    console.log(
      'maybeTagWithCurrentAgent currentAgent',
      this.agentState?.agentName
    );
    if (this.agentState?.agentName) {
      return msgs.map((m) => ({
        ...m,
        metadata: {
          ...m.metadata,
          fromAgent: this.agentState?.agentName,
        },
      }));
    }
    return msgs;
  }

  sendStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | GenerateStreamOptions<O, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    return runWithSession(this.session.registry, this.session, () =>
      runInNewSpan(
        this.session.registry,
        { metadata: { name: 'send' } },
        async () => {
          let resolvedOptions;

          // string
          if (typeof options === 'string') {
            resolvedOptions = {
              prompt: options,
            } as GenerateStreamOptions<O, CustomOptions>;
          } else if (Array.isArray(options)) {
            // Part[]
            resolvedOptions = {
              prompt: options,
            } as GenerateStreamOptions<O, CustomOptions>;
          } else {
            resolvedOptions = options as GenerateStreamOptions<
              O,
              CustomOptions
            >;
          }

          const { response, stream } = await generateStream(
            this.session.registry,
            {
              ...(await this.requestBase),
              messages: this.messages,
              ...resolvedOptions,
            }
          );

          return {
            response: response.finally(async () => {
              const resolvedResponse = await response;
              this.requestBase = {
                ...this.requestBase,
                // these things may get changed by tools calling within generate.
                tools: resolvedResponse?.request?.tools,
                toolChoice: resolvedResponse?.request?.toolChoice,
                config: resolvedResponse?.request?.config,
              };
              this.updateMessages(resolvedResponse.messages);
            }),
            stream,
          };
        }
      )
    );
  }

  get messages(): MessageData[] {
    return this._messages ?? [];
  }

  private updateMessages(messages: MessageData[]): void {
    this._messages = messages;
    this.session.updateMessages(this.threadName, messages);
  }
}

function hasPreamble(msgs?: MessageData[]) {
  return !!msgs?.find((m) => m.metadata?.preamble);
}

function getPreamble(msgs?: MessageData[]) {
  return msgs?.filter((m) => m.metadata?.preamble);
}

function stripPreamble(msgs?: MessageData[]) {
  return msgs?.filter((m) => !m.metadata?.preamble) ?? [];
}
