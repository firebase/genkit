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

import { GenerateOptions, MessageData } from '@genkit-ai/ai';
import { z } from '@genkit-ai/core';
import { AsyncLocalStorage } from 'node:async_hooks';
import { v4 as uuidv4 } from 'uuid';
import { Chat, ChatOptions, MAIN_THREAD, PromptRenderOptions } from './chat';
import { Genkit } from './genkit';

export type BaseGenerateOptions = Omit<GenerateOptions, 'prompt'>;

export interface SessionOptions<S extends z.ZodTypeAny = z.ZodTypeAny> {
  /** Schema describing the state. */
  stateSchema?: S;
  /** Session store implementation for persisting the session state. */
  store?: SessionStore<S>;
  /** Initial state of the session.  */
  state?: z.infer<S>;
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
export class Session<S extends z.ZodTypeAny = z.ZodTypeAny> {
  readonly id: string;
  readonly schema?: S;
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
    this.schema = options?.stateSchema;
    this.sessionData = options?.sessionData;
    if (!this.sessionData) {
      this.sessionData = { id: this.id };
    }
    if (!this.sessionData.threads) {
      this.sessionData!.threads = {};
    }
    this.store = options?.store ?? new InMemorySessionStore();
  }

  get state(): z.infer<S> {
    // We always get state from the parent. Parent session is the source of truth.
    if (this.genkit instanceof Session) {
      return this.genkit.state;
    }
    return this.sessionData!.state;
  }

  /**
   * Update session state data.
   */
  async updateState(data: z.infer<S>): Promise<void> {
    // We always update the state on the parent. Parent session is the source of truth.
    if (this.genkit instanceof Session) {
      return this.genkit.updateState(data);
    }
    let sessionData = await this.store.get(this.id);
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
    let sessionData = await this.store.get(this.id);
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
  chat<I>(options?: ChatOptions<I, S>): Chat<S>;

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
  chat<I>(threadName: string, options?: ChatOptions<I, S>): Chat<S>;

  chat<I>(
    optionsOrThreadName?: ChatOptions<I, S> | string,
    maybeOptions?: ChatOptions<I, S>
  ): Chat<S> {
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
      console.log('yeah, prompt, render....');
      const renderOptions = options as PromptRenderOptions<I>;
      requestBase = renderOptions.prompt.render({
        input: renderOptions.input,
      });
    } else {
      requestBase = Promise.resolve(options as BaseGenerateOptions);
    }
    return new Chat<S>(this, requestBase, {
      thread: threadName,
      id: this.id,
      messages:
        (this.sessionData?.threads && this.sessionData?.threads[threadName]) ??
        [],
    });
  }

  toJSON() {
    return this.sessionData;
  }
}

export interface SessionData<S extends z.ZodTypeAny = z.ZodTypeAny> {
  id: string;
  state?: z.infer<S>;
  threads?: Record<string, MessageData[]>;
}

const sessionAls = new AsyncLocalStorage<Session<any>>();

/**
 * Executes provided function within the provided session state.
 */
export function runWithSession<S extends z.ZodTypeAny, O>(
  session: Session<S>,
  fn: () => O
): O {
  return sessionAls.run(session, fn);
}

/** Returns the current session. */
export function getCurrentSession<S extends z.ZodTypeAny = z.ZodTypeAny>():
  | Session<S>
  | undefined {
  return sessionAls.getStore();
}

/** Throw when session state errors occur, ex. missing state, etc. */
export class SessionError extends Error {
  constructor(msg: string) {
    super(msg);
  }
}

/** Session store persists session data such as state and chat messages. */
export interface SessionStore<S extends z.ZodTypeAny> {
  get(sessionId: string): Promise<SessionData<S> | undefined>;

  save(sessionId: string, data: Omit<SessionData<S>, 'id'>): Promise<void>;
}

export function inMemorySessionStore() {
  return new InMemorySessionStore();
}

class InMemorySessionStore<S extends z.ZodTypeAny> implements SessionStore<S> {
  private data: Record<string, SessionData<S>> = {};

  async get(sessionId: string): Promise<SessionData<S> | undefined> {
    return this.data[sessionId];
  }

  async save(sessionId: string, sessionData: SessionData<S>): Promise<void> {
    this.data[sessionId] = sessionData;
  }
}
