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
  ExecutablePrompt,
  GenerateOptions,
  GenerateResponse,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  MessageData,
  Part,
} from '@genkit-ai/ai';
import { z } from '@genkit-ai/core';
import { Genkit } from './genkit';
import { Session, SessionStore } from './session';

export const MAIN_THREAD = 'main';

export type BaseGenerateOptions = Omit<GenerateOptions, 'prompt'>;

export interface PromptRenderOptions<I> {
  prompt: ExecutablePrompt<I>;
  input?: I;
}

export type ChatOptions<
  I = undefined,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = (PromptRenderOptions<I> | BaseGenerateOptions) & {
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
export class Chat<S extends z.ZodTypeAny = z.ZodTypeAny> {
  readonly requestBase?: Promise<BaseGenerateOptions>;
  readonly sessionId: string;
  readonly schema?: S;
  private _messages?: MessageData[];
  private threadName: string;

  constructor(
    readonly session: Session<S>,
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
      requestBase.messages = [
        ...(options.messages ?? []),
        ...(requestBase.messages ?? []),
      ];
      this._messages = requestBase.messages;
      return requestBase;
    });
    this._messages = options.messages;
  }

  async send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | GenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    // string
    if (typeof options === 'string') {
      options = {
        prompt: options,
      } as GenerateOptions<O, CustomOptions>;
    }
    // Part[]
    if (Array.isArray(options)) {
      options = {
        prompt: options,
      } as GenerateOptions<O, CustomOptions>;
    }
    const response = await this.genkit.generate({
      ...(await this.requestBase),
      messages: this.messages,
      ...options,
    });
    await this.updateMessages(response.messages);
    return response;
  }

  async sendStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | GenerateStreamOptions<O, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    // string
    if (typeof options === 'string') {
      options = {
        prompt: options,
      } as GenerateOptions<O, CustomOptions>;
    }
    // Part[]
    if (Array.isArray(options)) {
      options = {
        prompt: options,
      } as GenerateOptions<O, CustomOptions>;
    }
    const { response, stream } = await this.genkit.generateStream({
      ...(await this.requestBase),
      messages: this.messages,
      ...options,
    });

    return {
      response: response.finally(async () => {
        this.updateMessages((await response).messages);
      }),
      stream,
    };
  }

  private get genkit(): Genkit {
    return this.session.genkit;
  }

  get messages(): MessageData[] {
    return this._messages ?? [];
  }

  async updateMessages(messages: MessageData[]): Promise<void> {
    this._messages = messages;
    await this.session.updateMessages(this.threadName, messages);
  }
}
