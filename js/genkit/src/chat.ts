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
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  MessageData,
  Part,
} from '@genkit-ai/ai';
import { z } from '@genkit-ai/core';
import { v4 as uuidv4 } from 'uuid';
import { Genkit } from './genkit';
import {
  Session,
  SessionData,
  SessionStore,
  inMemorySessionStore,
} from './session';

export const MAIN_THREAD = 'main';

export type BaseGenerateOptions = Omit<GenerateOptions, 'prompt'>;

export type ChatOptions<S extends z.ZodTypeAny = z.ZodTypeAny> =
  BaseGenerateOptions & {
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
  readonly sessionId: string;
  readonly schema?: S;
  private sessionData?: SessionData<S>;
  private store: SessionStore<S>;
  private threadName: string;

  constructor(
    readonly parent: Genkit | Session<S> | Chat<S>,
    readonly requestBase?: BaseGenerateOptions,
    options?: {
      id?: string;
      sessionData?: SessionData<S>;
      store?: SessionStore<S>;
      thread?: string;
    }
  ) {
    this.sessionId = options?.id ?? uuidv4();
    this.threadName = options?.thread ?? MAIN_THREAD;
    this.sessionData = options?.sessionData;
    if (!this.sessionData) {
      this.sessionData = {};
    }
    if (!this.sessionData.threads) {
      this.sessionData!.threads = {};
    }
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
    if (parent instanceof Chat) {
      if (!this.sessionData.threads[this.threadName]) {
        this!.sessionData.threads[this.threadName] = [
          ...(parent.messages ?? []),
          ...(requestBase?.messages ?? []),
        ];
      }
    } else if (parent instanceof Session) {
      if (!this.sessionData.threads[this.threadName]) {
        this!.sessionData.threads[this.threadName] = [
          ...(requestBase?.messages ?? []),
        ];
      }
    } else {
      // Genkit
      if (!this.sessionData.threads[this.threadName]) {
        this.sessionData.threads[this.threadName] = [
          ...(requestBase?.messages ?? []),
        ];
      }
    }
    this.store = options?.store ?? (inMemorySessionStore() as SessionStore<S>);
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
      ...this.requestBase,
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
      ...this.requestBase,
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
    if (this.parent instanceof Genkit) {
      return this.parent;
    }
    if (this.parent instanceof Session) {
      return this.parent.genkit;
    }
    return this.parent.genkit;
  }

  get state(): z.infer<S> {
    // We always get state from the parent. Parent session is the source of truth.
    if (this.parent instanceof Session) {
      return this.parent.state;
    }
    return this.sessionData!.state;
  }

  async updateState(data: z.infer<S>): Promise<void> {
    // We always update the state on the parent. Parent session is the source of truth.
    if (this.parent instanceof Session) {
      return this.parent.updateState(data);
    }
    let sessionData = await this.store.get(this.sessionId);
    if (!sessionData) {
      sessionData = {} as SessionData<S>;
    }
    sessionData.state = data;
    this.sessionData = sessionData;

    await this.store.save(this.sessionId, sessionData);
  }

  get messages(): MessageData[] | undefined {
    if (!this.sessionData?.threads) {
      return undefined;
    }
    return this.sessionData?.threads[this.threadName];
  }

  async updateMessages(messages: MessageData[]): Promise<void> {
    let sessionData = await this.store.get(this.sessionId);
    if (!sessionData) {
      sessionData = { threads: {} };
    }
    if (!sessionData.threads) {
      sessionData.threads = {};
    }
    sessionData.threads[this.threadName] = messages;
    this.sessionData = sessionData;
    await this.store.save(this.sessionId, sessionData);
  }

  toJSON() {
    if (this.parent instanceof Session) {
      return this.parent.toJSON();
    }
    return this.sessionData;
  }

  static fromJSON<S extends z.ZodTypeAny>(data: SessionData<S>) {
    //return new Session();
  }
}
