/**
 * Copyright 2025 Google LLC
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

import { ExecutablePrompt, isExecutablePrompt } from '@genkit-ai/ai';
import { Chat, ChatOptions } from '@genkit-ai/ai/chat';
import {
  Session,
  SessionData,
  SessionError,
  SessionOptions,
  getCurrentSession,
} from '@genkit-ai/ai/session';
import { v4 as uuidv4 } from 'uuid';
import { Genkit, GenkitOptions } from './genkit';

/**
 * WARNING: these APIs are considered unstable and subject to frequent breaking changes that may not honor semver.
 *
 * Initializes Genkit BETA APIs with a set of options.
 *
 * This will create a new Genkit registry, register the provided plugins, stores, and other configuration. This
 * should be called before any flows are registered.
 */
export function genkit(options: GenkitOptions): GenkitBeta {
  return new GenkitBeta(options);
}

/**
 * Genkit BETA APIs.
 */
export class GenkitBeta extends Genkit {
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
  chat<I>(options?: ChatOptions<I>): Chat;

  /**
   * Create a chat session with the provided preabmle.
   *
   * ```ts
   * const triageAgent = ai.definePrompt({
   *   system: 'help the user triage a problem',
   * })
   * const chat = ai.chat(triageAgent)
   * const { text } = await chat.send('my phone feels hot');
   * ```
   */
  chat<I>(preamble: ExecutablePrompt<I>, options?: ChatOptions<I>): Chat;

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
  chat<I>(
    preambleOrOptions?: ChatOptions<I> | ExecutablePrompt<I>,
    maybeOptions?: ChatOptions<I>
  ): Chat {
    let options: ChatOptions<I> | undefined;
    let preamble: ExecutablePrompt<I> | undefined;
    if (maybeOptions) {
      options = maybeOptions;
    }
    if (preambleOrOptions) {
      if (isExecutablePrompt(preambleOrOptions)) {
        preamble = preambleOrOptions as ExecutablePrompt<I>;
      } else {
        options = preambleOrOptions as ChatOptions<I>;
      }
    }

    const session = this.createSession();
    if (preamble) {
      return session.chat(preamble, options);
    }
    return session.chat(options);
  }

  /**
   * Create a session for this environment.
   */
  createSession<S = any>(options?: SessionOptions<S>): Session<S> {
    const sessionId = options?.sessionId?.trim() || uuidv4();
    const sessionData: SessionData = {
      id: sessionId,
      state: options?.initialState,
    };
    return new Session(this.registry, {
      id: sessionId,
      sessionData,
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

    return new Session(this.registry, {
      id: sessionId,
      sessionData,
      store: options.store,
    });
  }

  /**
   * Gets the current session from async local storage.
   */
  currentSession<S = any>(): Session<S> {
    const currentSession = getCurrentSession(this.registry);
    if (!currentSession) {
      throw new SessionError('not running within a session');
    }
    return currentSession as Session;
  }
}
