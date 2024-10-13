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
  MessageData,
  PromptFn,
  ToolAction,
  ToolConfig,
} from '@genkit-ai/ai';
import {
  CallableFlow,
  FlowConfig,
  FlowFn,
  StreamableFlow,
  StreamingFlowConfig,
  z,
} from '@genkit-ai/core';
import { PromptMetadata } from '@genkit-ai/dotprompt';
import { AsyncLocalStorage } from 'node:async_hooks';
import { v4 as uuidv4 } from 'uuid';
import { Chat, ChatOptions, MAIN_THREAD } from './chat';
import { ExecutablePrompt, Genkit } from './genkit';

export type BaseGenerateOptions = Omit<GenerateOptions, 'prompt'>;

type EnvironmentType = Pick<
  Genkit,
  'defineFlow' | 'defineStreamingFlow' | 'defineTool' | 'definePrompt'
>;

type EnvironmentSessionOptions<S extends z.ZodTypeAny> = Omit<
  SessionOptions<S>,
  'store'
>;

/**
 * Environment encapsulates a statful execution environment for chat sessions, flows and prompts.
 * Flows, prompts, chat session executed within a session in this environment will have acesss to
 * session state data which includes custom state objects and session convesation history.
 *
 * ```ts
 * const ai = genkit({...});
 * const agent = ai.defineEnvironment();
 * const flow = agent.defineFlow({...})
 * agent.definePrompt({...})
 * agent.defineTool({...})
 * const session = agent.createSession(); // create a Session
 * let response = await session.send('hi'); // session state aware conversation
 * await session.runFlow(flow, {...})
 * ```
 */
export class Environment<S extends z.ZodTypeAny> implements EnvironmentType {
  private store: SessionStore<S>;

  constructor(
    readonly name: string,
    readonly genkit: Genkit,
    config: {
      stateSchema?: S;
      store?: SessionStore<S>;
    }
  ) {
    this.store = config.store ?? (inMemorySessionStore() as SessionStore<S>);
  }

  /**
   * Defines and registers a non-streaming flow.
   *
   * @todo TODO: Improve this documentation (show snippets, etc).
   */
  defineFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(config: FlowConfig<I, O>, fn: FlowFn<I, O>): CallableFlow<I, O> {
    return this.genkit.defineFlow(config, fn);
  }

  /**
   * Defines and registers a streaming flow.
   *
   * @todo TODO: Improve this documentation (show snippetss, etc).
   */
  defineStreamingFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    S extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    config: StreamingFlowConfig<I, O, S>,
    fn: FlowFn<I, O, S>
  ): StreamableFlow<I, O, S> {
    return this.genkit.defineStreamingFlow(config, fn);
  }

  /**
   * Defines and registers a tool.
   *
   * Tools can be passed to models by name or value during `generate` calls to be called automatically based on the prompt and situation.
   */
  defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    config: ToolConfig<I, O>,
    fn: (input: z.infer<I>) => Promise<z.infer<O>>
  ): ToolAction<I, O> {
    return this.genkit.defineTool(config, fn);
  }

  /**
   * Defines and registers a dotprompt.
   *
   * This is an alternative to defining and importing a .prompt file.
   *
   * ```ts
   * const hi = ai.definePrompt(
   *   {
   *     name: 'hi',
   *     input: {
   *       schema: z.object({
   *         name: z.string(),
   *       }),
   *     },
   *   },
   *   'hi {{ name }}'
   * );
   * const { text } = await hi({ name: 'Genkit' });
   * ```
   */
  definePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions> & {
      /** The name of the prompt. */
      name: string;
    },
    template: string
  ): ExecutablePrompt<I, O, CustomOptions>;

  /**
   * Defines and registers a function-based prompt.
   *
   * ```ts
   * const hi = ai.definePrompt(
   *   {
   *     name: 'hi',
   *     input: {
   *       schema: z.object({
   *         name: z.string(),
   *       }),
   *     },
   *     config: {
   *       temperature: 1,
   *     },
   *   },
   *   async (input) => {
   *     return {
   *       messages: [ { role: 'user', content: [{ text: `hi ${input.name}` }] } ],
   *     };
   *   }
   * );
   * const { text } = await hi({ name: 'Genkit' });
   * ```
   */
  definePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions> & {
      /** The name of the prompt. */
      name: string;
    },
    fn: PromptFn<I>
  ): ExecutablePrompt<I, O, CustomOptions>;

  definePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions> & {
      /** The name of the prompt. */
      name: string;
    },
    templateOrFn: string | PromptFn<I>
  ): ExecutablePrompt<I, O, CustomOptions> {
    return this.genkit.definePrompt(options, templateOrFn as PromptFn<I>);
  }

  /**
   * Create a session for this environment.
   */
  async createSession(
    options?: EnvironmentSessionOptions<S>
  ): Promise<Session<S>> {
    const sessionId = uuidv4();
    const sessionData: SessionData<S> = {
      state: options?.state,
      threads: {
        [MAIN_THREAD]: options?.messages ?? [],
      },
    };
    await this.store.save(sessionId, sessionData);
    return new Session(
      this,
      {
        ...options,
      },
      {
        id: sessionId,
        sessionData,
        stateSchema: options?.stateSchema,
        store: this.store,
      }
    );
  }

  /**
   * Loads a session from the store.
   */
  async loadSession(
    sessionId: string,
    options?: EnvironmentSessionOptions<S>
  ): Promise<Session<S>> {
    const sessionData = await this.store.get(sessionId);

    return new Session(
      this,
      {
        ...options,
      },
      {
        id: sessionId,
        sessionData,
        stateSchema: options?.stateSchema,
        store: this.store,
      }
    );
  }

  /**
   * Gets the current session from async local storage.
   */
  get currentSession(): Session<S> {
    const currentSession = getCurrentSession();
    if (!currentSession) {
      throw new SessionError('not running within a session');
    }
    return currentSession as Session<S>;
  }
}

