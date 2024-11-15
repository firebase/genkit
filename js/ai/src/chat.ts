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

import { z } from '@genkit-ai/core';
import { runInNewSpan } from '@genkit-ai/core/tracing';
import {
  generate,
  GenerateOptions,
  GenerateResponse,
  generateStream,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  MessageData,
  Part,
} from './index.js';
import {
  BaseGenerateOptions,
  runWithSession,
  Session,
  SessionStore,
} from './session';

export const MAIN_THREAD = 'main';

export type ChatGenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = GenerateOptions<O, CustomOptions>;

export interface PromptRenderOptions<I> {
  input?: I;
}

export type ChatOptions<I = undefined, S = any> = (
  | PromptRenderOptions<I>
  | BaseGenerateOptions
) & {
  store?: SessionStore<S>;
  sessionId?: string;
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
  private requestBase?: Promise<BaseGenerateOptions>;
  readonly sessionId: string;
  private _messages?: MessageData[];
  private threadName: string;

  constructor(
    readonly session: Session,
    requestBase: Promise<BaseGenerateOptions>,
    options: {
      id: string;
      thread: string;
      messages?: MessageData[];
    }
  ) {
    this.sessionId = options.id;
    this.threadName = options.thread;
    this.requestBase = requestBase?.then((rb) => {
      const requestBase = { ...rb };
      // this is handling dotprompt render case
      if (requestBase && requestBase['prompt']) {
        const basePrompt = requestBase['prompt'] as string | Part | Part[];
        let promptMessage: MessageData;
        if (typeof basePrompt === 'string') {
          promptMessage = {
            role: 'user',
            content: [{ text: basePrompt }],
          };
        } else if (Array.isArray(basePrompt)) {
          promptMessage = {
            role: 'user',
            content: basePrompt,
          };
        } else {
          promptMessage = {
            role: 'user',
            content: [basePrompt],
          };
        }
        requestBase.messages = [...(requestBase.messages ?? []), promptMessage];
      }
      if (hasPreamble(requestBase.messages)) {
        requestBase.messages = [
          // if request base contains a preamble, always put it first
          ...(getPreamble(requestBase.messages) ?? []),
          // strip out the preamble from history
          ...(stripPreamble(options.messages) ?? []),
          // add whatever non-preamble remains from request
          ...(stripPreamble(requestBase.messages) ?? []),
        ];
      } else {
        requestBase.messages = [
          ...(options.messages ?? []),
          ...(requestBase.messages ?? []),
        ];
      }
      this._messages = requestBase.messages;
      return requestBase;
    });
    this._messages = options.messages;
  }

  async send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    return runWithSession(this.session, () =>
      runInNewSpan({ metadata: { name: 'send' } }, async () => {
        let resolvedOptions;
        let streamingCallback = undefined;

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
          streamingCallback = resolvedOptions.streamingCallback;
        }
        let request: GenerateOptions = {
          ...(await this.requestBase),
          messages: this.messages,
          ...resolvedOptions,
        };
        let response = await generate(this.session.registry, {
          ...request,
          streamingCallback,
        });
        this.requestBase = Promise.resolve({
          ...(await this.requestBase),
          // these things may get changed by tools calling within generate.
          tools: response?.request?.tools,
          config: response?.request?.config,
        });
        await this.updateMessages(response.messages);
        return response;
      })
    );
  }

  sendStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | GenerateStreamOptions<O, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    return runWithSession(this.session, () =>
      runInNewSpan({ metadata: { name: 'send' } }, async () => {
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
          resolvedOptions = options as GenerateStreamOptions<O, CustomOptions>;
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
            this.requestBase = Promise.resolve({
              ...(await this.requestBase),
              // these things may get changed by tools calling within generate.
              tools: resolvedResponse?.request?.tools,
              config: resolvedResponse?.request?.config,
            });
            this.updateMessages(resolvedResponse.messages);
          }),
          stream,
        };
      })
    );
  }

  get messages(): MessageData[] {
    return this._messages ?? [];
  }

  async updateMessages(messages: MessageData[]): Promise<void> {
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
  return msgs?.filter((m) => !m.metadata?.preamble);
}
