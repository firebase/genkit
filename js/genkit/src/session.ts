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
  Message,
  MessageData,
  tagAsPreamble,
} from '@genkit-ai/ai';
import { z } from '@genkit-ai/core';
import { AsyncLocalStorage } from 'node:async_hooks';
import { v4 as uuidv4 } from 'uuid';
import { Chat, ChatOptions, MAIN_THREAD, PromptRenderOptions } from './chat';
import { Genkit } from './genkit';

export type BaseGenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Omit<GenerateOptions<O, CustomOptions>, 'prompt'>;

export interface SessionOptions<S = any> {
  /** Session store implementation for persisting the session state. */
  store?: SessionStore<S>;
  /** Initial state of the session.  */
  initialState?: S;
  /** Custom session Id. */
  sessionId?: string;
}

/**
 * Session encapsulates a statful execution environment for chat.
 * Chat session executed within a session in this environment will have acesss to
 * session session convesation history.
 *
 * ```ts
 * const ai = genkit({...});
 * const chat = ai.chat(); // create a Session
 * let response = await chat.send('hi'); // session/history aware conversation
 * response = await chat.send('tell me a story');
 * ```
 */
export class Session<S = any> {
  readonly id: string;
  private sessionData?: SessionData<S>;
  private store: SessionStore<S>;

  constructor(
    readonly genkit: Genkit,
    options?: {
      id?: string;
      stateSchema?: S;
      sessionData?: SessionData<S>;
      store?: SessionStore<S>;
    }
  ) {
    this.id = options?.id ?? uuidv4();
    this.sessionData = options?.sessionData ?? {
      id: this.id,
    };
    if (!this.sessionData) {
      this.sessionData = { id: this.id };
    }
    if (!this.sessionData.threads) {
      this.sessionData!.threads = {};
    }
    this.store = options?.store ?? new InMemorySessionStore<S>();
  }

  get state(): S | undefined {
    // We always get state from the parent. Parent session is the source of truth.
    if (this.genkit instanceof Session) {
      return this.genkit.state;
    }
    return this.sessionData!.state;
  }

  /**
   * Update session state data.
   */
  async updateState(data: S): Promise<void> {
    let sessionData = this.sessionData;
    if (!sessionData) {
      sessionData = {} as SessionData<S>;
    }
    sessionData.state = data;
    this.sessionData = sessionData;

    await this.store.save(this.id, sessionData);
  }

  /**
   * Update messages for a given thread.
   */
  async updateMessages(
    thread: string,
    messasges: MessageData[]
  ): Promise<void> {
    let sessionData = this.sessionData;
    if (!sessionData) {
      sessionData = {} as SessionData<S>;
    }
    if (!sessionData.threads) {
      sessionData.threads = {};
    }
    sessionData.threads[thread] = messasges;
    this.sessionData = sessionData;

    await this.store.save(this.id, sessionData);
  }

  /**
   * Create a chat session with the provided options.
   *
   * ```ts
   * const chat = ai.chat({
   *   system: 'talk like a pirate',
   * })
   * let response = await chat.send('tell me a joke')
   * response = await chat.send('another one')
   * ```
   */
  chat<I>(options?: ChatOptions<I, S>): Chat;

  /**
   * Craete a separaete chat conversation ("thread") within the same session state.
   *
   * ```ts
   * const lawyerChat = ai.chat('lawyerThread', {
   *   system: 'talk like a lawyer',
   * })
   * const pirateChat = ai.chat('pirateThread', {
   *   system: 'talk like a pirate',
   * })
   * await lawyerChat.send('tell me a joke')
   * await pirateChat.send('tell me a joke')
   * ```
   */
  chat<I>(threadName: string, options?: ChatOptions<I, S>): Chat;

  chat<I>(
    optionsOrThreadName?: ChatOptions<I, S> | string,
    maybeOptions?: ChatOptions<I, S>
  ): Chat {
    return runWithSession(this, () => {
      let options: ChatOptions<S> | undefined;
      let threadName = MAIN_THREAD;
      if (maybeOptions) {
        threadName = optionsOrThreadName as string;
        options = maybeOptions as ChatOptions<S>;
      } else if (optionsOrThreadName) {
        if (typeof optionsOrThreadName === 'string') {
          threadName = optionsOrThreadName as string;
        } else {
          options = optionsOrThreadName as ChatOptions<S>;
        }
      }
      let requestBase: Promise<BaseGenerateOptions>;
      if (!!(options as PromptRenderOptions<I>)?.prompt?.render) {
        const renderOptions = options as PromptRenderOptions<I>;
        requestBase = renderOptions.prompt
          .render({
            input: renderOptions.input,
          })
          .then((rb) => {
            return {
              ...rb,
              messages: tagAsPreamble(rb?.messages),
            };
          });
      } else {
        const baseOptions = { ...(options as BaseGenerateOptions) };
        const messages: MessageData[] = [];
        if (baseOptions.system) {
          messages.push({
            role: 'system',
            content: Message.parseContent(baseOptions.system),
          });
        }
        delete baseOptions.system;
        if (baseOptions.messages) {
          messages.push(...baseOptions.messages);
        }
        baseOptions.messages = tagAsPreamble(messages);

        requestBase = Promise.resolve(baseOptions);
      }
      return new Chat(this, requestBase, {
        thread: threadName,
        id: this.id,
        messages:
          (this.sessionData?.threads &&
            this.sessionData?.threads[threadName]) ??
          [],
      });
    });
  }

  /**
   * Executes provided function within this session context allowing calling
   * `ai.currentSession().state`
   */
  run<O>(fn: () => O) {
    return runWithSession(this, fn);
  }

  toJSON() {
    return this.sessionData;
  }
}

export interface SessionData<S = any> {
  id: string;
  state?: S;
  threads?: Record<string, MessageData[]>;
}

const sessionAls = new AsyncLocalStorage<Session<any>>();

/**
 * Executes provided function within the provided session state.
 */
export function runWithSession<S = any, O = any>(
  session: Session<S>,
  fn: () => O
): O {
  return sessionAls.run(session, fn);
}

/** Returns the current session. */
export function getCurrentSession<S = any>(): Session<S> | undefined {
  return sessionAls.getStore();
}

/** Throw when session state errors occur, ex. missing state, etc. */
export class SessionError extends Error {
  constructor(msg: string) {
    super(msg);
  }
}

/** Session store persists session data such as state and chat messages. */
export interface SessionStore<S = any> {
  get(sessionId: string): Promise<SessionData<S> | undefined>;

  save(sessionId: string, data: Omit<SessionData<S>, 'id'>): Promise<void>;
}

export function inMemorySessionStore() {
  return new InMemorySessionStore();
}

class InMemorySessionStore<S = any> implements SessionStore<S> {
  private data: Record<string, SessionData<S>> = {};

  async get(sessionId: string): Promise<SessionData<S> | undefined> {
    return this.data[sessionId];
  }

  async save(sessionId: string, sessionData: SessionData<S>): Promise<void> {
    this.data[sessionId] = sessionData;
  }
}
