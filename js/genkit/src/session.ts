import {
  GenerateOptions,
  GenerateResponse,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  MessageData,
  Part,
  PromptAction,
  PromptConfig,
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
import { Dotprompt, PromptMetadata } from '@genkit-ai/dotprompt';
import { AsyncLocalStorage } from 'node:async_hooks';
import { v4 as uuidv4 } from 'uuid';
import { Genkit } from './genkit';

export type BaseGenerateOptions = Omit<GenerateOptions, 'prompt'>;

export interface SessionOptions<S extends z.ZodTypeAny> {
  state?: z.infer<S>;
  schema?: S;
  store?: SessionStore<S>;
}

type EnvironmentType = Pick<
  Genkit,
  | 'defineFlow'
  | 'defineStreamingFlow'
  | 'defineTool'
  | 'defineDotprompt'
  | 'definePrompt'
>;

type EnvironmentSessionOptions<S extends z.ZodTypeAny> = Omit<
  SessionOptions<S>,
  'store'
>;

export class Environment<S extends z.ZodTypeAny> implements EnvironmentType {
  private store: SessionStore<S>;
  private name: string;

  constructor(
    private genkit: Genkit,
    config: {
      name: string;
      stateSchema?: S;
      store?: SessionStore<S>;
    }
  ) {
    this.name = config.name;
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
   * This replaces defining and importing a .dotprompt file.
   *
   * @todo TODO: Improve this documentation (show an example, etc).
   */
  defineDotprompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions>,
    template: string
  ): Dotprompt<z.infer<I>> {
    return this.genkit.defineDotprompt(options, template);
  }

  /**
   * Defines and registers a prompt action.
   */
  definePrompt<I extends z.ZodTypeAny = z.ZodTypeAny>(
    config: PromptConfig<I>,
    fn: PromptFn<I>
  ): PromptAction<I> {
    return this.genkit.definePrompt(config, fn);
  }

  createSession(options?: EnvironmentSessionOptions<S>): Session<S>;

  createSession(
    requestBase: BaseGenerateOptions,
    options?: EnvironmentSessionOptions<S>
  ): Session<S>;

  createSession(
    requestBaseOrOpts?: EnvironmentSessionOptions<S> | BaseGenerateOptions,
    maybeOptions?: EnvironmentSessionOptions<S>
  ): Session<S> {
    // parse overloaded args
    let baseGenerateOptions: BaseGenerateOptions | undefined = undefined;
    let options: EnvironmentSessionOptions<S> | undefined = undefined;
    if (maybeOptions !== undefined) {
      options = maybeOptions;
      baseGenerateOptions = requestBaseOrOpts as BaseGenerateOptions;
    } else if (requestBaseOrOpts !== undefined) {
      if (
        (requestBaseOrOpts as EnvironmentSessionOptions<S>).state ||
        (requestBaseOrOpts as EnvironmentSessionOptions<S>).schema
      ) {
        options = requestBaseOrOpts as EnvironmentSessionOptions<S>;
      } else {
        baseGenerateOptions = requestBaseOrOpts as BaseGenerateOptions;
      }
    }

    return new Session(
      this.genkit,
      {
        ...baseGenerateOptions,
      },
      {
        state: options?.state,
        schema: options?.schema,
        store: this.store,
      }
    );
  }

  loadSession(
    sessionId: string,
    options?: EnvironmentSessionOptions<S>
  ): Promise<Session<S>>;

  loadSession(
    sessionId: string,
    requestBase: BaseGenerateOptions,
    options?: EnvironmentSessionOptions<S>
  ): Promise<Session<S>>;

  async loadSession(
    sessionId: string,
    requestBaseOrOpts?: EnvironmentSessionOptions<S> | BaseGenerateOptions,
    maybeOptions?: EnvironmentSessionOptions<S>
  ): Promise<Session<S>> {
    // parse overloaded args
    let baseGenerateOptions: BaseGenerateOptions | undefined = undefined;
    let options: EnvironmentSessionOptions<S> | undefined = undefined;
    if (maybeOptions !== undefined) {
      options = maybeOptions;
      baseGenerateOptions = requestBaseOrOpts as BaseGenerateOptions;
    } else if (requestBaseOrOpts !== undefined) {
      if (
        (requestBaseOrOpts as EnvironmentSessionOptions<S>).state ||
        (requestBaseOrOpts as EnvironmentSessionOptions<S>).schema
      ) {
        options = requestBaseOrOpts as EnvironmentSessionOptions<S>;
      } else {
        baseGenerateOptions = requestBaseOrOpts as BaseGenerateOptions;
      }
    }

    const state = this.store.get(sessionId);

    return this.createSession(baseGenerateOptions!, {
      ...options,
      state
    });
  }

  get currentSession() {
    const currentSession = getCurrentSession();
    if (!currentSession) {
      throw new SessionError('not running within a session');
    }
    return currentSession;
  }
}

export class Session<S extends z.ZodTypeAny> {
  readonly id: string;
  readonly schema?: S;
  readonly sessionData: SessionData<S>;
  private store: SessionStore<S>;

  constructor(
    readonly environment: Genkit,
    readonly requestBase?: BaseGenerateOptions,
    options?: {
      schema?: S;
      state: z.infer<S>;
      store?: SessionStore<S>;
    }
  ) {
    this.id = uuidv4();
    this.schema = options?.schema;
    this.sessionData = {
      state: options?.state ?? {},
      messages: requestBase?.messages ?? [],
    };
    this.store = options?.store ?? new InMemorySessionStore()
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
    const response = await this.environment.generate({
      ...this.requestBase,
      messages: this.sessionData.messages,
      ...options,
    });
    await this.updateMessages(response.toHistory());
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
    const response = await this.environment.generateStream({
      ...this.requestBase,
      ...options,
    });

    try {
      return response;
    } finally {
      await this.updateMessages((await response.response()).toHistory());
    }
  }

  runFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(flow: CallableFlow<I, O>, input: z.infer<I>): Promise<z.infer<O>> {
    return runWithSession(this, () => flow(input));
  }

  get state(): z.infer<S> {
    return this.sessionData.state;
  }

  async updateState(data: z.infer<S>): Promise<void> {
    this.sessionData.state = data;
    await this.store.save(this.id, {
      state: this.state,
      messages: this.messages,
    });
  }

  get messages(): MessageData[] | undefined {
    return this.sessionData.messages;
  }

  async updateMessages(messages: MessageData[]): Promise<void> {
    this.sessionData.messages = messages;
    await this.store.save(this.id, {
      state: this.state,
      messages: this.messages,
    });
  }

  toJSON() {
    return this.sessionData;
  }

  static fromJSON<S extends z.ZodTypeAny>(data: SessionData<S>) {
    //return new Session();
  }
}

export interface SessionData<S extends z.ZodTypeAny> {
  state?: z.infer<S>;
  messages?: MessageData[];
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

export interface SessionStore<S extends z.ZodTypeAny> {
  get(sessionId: string): Promise<SessionData<S> | undefined>;

  save(sessionId: string, data: SessionData<S>): Promise<void>;
}

class InMemorySessionStore<S extends z.ZodTypeAny> implements SessionStore<S> {
  private data: Record<string, SessionData<S>> = {};

  async get(sessionId: string): Promise<SessionData<S> | undefined> {
    return this.data[sessionId];
  }

  async save(sessionId: string, data: SessionData<S>): Promise<void> {
    data[sessionId] = data;
  }
}