export type SessionOptions<S extends z.ZodTypeAny> = BaseGenerateOptions & {
  /** Schema describing the state. */
  stateSchema?: S;
  /** Session store implementation for persisting the session state. */
  store?: SessionStore<S>;
  /** Initial state of the session.  */
  state?: z.infer<S>;
  /** Custom session Id. */
  sessionId?: string;
};

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
export class Session<S extends z.ZodTypeAny> {
  readonly id: string;
  readonly schema?: S;
  private sessionData?: SessionData<S>;
  private store: SessionStore<S>;

  constructor(
    readonly parent: Genkit | Environment<S>,
    private requestBase?: BaseGenerateOptions,
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
      this.sessionData = {};
    }
    if (!this.sessionData.threads) {
      this.sessionData!.threads = {};
    }
    this.store = options?.store ?? new InMemorySessionStore();
  }

  get genkit(): Genkit {
    if (this.parent instanceof Session) {
      return this.parent.genkit;
    }
    if (this.parent instanceof Environment) {
      return this.parent.genkit;
    }
    return this.parent;
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
    let sessionData = await this.store.get(this.id);
    if (!sessionData) {
      sessionData = {} as SessionData<S>;
    }
    sessionData.state = data;
    this.sessionData = sessionData;

    await this.store.save(this.id, sessionData);
  }

  chat<S extends z.ZodTypeAny = z.ZodTypeAny>(
    options?: ChatOptions<S>
  ): Chat<S>;

  chat<S extends z.ZodTypeAny = z.ZodTypeAny>(
    threadName: string,
    options?: ChatOptions<S>
  ): Chat<S>;

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
  chat(
    optionsOrThreadName?: ChatOptions<S> | string,
    maybeOptions?: ChatOptions<S>
  ): Chat<S> {
    let options: ChatOptions<S> | undefined;
    let threadName = '__main';
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
    return new Chat<S>(
      this,
      {
        ...this.requestBase,
        ...options,
      },
      {
        threadName,
        id: this.id,
        sessionData: {
          state: options?.state,
        },
        stateSchema: options?.stateSchema,
        store: this.store ?? options?.store,
      }
    );
  }

  toJSON() {
    return this.sessionData;
  }
}

export interface SessionData<S extends z.ZodTypeAny> {
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

  save(sessionId: string, data: SessionData<S>): Promise<void>;
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
