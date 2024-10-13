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

import { PromptFn, ToolAction, ToolConfig } from '@genkit-ai/ai';
import {
  CallableFlow,
  FlowConfig,
  FlowFn,
  StreamableFlow,
  StreamingFlowConfig,
  z,
} from '@genkit-ai/core';
import { PromptMetadata } from '@genkit-ai/dotprompt';
import { v4 as uuidv4 } from 'uuid';
import { MAIN_THREAD } from './chat.js';
import { ExecutablePrompt, Genkit } from './genkit.js';
import {
  Session,
  SessionData,
  SessionError,
  SessionOptions,
  SessionStore,
  getCurrentSession,
  inMemorySessionStore,
} from './session.js';

type EnvironmentInterface = Pick<
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
export class Environment<S extends z.ZodTypeAny>
  implements EnvironmentInterface
{
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
