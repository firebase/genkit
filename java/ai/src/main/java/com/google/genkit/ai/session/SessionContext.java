/*
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.ai.session;

import java.util.concurrent.Callable;

import com.google.genkit.core.GenkitException;

/**
 * Provides access to the current session context.
 *
 * <p>
 * This class uses ThreadLocal to store the current session, making it
 * accessible from within tool execution. This enables tools to access and
 * modify session state during their execution.
 *
 * <p>
 * Example usage in a tool:
 *
 * <pre>{@code
 * Tool<Input, Output> myTool = genkit.defineTool(
 * 		ToolConfig.<Input, Output>builder().name("myTool").description("A tool that accesses session state")
 * 				.inputSchema(Input.class).outputSchema(Output.class).build(),
 * 		(input, ctx) -> {
 * 			// Access current session from within tool
 * 			Session<MyState> session = SessionContext.currentSession();
 * 			MyState state = session.getState();
 *
 * 			// Update session state
 * 			session.updateState(new MyState(state.getName(), state.getCount() + 1));
 *
 * 			return new Output("Updated");
 * 		});
 * }</pre>
 */
public final class SessionContext {

  private static final ThreadLocal<Session<?>> CURRENT_SESSION = new ThreadLocal<>();

  private SessionContext() {
  }

  /**
   * Gets the current session.
   *
   * @param <S>
   *            the session state type
   * @return the current session
   * @throws SessionException
   *             if not running within a session
   */
  @SuppressWarnings("unchecked")
  public static <S> Session<S> currentSession() {
    Session<?> session = CURRENT_SESSION.get();
    if (session == null) {
      throw new SessionException("Not running within a session context");
    }
    return (Session<S>) session;
  }

  /**
   * Gets the current session if available.
   *
   * @param <S>
   *            the session state type
   * @return the current session, or null if not in a session context
   */
  @SuppressWarnings("unchecked")
  public static <S> Session<S> getCurrentSession() {
    return (Session<S>) CURRENT_SESSION.get();
  }

  /**
   * Checks if currently running within a session context.
   *
   * @return true if in a session context
   */
  public static boolean hasSession() {
    return CURRENT_SESSION.get() != null;
  }

  /**
   * Runs a function within a session context.
   *
   * @param <S>
   *            the session state type
   * @param <T>
   *            the return type
   * @param session
   *            the session to use
   * @param callable
   *            the function to run
   * @return the result of the function
   * @throws Exception
   *             if the function throws an exception
   */
  public static <S, T> T runWithSession(Session<S> session, Callable<T> callable) throws Exception {
    Session<?> previous = CURRENT_SESSION.get();
    try {
      CURRENT_SESSION.set(session);
      return callable.call();
    } finally {
      if (previous != null) {
        CURRENT_SESSION.set(previous);
      } else {
        CURRENT_SESSION.remove();
      }
    }
  }

  /**
   * Runs a runnable within a session context.
   *
   * @param <S>
   *            the session state type
   * @param session
   *            the session to use
   * @param runnable
   *            the runnable to execute
   */
  public static <S> void runWithSession(Session<S> session, Runnable runnable) {
    Session<?> previous = CURRENT_SESSION.get();
    try {
      CURRENT_SESSION.set(session);
      runnable.run();
    } finally {
      if (previous != null) {
        CURRENT_SESSION.set(previous);
      } else {
        CURRENT_SESSION.remove();
      }
    }
  }

  /**
   * Sets the current session. This is typically called internally by Chat.
   *
   * @param session
   *            the session to set
   */
  public static void setSession(Session<?> session) {
    if (session != null) {
      CURRENT_SESSION.set(session);
    } else {
      CURRENT_SESSION.remove();
    }
  }

  /** Clears the current session. */
  public static void clearSession() {
    CURRENT_SESSION.remove();
  }

  /** Exception thrown when session operations fail. */
  public static class SessionException extends GenkitException {
    public SessionException(String message) {
      super(message);
    }

    public SessionException(String message, Throwable cause) {
      super(message, cause);
    }
  }
}
