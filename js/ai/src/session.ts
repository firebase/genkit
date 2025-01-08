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
import { Registry } from '@genkit-ai/core/registry';
import { v4 as uuidv4 } from 'uuid';
import { AgentAction } from './agent.js';
import { Chat, ChatOptions, MAIN_THREAD } from './chat.js';
import {
  GenerateOptions,
  Message,
  MessageData,
  tagAsPreamble,
} from './index.js';

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
  protected sessionData?: SessionData<S>;
  private store: SessionStore<S>;

  constructor(
    readonly registry: Registry,
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
    return this.sessionData!.state;
  }

  /**
   * Update session state data by patching the existing state.
   * @param data Partial state update that will be merged with existing state
   */
  async updateState(data: Partial<S>): Promise<void> {
    let sessionData = this.sessionData;
    if (!sessionData) {
      sessionData = {} as SessionData<S>;
    }

    // Merge the new data with existing state
    sessionData.state = {
      ...sessionData.state,
      ...data,
    } as S & AgentThreadsSessionState;

    this.sessionData = sessionData;
    await this.store.save(this.id, sessionData);
  }

  /**
   * Update messages for a given thread.
   */
  async updateMessages(thread: string, messages: MessageData[]): Promise<void> {
    let sessionData = this.sessionData;
    if (!sessionData) {
      sessionData = {} as SessionData<S>;
    }
    if (!sessionData.threads) {
      sessionData.threads = {};
    }
    sessionData.threads[thread] = messages.map((m: any) =>
      m.toJSON ? m.toJSON() : m
    );
    this.sessionData = sessionData;

    await this.store.save(this.id, sessionData);
  }

  /**
   * Create a chat session with the provided options.
   *
   * ```ts
   * const session = ai.createSession({});
   * const chat = session.chat({
   *   system: 'talk like a pirate',
   * })
   * let response = await chat.send('tell me a joke');
   * response = await chat.send('another one');
   * ```
   */
  chat<I extends z.ZodTypeAny>(options?: ChatOptions<z.infer<I>, S>): Chat;

  /**
   * Create a chat session with the provided preamble.
   *
   * ```ts
   * const triageAgent = ai.definePrompt({
   *   system: 'help the user triage a problem',
   * })
   * const session = ai.createSession({});
   * const chat = session.chat(triageAgent);
   * const { text } = await chat.send('my phone feels hot');
   * ```
   */
  chat<I extends z.ZodTypeAny>(
    agent: AgentAction<I>,
    options?: ChatOptions<z.infer<I>, S>
  ): Chat;

  /**
   * Craete a separate chat conversation ("thread") within the given preamble.
   *
   * ```ts
   * const session = ai.createSession({});
   * const lawyerChat = session.chat('lawyerThread', {
   *   system: 'talk like a lawyer',
   * });
   * const pirateChat = session.chat('pirateThread', {
   *   system: 'talk like a pirate',
   * });
   * await lawyerChat.send('tell me a joke');
   * await pirateChat.send('tell me a joke');
   * ```
   */
  chat<I extends z.ZodTypeAny>(
    threadName: string,
    agent: AgentAction<I>,
    options?: ChatOptions<z.infer<I>, S>
  ): Chat;

  /**
   * Craete a separate chat conversation ("thread").
   *
   * ```ts
   * const session = ai.createSession({});
   * const lawyerChat = session.chat('lawyerThread', {
   *   system: 'talk like a lawyer',
   * });
   * const pirateChat = session.chat('pirateThread', {
   *   system: 'talk like a pirate',
   * });
   * await lawyerChat.send('tell me a joke');
   * await pirateChat.send('tell me a joke');
   * ```
   */
  chat<I extends z.ZodTypeAny>(
    threadName: string,
    options?: ChatOptions<z.infer<I>, S>
  ): Chat;

  chat<I extends z.ZodTypeAny>(
    optionsOrAgentOrThreadName?:
      | ChatOptions<z.infer<I>, S>
      | string
      | AgentAction<I>,
    maybeOptionsOrAgent?: ChatOptions<I, S> | AgentAction<I>,
    maybeOptions?: ChatOptions<z.infer<I>, S>
  ): Chat {
    return runWithSession(this.registry, this, () => {
      let options: ChatOptions<I, S> | undefined;
      let threadName = MAIN_THREAD;
      let agent: AgentAction<I> | undefined;

      if (optionsOrAgentOrThreadName) {
        if (typeof optionsOrAgentOrThreadName === 'string') {
          threadName = optionsOrAgentOrThreadName as string;
        } else if (
          (optionsOrAgentOrThreadName as AgentAction<I>).__agentOptions
        ) {
          agent = optionsOrAgentOrThreadName as AgentAction<I>;
        } else {
          options = optionsOrAgentOrThreadName as ChatOptions<I, S>;
        }
      }
      if (maybeOptionsOrAgent) {
        if ((maybeOptionsOrAgent as AgentAction<I>).__agentOptions) {
          agent = maybeOptionsOrAgent as AgentAction<I>;
        } else {
          options = maybeOptionsOrAgent as ChatOptions<I, S>;
        }
      }
      if (maybeOptions) {
        options = maybeOptions as ChatOptions<I, S>;
      }
      const baseOptions = { ...(options as BaseGenerateOptions) };
      const messages: MessageData[] = [];
      if (baseOptions.system) {
        messages.push({
          role: 'system',
          content: Message.parseContent(baseOptions.system),
        });
      }
      delete baseOptions.system;

      let historyOverride: MessageData[] | undefined;
      if (baseOptions.messages) {
        historyOverride = [...baseOptions.messages];
        delete baseOptions.messages;
      }

      baseOptions.messages = tagAsPreamble(messages);

      if (
        agent &&
        !this.sessionData?.state?.__agentState?.[threadName]?.currentAgent
      ) {
        this.sessionData = updateAgentSessionData(
          this.id,
          this.sessionData,
          threadName,
          {
            currentAgent: agent.__agentOptions.name,
            currentAgentInput: (options as ChatOptions<any>)?.input,
          }
        );
      }

      return new Chat(this, baseOptions, {
        thread: threadName,
        id: this.id,
        agent,
        messages:
          historyOverride ??
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
    return runWithSession(this.registry, this, fn);
  }

  toJSON() {
    return this.sessionData;
  }
}

export function updateAgentSessionData<S>(
  sessionId: string,
  sessionData: SessionData | undefined,
  threadName: string,
  data: AgentState
): SessionData<S> {
  if (!sessionData) {
    sessionData = {
      id: sessionId,
    };
  }
  if (!sessionData.state) {
    sessionData.state = {};
  }
  if (!sessionData.state.__agentState) {
    sessionData.state.__agentState = {};
  }
  sessionData.state['__agentState'][threadName] = {
    ...sessionData.state['__agentState'][threadName],
    ...data,
  };

  return sessionData;
}

export interface SessionData<S = any> {
  id: string;
  state?: S & AgentThreadsSessionState;
  threads?: Record<string, MessageData[]>;
}

const sessionAlsKey = 'ai.session';

/**
 * Executes provided function within the provided session state.
 */
export function runWithSession<S = any, O = any>(
  registry: Registry,
  session: Session<S>,
  fn: () => O
): O {
  return registry.asyncStore.run(sessionAlsKey, session, fn);
}

/** Returns the current session. */
export function getCurrentSession<S = any>(
  registry: Registry
): Session<S> | undefined {
  return registry.asyncStore.getStore(sessionAlsKey);
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

export interface AgentState {
  currentAgent: string;
  currentAgentInput?: any;
  interruptedAt?: string;
}

export type AgentThreadsSessionState = {
  __agentState?: Record<string, AgentState>;
};
