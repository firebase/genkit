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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.google.genkit.ai.Message;

/**
 * SessionData represents the persistent data structure for a session, including
 * state and conversation threads.
 *
 * @param <S>
 *            the type of the custom session state
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SessionData<S> {

  /**
   * The unique identifier for this session.
   */
  @JsonProperty("id")
  private String id;

  /**
   * Custom user-defined state associated with the session.
   */
  @JsonProperty("state")
  private S state;

  /**
   * Named conversation threads. Each thread is identified by a string key
   * (default is "main") and contains a list of messages.
   */
  @JsonProperty("threads")
  private Map<String, List<Message>> threads;

  /**
   * Default constructor.
   */
  public SessionData() {
    this.threads = new HashMap<>();
  }

  /**
   * Creates a new SessionData with the given ID.
   *
   * @param id
   *            the session ID
   */
  public SessionData(String id) {
    this.id = id;
    this.threads = new HashMap<>();
  }

  /**
   * Creates a new SessionData with the given ID and initial state.
   *
   * @param id
   *            the session ID
   * @param state
   *            the initial state
   */
  public SessionData(String id, S state) {
    this.id = id;
    this.state = state;
    this.threads = new HashMap<>();
  }

  /**
   * Gets the session ID.
   *
   * @return the session ID
   */
  public String getId() {
    return id;
  }

  /**
   * Sets the session ID.
   *
   * @param id
   *            the session ID
   */
  public void setId(String id) {
    this.id = id;
  }

  /**
   * Gets the session state.
   *
   * @return the session state
   */
  public S getState() {
    return state;
  }

  /**
   * Sets the session state.
   *
   * @param state
   *            the session state
   */
  public void setState(S state) {
    this.state = state;
  }

  /**
   * Gets all conversation threads.
   *
   * @return the threads map
   */
  public Map<String, List<Message>> getThreads() {
    return threads;
  }

  /**
   * Sets all conversation threads.
   *
   * @param threads
   *            the threads map
   */
  public void setThreads(Map<String, List<Message>> threads) {
    this.threads = threads;
  }

  /**
   * Gets a specific thread by name.
   *
   * @param threadName
   *            the thread name
   * @return the list of messages in the thread, or null if not found
   */
  public List<Message> getThread(String threadName) {
    return threads.get(threadName);
  }

  /**
   * Gets or creates a thread by name.
   *
   * @param threadName
   *            the thread name
   * @return the list of messages in the thread
   */
  public List<Message> getOrCreateThread(String threadName) {
    return threads.computeIfAbsent(threadName, k -> new ArrayList<>());
  }

  /**
   * Sets messages for a specific thread.
   *
   * @param threadName
   *            the thread name
   * @param messages
   *            the messages to set
   */
  public void setThread(String threadName, List<Message> messages) {
    threads.put(threadName, new ArrayList<>(messages));
  }

  /**
   * Creates a builder for SessionData.
   *
   * @param <S>
   *            the state type
   * @return a new builder
   */
  public static <S> Builder<S> builder() {
    return new Builder<>();
  }

  /**
   * Builder for SessionData.
   *
   * @param <S>
   *            the state type
   */
  public static class Builder<S> {
    private String id;
    private S state;
    private Map<String, List<Message>> threads = new HashMap<>();

    /**
     * Sets the session ID.
     *
     * @param id
     *            the session ID
     * @return this builder
     */
    public Builder<S> id(String id) {
      this.id = id;
      return this;
    }

    /**
     * Sets the session state.
     *
     * @param state
     *            the session state
     * @return this builder
     */
    public Builder<S> state(S state) {
      this.state = state;
      return this;
    }

    /**
     * Sets the conversation threads.
     *
     * @param threads
     *            the threads map
     * @return this builder
     */
    public Builder<S> threads(Map<String, List<Message>> threads) {
      this.threads = new HashMap<>(threads);
      return this;
    }

    /**
     * Adds a thread.
     *
     * @param threadName
     *            the thread name
     * @param messages
     *            the messages
     * @return this builder
     */
    public Builder<S> thread(String threadName, List<Message> messages) {
      this.threads.put(threadName, new ArrayList<>(messages));
      return this;
    }

    /**
     * Builds the SessionData.
     *
     * @return the built SessionData
     */
    public SessionData<S> build() {
      SessionData<S> data = new SessionData<>();
      data.setId(id);
      data.setState(state);
      data.setThreads(threads);
      return data;
    }
  }
}
