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
import { v4 as uuidv4 } from 'uuid';
import { Genkit } from './genkit.js';
import {
  getCurrentSession,
  inMemorySessionStore,
  Session,
  SessionData,
  SessionError,
  SessionOptions,
  SessionStore,
} from './session.js';

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
export class Environment<S extends z.ZodTypeAny> {
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
   * Create a session for this environment.
   */
  createSession(options?: SessionOptions): Session {
    const sessionId = uuidv4();
    const sessionData: SessionData = {
      id: sessionId,
      state: options?.initialState,
    };
    return new Session(this.genkit, {
      id: sessionId,
      sessionData,
      stateSchema: options?.stateSchema,
      store: options?.store,
    });
  }

  /**
   * Loads a session from the store.
   */
  async loadSession(
    sessionId: string,
    options: SessionOptions
  ): Promise<Session> {
    if (!options.store) {
      throw new Error('options.store is required');
    }
    const sessionData = await options.store.get(sessionId);

    return new Session(this.genkit, {
      id: sessionId,
      sessionData,
      stateSchema: options?.stateSchema,
      store: options.store,
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
