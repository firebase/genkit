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
import { dotprompt } from 'dotprompt';
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

  constructor(
    readonly session: Session,
    requestBase: BaseGenerateOptions,
    options: {
      id: string;
      thread: string;
      messages?: MessageData[];
      agent?: AgentAction<any>;
    }
  ) {
    this.sessionId = options.id;
    this.threadName = options.thread;
    this.requestBase = requestBase;
    this._messages = options.messages;
  }

  private async lookupCurrentAgent(): Promise<AgentAction<any> | undefined> {
    if (
      !this.session.toJSON()?.state?.__agentState?.[this.threadName]
        ?.currentAgent
    ) {
      return undefined;
    }
    return (await this.session.registry.lookupAction(
      `/tool/${this.session.toJSON()?.state?.__agentState?.[this.threadName]?.currentAgent}`
    )) as AgentAction<any>;
  }

  private currentAgentThread(agent: AgentAction<any>): string {
    return `${this.threadName}_${agent.__agentOptions.name}`;
  }

  async send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    const currentAgent = await this.lookupCurrentAgent();
    console.log(
      '--- - - - - - -currentAgent',
      currentAgent?.__agentOptions?.name
    );
    if (!currentAgent) {
      return this.rawSend(options);
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
      this.currentAgentThread(currentAgent),
      await this.renderChatOptions(
        currentAgent!,
        (this.session.toJSON()?.state as AgentThreadsSessionState)
          ?.__agentState?.[this.threadName]?.currentAgentInput,
        this.session?.toJSON()?.threads?.[
          this.currentAgentThread(currentAgent)
        ] ?? []
      )
    );

    const response = await currentChat.rawSend({
      ...resolveOptions,
      returnToolRequests: true,
    });
    if (response.toolRequests) {
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
          await this.session.updateState({
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
    sessionData.threads[this.threadName].push(
      ...this.transformExit(oldChat, oldAgent)
    );
    const newChat = this.session.chat(
      this.currentAgentThread(nextAgent),
      await this.renderChatOptions(
        nextAgent,
        input,
        this.session?.toJSON()?.threads?.[this.currentAgentThread(oldAgent)]
      )
    );
    await this.session.updateState({
      ...this.session.state,
      __agentState: {
        [this.threadName]: {
          currentAgent: nextAgent.__agentOptions.name,
          currentAgentInput: input,
        } as AgentState,
      },
    } as AgentThreadsSessionState & any);
    return newChat;
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
      const dp = await this.session.registry.dotprompt.render(agent.__agentOptions.instructions, {
        input,
        context: { state: this.session.toJSON()?.state },
      });
      if (!dp.messages || dp.messages.length === 0 || dp.messages.length > 1) {
        throw new Error('instructions must only be a single message.');
      }
      preamble.push({
        role: 'system',
        content: dp.messages[0].content,
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
      config: agent.__agentOptions.config,
      tools: agent.__agentOptions.tools,
      toolChoice: agent.__agentOptions.toolChoice,
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
          await this.updateMessages(response.messages);
          return response;
        }
      )
    );
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
                ...(await this.requestBase),
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

  private async updateMessages(messages: MessageData[]): Promise<void> {
    this._messages = messages;
    await this.session.updateMessages(this.threadName, messages);
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
