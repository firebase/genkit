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

/**
 * SessionOptions provides configuration options for creating or loading
 * sessions.
 *
 * @param <S>
 *            the type of the custom session state
 */
public class SessionOptions<S> {

  private SessionStore<S> store;
  private S initialState;
  private String sessionId;

  /**
   * Default constructor.
   */
  public SessionOptions() {
  }

  /**
   * Gets the session store.
   *
   * @return the session store
   */
  public SessionStore<S> getStore() {
    return store;
  }

  /**
   * Sets the session store.
   *
   * @param store
   *            the session store
   */
  public void setStore(SessionStore<S> store) {
    this.store = store;
  }

  /**
   * Gets the initial state.
   *
   * @return the initial state
   */
  public S getInitialState() {
    return initialState;
  }

  /**
   * Sets the initial state.
   *
   * @param initialState
   *            the initial state
   */
  public void setInitialState(S initialState) {
    this.initialState = initialState;
  }

  /**
   * Gets the session ID.
   *
   * @return the session ID
   */
  public String getSessionId() {
    return sessionId;
  }

  /**
   * Sets the session ID.
   *
   * @param sessionId
   *            the session ID
   */
  public void setSessionId(String sessionId) {
    this.sessionId = sessionId;
  }

  /**
   * Creates a builder for SessionOptions.
   *
   * @param <S>
   *            the state type
   * @return a new builder
   */
  public static <S> Builder<S> builder() {
    return new Builder<>();
  }

  /**
   * Builder for SessionOptions.
   *
   * @param <S>
   *            the state type
   */
  public static class Builder<S> {
    private SessionStore<S> store;
    private S initialState;
    private String sessionId;

    /**
     * Sets the session store.
     *
     * @param store
     *            the session store
     * @return this builder
     */
    public Builder<S> store(SessionStore<S> store) {
      this.store = store;
      return this;
    }

    /**
     * Sets the initial state.
     *
     * @param initialState
     *            the initial state
     * @return this builder
     */
    public Builder<S> initialState(S initialState) {
      this.initialState = initialState;
      return this;
    }

    /**
     * Sets the session ID.
     *
     * @param sessionId
     *            the session ID
     * @return this builder
     */
    public Builder<S> sessionId(String sessionId) {
      this.sessionId = sessionId;
      return this;
    }

    /**
     * Builds the SessionOptions.
     *
     * @return the built SessionOptions
     */
    public SessionOptions<S> build() {
      SessionOptions<S> options = new SessionOptions<>();
      options.setStore(store);
      options.setInitialState(initialState);
      options.setSessionId(sessionId);
      return options;
    }
  }
}
