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
import { ExecutablePrompt, Genkit } from './genkit';

const MAIN_THREAD = '__main';

export type BaseGenerateOptions = Omit<GenerateOptions, 'prompt'>;

export type SessionOptions<S extends z.ZodTypeAny> = BaseGenerateOptions & {
  stateSchema?: S;
  store?: SessionStore<S>;
  state?: z.infer<S>;
  sessionId?: string;
};

type EnvironmentType = Pick<
  Genkit,
  'defineFlow' | 'defineStreamingFlow' | 'defineTool' | 'definePrompt'
>;

type EnvironmentSessionOptions<S extends z.ZodTypeAny> = Omit<
  SessionOptions<S>,
  'store'
>;

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
    this.store = config.store ?? new InMemorySessionStore();
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
  createSession(options?: EnvironmentSessionOptions<S>): Session<S> {
    return new Session(
      this.genkit,
      {
        ...options,
      },
      {
        id: options?.sessionId,
        sessionData: {
          state: options?.state,
        },
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
    const state = await this.store.get(sessionId);

    return this.createSession({
      sessionId,
      ...options,
      state,
    });
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

export class Session<S extends z.ZodTypeAny> {
  readonly id: string;
  readonly schema?: S;
  private sessionData?: SessionData<S>;
  private store: SessionStore<S>;
  private threadName: string;

  constructor(
    readonly parent: Genkit | Environment<S> | Session<S>,
    readonly requestBase?: BaseGenerateOptions,
    options?: {
      id?: string;
      stateSchema?: S;
      sessionData?: SessionData<S>;
      store?: SessionStore<S>;
      threadName?: string;
    }
  ) {
    this.id = options?.id ?? uuidv4();
    this.schema = options?.stateSchema;
    this.threadName = options?.threadName ?? MAIN_THREAD;
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
    if (parent instanceof Session) {
      if (!this.sessionData.threads[this.threadName]) {
        this!.sessionData.threads[this.threadName] = [
          ...(parent.messages ?? []),
          ...(requestBase?.messages ?? []),
        ];
      }
    } else {
      if (!this.sessionData.threads[this.threadName]) {
        this.sessionData.threads[this.threadName] = [
          ...(requestBase?.messages ?? []),
        ];
      }
    }
    this.store = options?.store ?? new InMemorySessionStore();
  }

  thread(threadName: string): Session<S> {
    const requestBase = {
      ...this.requestBase,
    };
    delete requestBase.messages;
    const parent = this.parent instanceof Session ? this.parent : this;
    return new Session(parent, requestBase, {
      id: this.id,
      stateSchema: this.schema,
      store: this.store,
      threadName,
      sessionData: this.sessionData,
    });
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
    if (this.parent instanceof Session) {
      return this.parent.genkit;
    }
    if (this.parent instanceof Environment) {
      return this.parent.genkit;
    }
    return this.parent;
  }

  runFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(flow: CallableFlow<I, O>, input: z.infer<I>): Promise<z.infer<O>> {
    return runWithSession(this, () => flow(input));
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

  get messages(): MessageData[] | undefined {
    if (!this.sessionData?.threads) {
      return undefined;
    }
    return this.sessionData?.threads[this.threadName];
  }

  async updateMessages(messages: MessageData[]): Promise<void> {
    let sessionData = await this.store.get(this.id);
    if (!sessionData) {
      sessionData = { threads: {} };
    }
    if (!sessionData.threads) {
      sessionData.threads = {};
    }
    sessionData.threads[this.threadName] = messages;
    this.sessionData = sessionData;
    await this.store.save(this.id, sessionData);
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

class InMemorySessionStore<S extends z.ZodTypeAny> implements SessionStore<S> {
  private data: Record<string, SessionData<S>> = {};

  async get(sessionId: string): Promise<SessionData<S> | undefined> {
    return this.data[sessionId];
  }

  async save(sessionId: string, sessionData: SessionData<S>): Promise<void> {
    this.data[sessionId] = sessionData;
  }
}
